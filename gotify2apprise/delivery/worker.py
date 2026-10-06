from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from gotify2apprise.models.config import AppConfig
from gotify2apprise.receivers.factory import create_receiver
from gotify2apprise.storage.queue import DeliveryQueue
from gotify2apprise.storage.stats_repo import StatsRepo

log = logging.getLogger(__name__)

ConfigProvider = Callable[[], AppConfig | None]


class DeliveryWorker:
    def __init__(
        self,
        queue: DeliveryQueue,
        stats: StatsRepo,
        config_provider: ConfigProvider,
        *,
        poll_interval: float = 1.5,
        on_prune: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self.queue = queue
        self.stats = stats
        self.config_provider = config_provider
        self.poll_interval = poll_interval
        self.on_prune = on_prune
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._prune_ticks = 0

    async def start(self) -> None:
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="delivery-worker")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                await self.tick()
                self._prune_ticks += 1
                if self.on_prune and self._prune_ticks >= 40:
                    self._prune_ticks = 0
                    await self.on_prune()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("delivery worker tick failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.poll_interval)
            except asyncio.TimeoutError:
                pass

    async def tick(self) -> None:
        config = self.config_provider()
        if config is None:
            return
        for row in await self.queue.due():
            await self._deliver(row, config)

    async def _deliver(self, row: dict, config: AppConfig) -> None:
        receiver_cfg = config.receiver_by_id(str(row["receiver_id"]))
        if receiver_cfg is None or not receiver_cfg.enabled:
            await self.queue.mark_failure(
                str(row["id"]),
                f"receiver {row['receiver_id']} missing or disabled",
                row,
            )
            return
        try:
            result = await create_receiver(receiver_cfg).send(
                str(row["title"]),
                str(row["body"]),
                int(row["priority"]),
            )
        except Exception as exc:
            result_ok = False
            error = str(exc)
        else:
            result_ok = result.ok
            error = result.error or "notify failed"

        if result_ok:
            await self.queue.mark_success(str(row["id"]))
            await self.stats.increment(str(row["listener_id"]), str(row["receiver_id"]), ok=True)
            log.info(
                "delivered %s → %s via %s",
                row["message_id"],
                row["receiver_id"],
                row["route_id"],
            )
            return

        status = await self.queue.mark_failure(str(row["id"]), error, row)
        await self.stats.increment(str(row["listener_id"]), str(row["receiver_id"]), ok=False)
        log.warning(
            "delivery %s %s: %s",
            row["id"],
            status,
            error,
        )
