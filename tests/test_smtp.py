from email.message import EmailMessage

import pytest
from pydantic import ValidationError

from gotify2apprise.listeners.smtp import (
    SmtpListener,
    _body_from_email,
    _decode_header_value,
    _priority_from_email,
    match_mailbox,
    route_smtp_recipients,
)
from gotify2apprise.models.config import AppConfig, ListenerConfig
from gotify2apprise.models.message import NormalizedMessage


def test_priority_header() -> None:
    msg = EmailMessage()
    msg["X-Priority"] = "1"
    assert _priority_from_email(msg, 5) == 10
    msg2 = EmailMessage()
    assert _priority_from_email(msg2, 5) == 5


def test_plain_body() -> None:
    msg = EmailMessage()
    msg.set_content("hello world")
    assert "hello world" in _body_from_email(msg)


def test_decode_rfc2047_subject() -> None:
    encoded = (
        "=?utf-8?b?0KLQvtGA0YDQtdC90YIgwqtTa2V0Y2hVcC5Qcm8uMjAyNi4yNi4xLjI1"
        "NsK7INC30LDQstC10YDRiNC40Lsg0LfQsNCz0YDRg9C30LrRgw==?="
    )
    assert _decode_header_value(encoded) == (
        "Торрент «SketchUp.Pro.2026.26.1.256» завершил загрузку"
    )
    assert _decode_header_value("Disk full") == "Disk full"
    assert _decode_header_value("=?utf-8?q?Hello_=C2=ABWorld=C2=BB?=") == "Hello «World»"
    assert _decode_header_value(None) == ""
    assert _decode_header_value("  ") == ""


@pytest.mark.asyncio
async def test_ingest_subject() -> None:
    captured: list[NormalizedMessage] = []

    async def on_message(message: NormalizedMessage) -> None:
        captured.append(message)

    listener = SmtpListener(
        ListenerConfig(
            id="smtp-local",
            type="smtp",
            options={"host": "127.0.0.1", "port": 2525},
        ),
        on_message,
    )
    raw = b"From: a@b.c\r\nSubject: Disk full\r\n\r\nThe disk is full.\r\n"
    await listener.ingest(raw, "a@b.c", ["bridge@local"])
    assert captured[0].title == "Disk full"
    assert "disk is full" in captured[0].body.lower()
    assert captured[0].extra["appid"] == "bridge@local"


@pytest.mark.asyncio
async def test_ingest_rfc2047_subject() -> None:
    captured: list[NormalizedMessage] = []

    async def on_message(message: NormalizedMessage) -> None:
        captured.append(message)

    listener = SmtpListener(
        ListenerConfig(
            id="smtp-local",
            type="smtp",
            options={"host": "127.0.0.1", "port": 2525},
        ),
        on_message,
    )
    subject = (
        "=?utf-8?b?0KLQvtGA0YDQtdC90YIgwqtTa2V0Y2hVcC5Qcm8uMjAyNi4yNi4xLjI1"
        "NsK7INC30LDQstC10YDRiNC40Lsg0LfQsNCz0YDRg9C30LrRgw==?="
    )
    raw = f"From: a@b.c\r\nSubject: {subject}\r\n\r\nbody\r\n".encode()
    await listener.ingest(raw, "a@b.c", ["bridge@local"])
    assert captured[0].title == (
        "Торрент «SketchUp.Pro.2026.26.1.256» завершил загрузку"
    )
    assert captured[0].raw["subject"] == captured[0].title


def test_match_mailbox_and_priority_suffix() -> None:
    assert match_mailbox(["alerts"], "alerts@bridge.local") == (True, "alerts", None, False)
    assert match_mailbox(["alerts"], "ALERTS@x")[0] is True
    assert match_mailbox(["alerts"], "alerts.high@x") == (True, "alerts", 8, False)
    assert match_mailbox(["alerts"], "other@x") == (False, None, None, False)
    assert match_mailbox([], "anything@x")[0] is True


def test_match_full_address() -> None:
    boxes = ["alerts@bridge.local"]
    assert match_mailbox(boxes, "alerts@bridge.local") == (
        True,
        "alerts@bridge.local",
        None,
        True,
    )
    assert match_mailbox(boxes, "ALERTS@Bridge.Local")[0] is True
    assert match_mailbox(boxes, "alerts@other.local")[0] is False
    assert match_mailbox(boxes, "alerts.high@bridge.local") == (
        True,
        "alerts@bridge.local",
        8,
        True,
    )
    assert match_mailbox(boxes, "alerts.high@other.local")[0] is False
    cfg = ListenerConfig(
        id="smtp-full",
        type="smtp",
        options={"port": 2525, "mailboxes": ["alerts@bridge.local"]},
    )
    assert cfg.smtp().mailboxes == ["alerts@bridge.local"]


