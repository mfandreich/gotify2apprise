from __future__ import annotations

import asyncio
import logging
from email import message_from_bytes
from email.message import Message

from aiosmtpd.controller import Controller

from gotify2apprise.listeners.base import OnMessage
from gotify2apprise.models.config import (
    ListenerConfig,
    SmtpOptions,
    mailbox_domain,
    mailbox_local_part,
    normalize_mailbox,
)
from gotify2apprise.models.message import NormalizedMessage

log = logging.getLogger(__name__)

# Mailrise-style local-part suffixes: alerts.high@host
MAILBOX_PRIORITY_SUFFIXES: dict[str, int] = {
    "low": 2,
    "info": 3,
    "normal": 5,
    "medium": 5,
    "warn": 6,
    "high": 8,
    "crit": 10,
}

_binds: dict[tuple[str, int], "_SmtpBind"] = {}


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


def match_mailbox(mailboxes: list[str], rcpt: str) -> tuple[bool, str | None, int | None, bool]:
    """Return (matched, mailbox, priority_override, exact_address).

    ``mailboxes`` entry with ``@`` is a full address. Without ``@`` it matches
    that local-part on any domain. Empty mailboxes = catch-all.
    """
    full = normalize_mailbox(rcpt)
    local = mailbox_local_part(rcpt)
    domain = mailbox_domain(rcpt)
    if not mailboxes:
        return True, full or None, None, False
    if full and full in mailboxes:
        return True, full, None, True
    if local and local in mailboxes:
        return True, local, None, False
    if "." in local:
        name, suffix = local.rsplit(".", 1)
        if suffix in MAILBOX_PRIORITY_SUFFIXES:
            prio = MAILBOX_PRIORITY_SUFFIXES[suffix]
            if domain:
                full_base = f"{name}@{domain}"
                if full_base in mailboxes:
                    return True, full_base, prio, True
            if name in mailboxes:
                return True, name, prio, False
    return False, None, None, False


def route_smtp_recipients(
    listeners: list[SmtpListener],
    rcpt_tos: list[str],
) -> list[tuple[SmtpListener, str, int | None]]:
    hits: list[tuple[SmtpListener, str, int | None]] = []
    seen: set[str] = set()
    for rcpt in rcpt_tos:
        exact: list[tuple[SmtpListener, str, int | None]] = []
        loose: list[tuple[SmtpListener, str, int | None]] = []
        for listener in listeners:
            ok, mailbox, priority, is_exact = match_mailbox(listener._opts.mailboxes, rcpt)
            if not ok:
                continue
            row = (listener, mailbox or normalize_mailbox(rcpt), priority)
            if is_exact:
                exact.append(row)
            else:
                loose.append(row)
        for listener, mailbox, priority in exact or loose:
            if listener.config.id in seen:
                continue
            seen.add(listener.config.id)
            hits.append((listener, mailbox, priority))
    return hits


class _Handler:
    def __init__(self, bind: _SmtpBind) -> None:
        self.bind = bind

    async def handle_DATA(self, server, session, envelope) -> str:  # noqa: ANN001
        return await self.bind.ingest(envelope.content, envelope.mail_from, envelope.rcpt_tos)


class _SmtpBind:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.listeners: list[SmtpListener] = []
        self._controller: Controller | None = None

    def add(self, listener: SmtpListener) -> None:
        if listener not in self.listeners:
            self.listeners.append(listener)
        if self._controller is not None:
            return
        hostname = listener._opts.hostname or None
        handler = _Handler(self)
        self._controller = Controller(
            handler,
            hostname=self.host,
            port=self.port,
            server_hostname=hostname,
        )
        self._controller.start()
        log.info(
            "SMTP bind %s:%s started (internal use only)",
            self.host,
            self.port,
        )

    def remove(self, listener: SmtpListener) -> None:
        self.listeners = [item for item in self.listeners if item is not listener]
        if self.listeners or self._controller is None:
            return
        self._controller.stop()
        self._controller = None
        log.info("SMTP bind %s:%s stopped", self.host, self.port)

    async def ingest(self, content: bytes, mail_from: str, rcpt_tos: list[str]) -> str:
        targets = route_smtp_recipients(self.listeners, rcpt_tos)
        if not targets:
            log.warning(
                "SMTP %s:%s: no mailbox for recipients %s",
                self.host,
                self.port,
                rcpt_tos,
            )
            return "550 5.1.1 Mailbox unavailable"
        try:
            for listener, mailbox, priority in targets:
                await listener.ingest(
                    content,
                    mail_from,
                    rcpt_tos,
                    mailbox=mailbox,
                    priority_override=priority,
                )
        except Exception:
            log.exception("SMTP %s:%s: ingest failed", self.host, self.port)
            return "451 Temporary local problem"
        return "250 OK"


def _bind_key(opts: SmtpOptions) -> tuple[str, int]:
    return (opts.host, opts.port)


class SmtpListener:
    """Internal-network SMTP sink. Do not expose to the public internet."""

    def __init__(self, config: ListenerConfig, on_message: OnMessage) -> None:
        self.config = config
        self._on_message = on_message
        self._opts = config.smtp()
        self._loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        key = _bind_key(self._opts)
        bind = _binds.get(key)
        if bind is None:
            bind = _SmtpBind(self._opts.host, self._opts.port)
            _binds[key] = bind
        bind.add(self)
        boxes = ",".join(self._opts.mailboxes) or "*"
        log.info(
            "listener %s: SMTP %s:%s mailboxes=[%s] (internal use only)",
            self.config.id,
            self._opts.host,
            self._opts.port,
            boxes,
        )

    async def stop(self) -> None:
        key = _bind_key(self._opts)
        bind = _binds.get(key)
        if bind is None:
            return
        bind.remove(self)
        if not bind.listeners:
            _binds.pop(key, None)

    async def ingest(
        self,
        content: bytes,
        mail_from: str,
        rcpt_tos: list[str],
        *,
        mailbox: str | None = None,
        priority_override: int | None = None,
    ) -> None:
        msg = message_from_bytes(content)
        title = str(msg.get("Subject") or "(no subject)")
        body = _body_from_email(msg)
        priority = (
            priority_override
            if priority_override is not None
            else _priority_from_email(msg, self._opts.default_priority)
        )
        matched = mailbox or (normalize_mailbox(rcpt_tos[0]) if rcpt_tos else "")
        message = NormalizedMessage(
            source_listener_id=self.config.id,
            title=title,
            body=body,
            priority=priority,
            raw={
                "mail_from": mail_from,
                "rcpt_tos": rcpt_tos,
                "subject": title,
                "mailbox": matched,
            },
            extra={"mail_from": mail_from, "appid": matched},
        )
        loop = self._loop
        if loop is None:
            await self._on_message(message)
            return
        future = asyncio.run_coroutine_threadsafe(self._on_message(message), loop)
        await asyncio.wrap_future(future)
