from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from gotify2apprise.models.config import DeliveryPolicy
from gotify2apprise.storage.db import Database


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


class DeliveryQueue:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def enqueue(
        self,
        *,
        message_id: str,
        receiver_id: str,
        route_id: str,
        title: str,
        body: str,
        policy: DeliveryPolicy,
    ) -> str:
        delivery_id = str(uuid4())
        now = datetime.now(timezone.utc)
        await self.db.conn.execute(
            """
            INSERT INTO deliveries(
                id, message_id, receiver_id, route_id, title, body, status,
                attempt, max_attempts, initial_delay_sec, backoff, max_delay_sec,
                last_error, next_retry_at, completed_at, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, 'pending', 0, ?, ?, ?, ?, NULL, ?, NULL, ?)
            """,
            (
                delivery_id,
                message_id,
                receiver_id,
                route_id,
                title,
                body,
                policy.max_attempts,
                policy.initial_delay_sec,
                policy.backoff,
                policy.max_delay_sec,
                _iso(now),
                _iso(now),
            ),
        )
        await self.db.conn.commit()
        return delivery_id

    async def due(self, limit: int = 20) -> list[dict[str, Any]]:
        now = _iso(datetime.now(timezone.utc))
        cursor = await self.db.conn.execute(
            """
            SELECT d.*, m.listener_id, m.priority
            FROM deliveries d
            JOIN messages m ON m.id = d.message_id
            WHERE d.status IN ('pending', 'failed')
              AND (d.next_retry_at IS NULL OR d.next_retry_at <= ?)
            ORDER BY d.next_retry_at ASC
            LIMIT ?
            """,
            (now, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def mark_success(self, delivery_id: str) -> None:
        now = _iso(datetime.now(timezone.utc))
        await self.db.conn.execute(
            """
            UPDATE deliveries
            SET status = 'success', completed_at = ?, last_error = NULL,
                attempt = attempt + 1
            WHERE id = ?
            """,
            (now, delivery_id),
        )
        await self.db.conn.commit()

    async def mark_failure(self, delivery_id: str, error: str, row: dict[str, Any]) -> str:
        attempt = int(row["attempt"]) + 1
        max_attempts = int(row["max_attempts"])
        now = datetime.now(timezone.utc)
        if attempt >= max_attempts:
            await self.db.conn.execute(
                """
                UPDATE deliveries
                SET status = 'dead', attempt = ?, last_error = ?, completed_at = ?,
                    next_retry_at = NULL
                WHERE id = ?
                """,
                (attempt, error, _iso(now), delivery_id),
            )
            await self.db.conn.commit()
            return "dead"
        delay = next_delay(row, attempt)
        nxt = now + timedelta(seconds=delay)
        await self.db.conn.execute(
            """
            UPDATE deliveries
            SET status = 'failed', attempt = ?, last_error = ?, next_retry_at = ?
            WHERE id = ?
            """,
            (attempt, error, _iso(nxt), delivery_id),
        )
        await self.db.conn.commit()
        return "failed"

    async def retry_now(self, delivery_id: str) -> None:
        now = _iso(datetime.now(timezone.utc))
        await self.db.conn.execute(
            """
            UPDATE deliveries
            SET status = 'pending', attempt = 0, next_retry_at = ?, completed_at = NULL
            WHERE id = ?
            """,
            (now, delivery_id),
        )
        await self.db.conn.commit()

    async def list_recent(
        self,
        *,
        limit: int = 100,
        status: str | None = None,
        receiver_id: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses = ["1=1"]
        args: list[Any] = []
        if status:
            clauses.append("d.status = ?")
            args.append(status)
        if receiver_id:
            clauses.append("d.receiver_id = ?")
            args.append(receiver_id)
        sql = (
            "SELECT d.*, m.listener_id, m.priority, m.received_at AS message_received_at "
            "FROM deliveries d JOIN messages m ON m.id = d.message_id "
            f"WHERE {' AND '.join(clauses)} "
            "ORDER BY d.created_at DESC LIMIT ?"
        )
        args.append(limit)
        cursor = await self.db.conn.execute(sql, args)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def counts(self) -> dict[str, int]:
        cursor = await self.db.conn.execute(
            "SELECT status, COUNT(*) AS n FROM deliveries GROUP BY status"
        )
        rows = await cursor.fetchall()
        result = {"pending": 0, "failed": 0, "success": 0, "dead": 0}
        for row in rows:
            result[str(row["status"])] = int(row["n"])
        return result


def next_delay(row: dict[str, Any], attempt: int) -> int:
    initial = int(row["initial_delay_sec"])
    cap = int(row["max_delay_sec"])
    backoff = str(row["backoff"])
    if backoff == "fixed":
        return min(initial, cap)
    return min(initial * (2 ** max(attempt - 1, 0)), cap)


def next_retry_at(policy: DeliveryPolicy, attempt: int, now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    dummy = {
        "initial_delay_sec": policy.initial_delay_sec,
        "max_delay_sec": policy.max_delay_sec,
        "backoff": policy.backoff,
    }
    return now + timedelta(seconds=next_delay(dummy, attempt))
