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


class GotifyListener:
    def __init__(self, config: ListenerConfig, on_message: OnMessage) -> None:
        self.config = config
        self._on_message = on_message
        self._opts = config.gotify()
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._apps: dict[int, dict[str, Any]] = {}
        self._apps_fetched_at = 0.0

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
            except Exception:
                log.exception("listener %s: failed to fetch Gotify applications", self.config.id)
        return self._apps

    def _accept_app(self, app: dict[str, Any]) -> bool:
        tokens = self._opts.app_tokens
        if "all" in tokens:
            return True
        return app.get("token") in tokens

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
