from __future__ import annotations

import asyncio
import logging

import apprise

from gotify2apprise.models.config import ReceiverConfig, priority_bucket
from gotify2apprise.models.message import SendResult

log = logging.getLogger(__name__)


def notify_type_for_priority(priority: int) -> apprise.NotifyType:
    bucket = priority_bucket(priority)
    if bucket == "warn":
        return apprise.NotifyType.WARNING
    if bucket == "crit":
        return apprise.NotifyType.FAILURE
    return apprise.NotifyType.INFO


class AppriseReceiver:
    def __init__(self, config: ReceiverConfig) -> None:
        self.config = config
        self._opts = config.apprise()

    def _notify_one(self, url: str, title: str, body: str, priority: int) -> None:
        instance = apprise.Apprise()
        if not instance.add(url):
            raise RuntimeError(f"invalid Apprise URL: {url}")
        ok = instance.notify(
            title=title,
            body=body,
            notify_type=notify_type_for_priority(priority),
        )
        if not ok:
            raise RuntimeError(f"Apprise notify failed for {url}")

    async def send(self, title: str, body: str, priority: int) -> SendResult:
        errors: list[str] = []
        for url in self._opts.urls:
            try:
                await asyncio.to_thread(self._notify_one, url, title, body, priority)
            except Exception as exc:
                log.warning("receiver %s: %s", self.config.id, exc)
                errors.append(str(exc))
        if errors:
            return SendResult(ok=False, error="; ".join(errors))
        return SendResult(ok=True)
