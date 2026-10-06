from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

DEFAULT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

_TIME_KEYS = ("created_at", "completed_at", "next_retry_at", "message_received_at")


def format_datetime(value: datetime | str | None, fmt: str | None = None) -> str:
    """Format a UTC datetime for the UI.

    ``%f`` is milliseconds with three digits (not Python microseconds).
    """
    pattern = fmt or DEFAULT_DATETIME_FORMAT
    dt = _parse(value)
    if dt is None:
        return "" if value is None else str(value)
    try:
        return dt.strftime(_expand_milliseconds(pattern, dt))
    except ValueError:
        return dt.isoformat()


def datetime_format_from_config(config: Any | None) -> str:
    if config is None:
        return DEFAULT_DATETIME_FORMAT
    defaults = getattr(config, "defaults", None)
    pattern = getattr(defaults, "datetime_format", None)
    return pattern or DEFAULT_DATETIME_FORMAT


def format_delivery_rows(rows: list[dict[str, Any]], fmt: str | None = None) -> list[dict[str, Any]]:
    pattern = fmt or DEFAULT_DATETIME_FORMAT
    formatted: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        for key in _TIME_KEYS:
            if item.get(key):
                item[key] = format_datetime(item[key], pattern)
        formatted.append(item)
    return formatted


def _parse(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _expand_milliseconds(fmt: str, dt: datetime) -> str:
    ms = f"{dt.microsecond // 1000:03d}"
    out: list[str] = []
    i = 0
    while i < len(fmt):
        if fmt[i] == "%" and i + 1 < len(fmt):
            nxt = fmt[i + 1]
            if nxt == "%":
                out.append("%%")
                i += 2
                continue
            if nxt == "f":
                out.append(ms)
                i += 2
                continue
        out.append(fmt[i])
        i += 1
    return "".join(out)
