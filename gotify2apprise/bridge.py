from __future__ import annotations

import asyncio
import logging
from typing import Any

from gotify2apprise.config.manager import ConfigError, ConfigManager, ConfigV1Error
from gotify2apprise.delivery.worker import DeliveryWorker
from gotify2apprise.listeners.base import Listener
from gotify2apprise.listeners.factory import create_listener
from gotify2apprise.models.config import AppConfig
from gotify2apprise.models.message import NormalizedMessage
from gotify2apprise.routing.engine import RoutingEngine
from gotify2apprise.settings import Settings
from gotify2apprise.storage.auth_repo import AuthRepo
from gotify2apprise.storage.db import Database
from gotify2apprise.storage.messages_repo import MessagesRepo
from gotify2apprise.storage.queue import DeliveryQueue
from gotify2apprise.storage.stats_repo import StatsRepo

log = logging.getLogger(__name__)


class Bridge:
    def __init__(self, settings: Settings, db: Database) -> None:
        self.settings = settings
        self.db = db
        self.config_manager = ConfigManager(settings)
        self.router = RoutingEngine()
        self.messages = MessagesRepo(db)
        self.queue = DeliveryQueue(db)
        self.stats = StatsRepo(db)
        self.auth = AuthRepo(db)
        self.worker = DeliveryWorker(
            self.queue,
            self.stats,
            lambda: self.config,
            on_prune=self._prune,
        )
        self.listeners: dict[str, Listener] = {}
        self.config: AppConfig | None = None
        self.last_error: str | None = None

    async def start(self) -> None:
        await self.worker.start()
        try:
            await self.reload()
        except ConfigV1Error:
            raise
        except ConfigError as exc:
            self.last_error = str(exc)
            log.error("config error: %s", exc)
        except Exception as exc:
            self.last_error = str(exc)
            log.exception("bridge start failed")

    async def stop(self) -> None:
        try:
            await self.worker.stop()
        except asyncio.CancelledError:
            pass
        try:
            await self._stop_listeners(list(self.listeners.keys()))
        except asyncio.CancelledError:
            pass

    async def reload(self) -> AppConfig:
        config = self.config_manager.load()
        await self._sync_listeners(config)
        self.config = config
        self.last_error = None
        log.info(
            "config loaded: %s listeners, %s receivers, %s routes",
            len(config.listeners),
            len(config.receivers),
            len(config.routes),
        )
        return config

    async def save_and_reload(self, text: str) -> AppConfig:
        self.config_manager.save_text(text)
        return await self.reload()

    async def handle_message(self, message: NormalizedMessage) -> None:
        log.info(
            "msg from %s prio=%s title=%s",
            message.source_listener_id,
            message.priority,
            message.title,
        )
        await self.messages.insert(message)
        config = self.config
        if config is None:
            log.warning("no config snapshot, drop routing for %s", message.id)
            return
        targets = self.router.route(message, config)
        if not targets:
            log.info("no receivers for message %s", message.id)
            return
        for target in targets:
            await self.queue.enqueue(
                message_id=message.id,
                receiver_id=target.receiver.id,
                route_id=target.route.id,
                title=target.title,
                body=target.body,
                policy=target.delivery,
            )

    async def retry_delivery(self, delivery_id: str) -> None:
        await self.queue.retry_now(delivery_id)

    async def _sync_listeners(self, config: AppConfig) -> None:
        desired = {
            item.id: item
            for item in config.listeners
            if item.enabled
        }
        for listener_id in list(self.listeners):
            old = self.listeners[listener_id]
            new = desired.get(listener_id)
            if new is None or new.model_dump() != old.config.model_dump():
                await self._stop_listeners([listener_id])
        for listener_id, item in desired.items():
            if listener_id in self.listeners:
                continue
            listener = create_listener(item, self.handle_message)
            try:
                await listener.start()
            except Exception:
                log.exception("failed to start listener %s", listener_id)
                continue
            self.listeners[listener_id] = listener

    async def _stop_listeners(self, ids: list[str]) -> None:
        for listener_id in ids:
            listener = self.listeners.pop(listener_id, None)
            if listener is None:
                continue
            try:
                await listener.stop()
            except asyncio.CancelledError:
                pass
            except Exception:
                log.exception("failed to stop listener %s", listener_id)

    async def _prune(self) -> None:
        await self.messages.prune(
            retention_days=self.settings.message_retention_days,
            max_per_channel=self.settings.max_messages_per_channel,
        )

    def status(self) -> dict[str, Any]:
        return {
            "error": self.last_error,
            "listeners": list(self.listeners),
            "config_loaded": self.config is not None,
        }
