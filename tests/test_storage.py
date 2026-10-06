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
async def test_unlimited_attempts_never_dead(tmp_path: Path) -> None:
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
    policy = DeliveryPolicy(max_attempts=0, initial_delay_sec=1, backoff="fixed")
    did = await queue.enqueue(
        message_id=msg.id,
        receiver_id="telegram",
        route_id="r1",
        title="t",
        body="b",
        policy=policy,
    )
    row = (await queue.due())[0]
    for _ in range(8):
        status = await queue.mark_failure(did, "boom", row)
        assert status == "failed"
        row = dict(row)
        row["attempt"] = int(row["attempt"]) + 1
    stored = (await queue.list_recent(limit=1))[0]
    assert stored["status"] == "failed"
    assert stored["attempt"] == 8
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


@pytest.mark.asyncio
async def test_list_recent_offset_and_count(tmp_path: Path) -> None:
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
    ids = [
        await queue.enqueue(
            message_id=msg.id,
            receiver_id="telegram",
            route_id="r1",
            title=f"t{i}",
            body="b",
            policy=policy,
        )
        for i in range(3)
    ]
    page1 = await queue.list_recent(limit=2, offset=0)
    page2 = await queue.list_recent(limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 1
    assert {row["id"] for row in page1 + page2} == set(ids)
    assert await queue.count_deliveries() == 3
    await db.close()


@pytest.mark.asyncio
async def test_delivery_list_filters(tmp_path: Path) -> None:
    db = Database(tmp_path / "t.db")
    await db.connect()
    messages = MessagesRepo(db)
    queue = DeliveryQueue(db)
    policy = DeliveryPolicy(max_attempts=2, initial_delay_sec=1, backoff="fixed")
    low = NormalizedMessage(source_listener_id="smtp-a", title="lo", body="b", priority=1)
    high = NormalizedMessage(source_listener_id="smtp-b", title="hi", body="b", priority=10)
    await messages.insert(low)
    await messages.insert(high)
    await queue.enqueue(
        message_id=low.id, receiver_id="to-a", route_id="r1", title="lo", body="b", policy=policy
    )
    await queue.enqueue(
        message_id=high.id, receiver_id="to-b", route_id="r2", title="hi", body="b", policy=policy
    )
    assert await queue.count_deliveries(listener_id="smtp-a") == 1
    assert await queue.count_deliveries(receiver_id="to-b") == 1
    assert await queue.count_deliveries(priority_bucket="info") == 1
    assert await queue.count_deliveries(priority_bucket="crit") == 1
    assert await queue.count_deliveries(priority_bucket="warn") == 0
    rows = await queue.list_recent(listener_id="smtp-b", priority_bucket="crit")
    assert len(rows) == 1
    assert rows[0]["receiver_id"] == "to-b"
    await db.close()
