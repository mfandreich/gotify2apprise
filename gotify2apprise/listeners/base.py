from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from gotify2apprise.models.config import ListenerConfig
from gotify2apprise.models.message import NormalizedMessage

OnMessage = Callable[[NormalizedMessage], Awaitable[None]]


class Listener(Protocol):
    config: ListenerConfig

    async def start(self) -> None: ...

    async def stop(self) -> None: ...
