from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class NormalizedMessage:
    source_listener_id: str
    title: str
    body: str
    priority: int
    id: str = field(default_factory=lambda: str(uuid4()))
    raw: dict[str, Any] = field(default_factory=dict)
    received_at: datetime = field(default_factory=utcnow)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class SendResult:
    ok: bool
    error: str | None = None
