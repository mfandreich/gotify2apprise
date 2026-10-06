from __future__ import annotations

import asyncio
import logging
from email import message_from_bytes
from email.message import Message

from aiosmtpd.controller import Controller

from gotify2apprise.listeners.base import OnMessage
from gotify2apprise.models.config import ListenerConfig
from gotify2apprise.models.message import NormalizedMessage

log = logging.getLogger(__name__)


def _body_from_email(msg: Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain" and part.get_payload(decode=True):
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace")
        for part in msg.walk():
            if part.get_content_type() == "text/html" and part.get_payload(decode=True):
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace")
        return ""
    payload = msg.get_payload(decode=True)
    if not payload:
        return str(msg.get_payload() or "")
    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _priority_from_email(msg: Message, default: int) -> int:
    raw = msg.get("X-Priority") or msg.get("Priority") or ""
    raw = str(raw).strip()
    if not raw:
        return default
    try:
        value = int(raw[0])
    except ValueError:
        return default
    mapping = {1: 10, 2: 8, 3: 5, 4: 3, 5: 0}
    return mapping.get(value, default)


class _Handler:
    def __init__(self, listener: SmtpListener) -> None:
        self.listener = listener

    async def handle_DATA(self, server, session, envelope) -> str:  # noqa: ANN001
        try:
            await self.listener.ingest(envelope.content, envelope.mail_from, envelope.rcpt_tos)
        except Exception:
            log.exception("listener %s: SMTP ingest failed", self.listener.config.id)
            return "451 Temporary local problem"
        return "250 OK"


class SmtpListener:
    """Internal-network SMTP sink. Do not expose to the public internet."""

    def __init__(self, config: ListenerConfig, on_message: OnMessage) -> None:
        self.config = config
        self._on_message = on_message
        self._opts = config.smtp()
        self._controller: Controller | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        handler = _Handler(self)
        self._controller = Controller(
            handler,
            hostname=self._opts.host,
            port=self._opts.port,
            server_hostname=self._opts.hostname or None,
        )
        self._controller.start()
        log.info(
            "listener %s: SMTP listening on %s:%s (internal use only)",
            self.config.id,
            self._opts.host,
            self._opts.port,
        )

    async def stop(self) -> None:
        if self._controller:
            self._controller.stop()
            self._controller = None

    async def ingest(self, content: bytes, mail_from: str, rcpt_tos: list[str]) -> None:
        msg = message_from_bytes(content)
        title = str(msg.get("Subject") or "(no subject)")
        body = _body_from_email(msg)
        priority = _priority_from_email(msg, self._opts.default_priority)
        message = NormalizedMessage(
            source_listener_id=self.config.id,
            title=title,
            body=body,
            priority=priority,
            raw={
                "mail_from": mail_from,
                "rcpt_tos": rcpt_tos,
                "subject": title,
            },
            extra={"mail_from": mail_from, "appid": ""},
        )
        loop = self._loop
        if loop is None:
            await self._on_message(message)
            return
        future = asyncio.run_coroutine_threadsafe(self._on_message(message), loop)
        await asyncio.wrap_future(future)
