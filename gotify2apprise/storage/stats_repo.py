from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from gotify2apprise.storage.db import Database


class StatsRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def increment(self, listener_id: str, receiver_id: str, *, ok: bool) -> None:
        day = datetime.now(timezone.utc).date().isoformat()
        column = "sent_ok" if ok else "sent_fail"
        await self.db.conn.execute(
            f"""
            INSERT INTO stats_daily(date, listener_id, receiver_id, sent_ok, sent_fail)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(date, listener_id, receiver_id) DO UPDATE SET
                {column} = {column} + 1
            """,
            (day, listener_id, receiver_id, 1 if ok else 0, 0 if ok else 1),
        )
        await self.db.conn.commit()

    async def range_days(self, days: int = 7) -> list[dict[str, Any]]:
        start = (datetime.now(timezone.utc) - timedelta(days=days - 1)).date().isoformat()
        cursor = await self.db.conn.execute(
            """
            SELECT date, listener_id, receiver_id, sent_ok, sent_fail
            FROM stats_daily
            WHERE date >= ?
            ORDER BY date ASC
            """,
            (start,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def totals(self, days: int = 1) -> dict[str, int]:
        rows = await self.range_days(days)
        ok = sum(int(r["sent_ok"]) for r in rows)
        fail = sum(int(r["sent_fail"]) for r in rows)
        return {"sent_ok": ok, "sent_fail": fail}
