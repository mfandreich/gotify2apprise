from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
import websockets

from gotify2apprise.listeners.base import OnMessage
from gotify2apprise.models.config import ListenerConfig
from gotify2apprise.models.message import NormalizedMessage

log = logging.getLogger(__name__)

APP_CACHE_TTL_SEC = 60.0


def _stripped(values: list[str]) -> list[str]:
    return [item.strip() for item in values if str(item).strip()]


def accept_gotify_app(
    app: dict[str, Any],
    *,
    app_tokens: list[str],
    app_names: list[str],
) -> bool:
    tokens = _stripped(app_tokens)
    names = _stripped(app_names)
    if not tokens and not names:
        return True
    if "all" in tokens:
        return True
    token = str(app.get("token") or "")
    if token and token in set(tokens):
        return True
    name = str(app.get("name") or "").strip()
    if name and name.casefold() in {item.casefold() for item in names}:
        return True
    return False


def app_tokens_unusable_without_api_tokens(apps: dict[int, dict[str, Any]], app_tokens: list[str]) -> bool:
    tokens = [item for item in _stripped(app_tokens) if item != "all"]
    if not tokens:
        return False
    return not any(app.get("token") for app in apps.values())


class GotifyListener:
    def __init__(self, config: ListenerConfig, on_message: OnMessage) -> None:
        self.config = config
        self._on_message = on_message
        self._opts = config.gotify()
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._apps: dict[int, dict[str, Any]] = {}
        self._apps_fetched_at = 0.0
        self._warned_tokenless = False

    async def start(self) -> None:
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name=f"gotify:{self.config.id}")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def _scheme(self) -> tuple[str, str]:
        if self._opts.ssl:
            return "https", "wss"
        return "http", "ws"

    async def _fetch_apps(self) -> dict[int, dict[str, Any]]:
        http, _ = self._scheme()
        url = f"{http}://{self._opts.host}/application"
        headers = {"X-Gotify-Key": self._opts.client_token}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            result: dict[int, dict[str, Any]] = {}
            for app in response.json():
                result[int(app["id"])] = app
            return result

    async def _apps_cached(self, *, force: bool = False) -> dict[int, dict[str, Any]]:
        now = asyncio.get_running_loop().time()
        if force or not self._apps or (now - self._apps_fetched_at) > APP_CACHE_TTL_SEC:
            try:
                self._apps = await self._fetch_apps()
                self._apps_fetched_at = now
                self._warn_if_tokenless_api()
            except Exception:
                log.exception("listener %s: failed to fetch Gotify applications", self.config.id)
        return self._apps

    def _accept_app(self, app: dict[str, Any]) -> bool:
        return accept_gotify_app(
            app,
            app_tokens=self._opts.app_tokens,
            app_names=self._opts.app_names,
        )

    def _warn_if_tokenless_api(self) -> None:
        if self._warned_tokenless:
            return
        if not app_tokens_unusable_without_api_tokens(self._apps, self._opts.app_tokens):
            return
        self._warned_tokenless = True
        log.warning(
            "listener %s: GET /application did not return tokens; app_tokens cannot match. "
            "This usually means Gotify 3.0+ (tokens are shown only on create/rotate). "
            "Use app_names instead.",
            self.config.id,
        )

    def _log_accept_set(self) -> None:
        accepted = [
            f"{app.get('name')}#{app.get('id')}"
            for app in self._apps.values()
            if self._accept_app(app)
        ]
        log.info("listener %s: accepting %s", self.config.id, ", ".join(accepted) or "nothing")

    async def _handle_payload(self, payload: str) -> None:
        data = json.loads(payload)
        app_id = int(data["appid"])
        apps = await self._apps_cached()
        app = apps.get(app_id)
        if app is None:
            apps = await self._apps_cached(force=True)
            app = apps.get(app_id)
        if app is None:
            log.warning("listener %s: unknown appid %s, skip", self.config.id, app_id)
            return
        if not self._accept_app(app):
            log.info(
                "listener %s: skip appid=%s name=%s (not in app_tokens/app_names)",
                self.config.id,
                app_id,
                app.get("name"),
            )
            return
        message = NormalizedMessage(
            source_listener_id=self.config.id,
            title=str(data.get("title") or ""),
            body=str(data.get("message") or ""),
            priority=int(data.get("priority") or 0),
            raw=data,
            extra={"appid": app_id, "app_token": app.get("token"), "app_name": app.get("name")},
        )
        await self._on_message(message)

    async def _run(self) -> None:
        delay = 1.0
        while not self._stop.is_set():
            try:
                await self._apps_cached(force=True)
                self._log_accept_set()
                _, ws_scheme = self._scheme()
                url = f"{ws_scheme}://{self._opts.host}/stream"
                headers = {"X-Gotify-Key": self._opts.client_token}
                log.info("listener %s: connecting %s", self.config.id, url)
                async with websockets.connect(
                    url,
                    additional_headers=headers,
                    ping_interval=20,
                    ping_timeout=20,
                ) as ws:
                    delay = 1.0
                    log.info("listener %s: connected", self.config.id)
                    async for payload in ws:
                        if self._stop.is_set():
                            break
                        try:
                            await self._handle_payload(str(payload))
                        except Exception:
                            log.exception("listener %s: failed to handle message", self.config.id)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if self._stop.is_set():
                    return
                log.warning("listener %s: connection error: %s (retry in %.0fs)", self.config.id, exc, delay)
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    pass
                delay = min(delay * 2, 60.0)
