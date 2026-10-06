from email.message import EmailMessage

import pytest

from gotify2apprise.listeners.smtp import SmtpListener, _body_from_email, _priority_from_email
from gotify2apprise.models.config import ListenerConfig
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
