from pathlib import Path

import pytest

from gotify2apprise.models.config import DeliveryPolicy
from gotify2apprise.models.message import NormalizedMessage
from gotify2apprise.storage.auth_repo import AuthRepo
from gotify2apprise.storage.db import Database
from gotify2apprise.storage.messages_repo import MessagesRepo
from gotify2apprise.storage.queue import DeliveryQueue


@pytest.mark.asyncio
async def test_message_and_delivery_roundtrip(tmp_path: Path) -> None:
    db = Database(tmp_path / "t.db")
    await db.connect()
    messages = MessagesRepo(db)
    queue = DeliveryQueue(db)
    msg = NormalizedMessage(
        source_listener_id="gotify-main",
        title="t",
        body="b",
        priority=5,
    )
    await messages.insert(msg)
    policy = DeliveryPolicy(max_attempts=2, initial_delay_sec=1, backoff="fixed")
    did = await queue.enqueue(
        message_id=msg.id,
        receiver_id="telegram",
        route_id="r1",
        title="t",
        body="b",
        policy=policy,
    )
    due = await queue.due()
    assert due and due[0]["id"] == did
    status = await queue.mark_failure(did, "boom", due[0])
    assert status == "failed"
    due2 = await queue.due()
    assert due2 == []
    await queue.retry_now(did)
    due3 = await queue.due()
    assert due3 and due3[0]["attempt"] == 0
    await db.close()


@pytest.mark.asyncio
async def test_auth_bootstrap(tmp_path: Path) -> None:
    db = Database(tmp_path / "t.db")
    await db.connect()
    auth = AuthRepo(db)
    await auth.upsert_user("admin", "secretsecret")
    assert await auth.verify("admin", "secretsecret")
    assert not await auth.verify("admin", "nope")
    assert not await auth.verify("other", "secretsecret")
    await db.close()
