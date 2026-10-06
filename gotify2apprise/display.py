from __future__ import annotations

from typing import Any

from gotify2apprise.datetime_fmt import DEFAULT_DATETIME_FORMAT, format_delivery_rows
from gotify2apprise.models.config import priority_bucket

TITLE_MAX_CHARS = 40
DELIVERY_PAGE_SIZE = 25
PRIORITY_ICONS = {"info": "info", "warn": "warning", "crit": "error"}


def as_plain_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def truncate_title(value: object, max_chars: int = TITLE_MAX_CHARS) -> str:
    text = " ".join(as_plain_text(value).split())
    if max_chars < 1 or len(text) <= max_chars:
        return text
    if max_chars == 1:
        return "…"
    return text[: max_chars - 1].rstrip() + "…"


def present_delivery_rows(
    rows: list[dict[str, Any]],
    fmt: str | None = None,
) -> list[dict[str, Any]]:
    presented: list[dict[str, Any]] = []
    for row in format_delivery_rows(rows, fmt or DEFAULT_DATETIME_FORMAT):
        item = dict(row)
        title = as_plain_text(item.get("title"))
        body = as_plain_text(item.get("body"))
        try:
            priority = int(item.get("priority") or 0)
        except (TypeError, ValueError):
            priority = 0
        bucket = priority_bucket(priority)
        item["title_full"] = title
        item["body_full"] = body
        item["title"] = truncate_title(title)
        item["priority"] = priority
        item["priority_bucket"] = bucket
        item["priority_label"] = bucket
        item["priority_icon"] = PRIORITY_ICONS.get(bucket, "info")
        item.pop("body", None)
        presented.append(item)
    return presented
