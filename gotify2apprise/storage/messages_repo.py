from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from gotify2apprise.models.message import NormalizedMessage
from gotify2apprise.storage.db import Database


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


class MessagesRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def insert(self, message: NormalizedMessage) -> None:
        await self.db.conn.execute(
            "INSERT INTO messages(id, listener_id, title, body, priority, raw, extra, received_at) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            (
                message.id,
                message.source_listener_id,
                message.title,
                message.body,
                message.priority,
                json.dumps(message.raw, default=str),
                json.dumps(message.extra, default=str),
                _iso(message.received_at),
            ),
        )
        await self.db.conn.commit()

    async def get(self, message_id: str) -> dict[str, Any] | None:
        cursor = await self.db.conn.execute(
            "SELECT * FROM messages WHERE id = ?",
            (message_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def list_recent(
        self,
        *,
        limit: int = 100,
        listener_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if listener_id:
            cursor = await self.db.conn.execute(
                "SELECT * FROM messages WHERE listener_id = ? ORDER BY received_at DESC LIMIT ?",
                (listener_id, limit),
            )
        else:
            cursor = await self.db.conn.execute(
                "SELECT * FROM messages ORDER BY received_at DESC LIMIT ?",
                (limit,),
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def prune(self, *, retention_days: int, max_per_channel: int) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        await self.db.conn.execute(
            "DELETE FROM messages WHERE received_at < ?",
            (_iso(cutoff),),
        )
        cursor = await self.db.conn.execute(
            "SELECT DISTINCT listener_id FROM messages"
        )
        listeners = [row["listener_id"] for row in await cursor.fetchall()]
        for listener_id in listeners:
            await self.db.conn.execute(
                """
                DELETE FROM messages WHERE id IN (
                    SELECT id FROM messages
                    WHERE listener_id = ?
                    ORDER BY received_at DESC
                    LIMIT -1 OFFSET ?
                )
                """,
                (listener_id, max_per_channel),
            )
        await self.db.conn.commit()
