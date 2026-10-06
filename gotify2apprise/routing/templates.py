from __future__ import annotations

from gotify2apprise.models.config import priority_bucket
from gotify2apprise.models.message import NormalizedMessage


def render_template(template: str, message: NormalizedMessage) -> str:
    result = template
    result = result.replace("$priorityStr", priority_bucket(message.priority))
    result = result.replace("$priority", str(message.priority))
    result = result.replace("$appid", str(message.extra.get("appid", "")))
    result = result.replace("$title", message.title)
    result = result.replace("$message", message.body)
    return result
