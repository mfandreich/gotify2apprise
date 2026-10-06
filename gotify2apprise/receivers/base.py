from __future__ import annotations

from typing import Protocol

from gotify2apprise.models.config import ReceiverConfig
from gotify2apprise.models.message import SendResult


class Receiver(Protocol):
    config: ReceiverConfig

    async def send(self, title: str, body: str, priority: int) -> SendResult: ...