def test_full_address_wins_over_local_part() -> None:
    smtp_any = SmtpListener(
        ListenerConfig(
            id="smtp-any",
            type="smtp",
            options={"host": "0.0.0.0", "port": 2525, "mailboxes": ["alerts"]},
        ),
        _noop,
    )
    smtp_full = SmtpListener(
        ListenerConfig(
            id="smtp-full",
            type="smtp",
            options={
                "host": "0.0.0.0",
                "port": 2525,
                "mailboxes": ["alerts@bridge.local"],
            },
        ),
        _noop,
    )
    hits = route_smtp_recipients([smtp_any, smtp_full], ["alerts@bridge.local"])
    assert len(hits) == 1
    assert hits[0][0] is smtp_full


async def _noop(message: NormalizedMessage) -> None:
    return None


@pytest.mark.asyncio
async def test_route_shared_port_by_mailbox() -> None:
    captured: list[str] = []

    async def on_a(message: NormalizedMessage) -> None:
        captured.append(f"a:{message.extra['appid']}:{message.priority}")

    async def on_b(message: NormalizedMessage) -> None:
        captured.append(f"b:{message.extra['appid']}:{message.priority}")

    smtp_a = SmtpListener(
        ListenerConfig(
            id="smtp-a",
            type="smtp",
            options={"host": "0.0.0.0", "port": 2525, "mailboxes": ["alerts"]},
        ),
        on_a,
    )
    smtp_b = SmtpListener(
        ListenerConfig(
            id="smtp-b",
            type="smtp",
            options={"host": "0.0.0.0", "port": 2525, "mailboxes": ["uptime"]},
        ),
        on_b,
    )
    hits = route_smtp_recipients([smtp_a, smtp_b], ["uptime.high@lab"])
    assert len(hits) == 1
    assert hits[0][0] is smtp_b
    await smtp_b.ingest(b"Subject: x\r\n\r\nbody\r\n", "n@e", ["uptime.high@lab"], mailbox="uptime", priority_override=8)
    assert captured == ["b:uptime:8"]


def _two_smtp(**kwargs: object) -> dict:
    base = {
        "version": 2,
        "listeners": [
            {
                "id": "smtp-a",
                "type": "smtp",
                "options": {"host": "0.0.0.0", "port": 2525, "mailboxes": ["alerts"]},
            },
            {
                "id": "smtp-b",
                "type": "smtp",
                "options": {"host": "0.0.0.0", "port": 2525, "mailboxes": ["uptime"]},
            },
        ],
        "receivers": [
            {"id": "out", "type": "apprise", "options": {"urls": ["json://localhost"]}}
        ],
        "routes": [
            {
                "id": "r1",
                "from": {"listeners": ["smtp-a"]},
                "to": {"receivers": ["out"]},
            }
        ],
    }
    base.update(kwargs)
    return base


def test_shared_port_requires_mailboxes() -> None:
    with pytest.raises(ValidationError, match="empty mailboxes"):
        AppConfig.model_validate(
            _two_smtp(
                listeners=[
                    {"id": "smtp-a", "type": "smtp", "options": {"port": 2525}},
                    {"id": "smtp-b", "type": "smtp", "options": {"port": 2525}},
                ]
            )
        )


def test_shared_port_rejects_overlapping_mailboxes() -> None:
    with pytest.raises(ValidationError, match="mailbox 'alerts'"):
        AppConfig.model_validate(
            _two_smtp(
                listeners=[
                    {
                        "id": "smtp-a",
                        "type": "smtp",
                        "options": {"port": 2525, "mailboxes": ["alerts"]},
                    },
                    {
                        "id": "smtp-b",
                        "type": "smtp",
                        "options": {"port": 2525, "mailboxes": ["alerts"]},
                    },
                ]
            )
        )


def test_shared_port_ok() -> None:
    cfg = AppConfig.model_validate(_two_smtp())
    assert cfg.listeners[0].smtp().mailboxes == ["alerts"]


def test_config_keeps_full_mailbox() -> None:
    cfg = ListenerConfig(
        id="smtp-a",
        type="smtp",
        options={"port": 2525, "mailboxes": ["Alerts@Bridge.Local"]},
    )
    assert cfg.smtp().mailboxes == ["alerts@bridge.local"]
