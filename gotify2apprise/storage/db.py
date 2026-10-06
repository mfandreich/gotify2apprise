from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    listener_id TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    priority INTEGER NOT NULL,
    raw TEXT NOT NULL,
    extra TEXT NOT NULL,
    received_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS deliveries (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL,
    receiver_id TEXT NOT NULL,
    route_id TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL,
    attempt INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    initial_delay_sec INTEGER NOT NULL DEFAULT 30,
    backoff TEXT NOT NULL DEFAULT 'exponential',
    max_delay_sec INTEGER NOT NULL DEFAULT 3600,
    last_error TEXT,
    next_retry_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS stats_daily (
    date TEXT NOT NULL,
    listener_id TEXT NOT NULL,
    receiver_id TEXT NOT NULL,
    sent_ok INTEGER NOT NULL DEFAULT 0,
    sent_fail INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (date, listener_id, receiver_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_received ON messages(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_listener ON messages(listener_id, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_deliveries_due ON deliveries(status, next_retry_at);
CREATE INDEX IF NOT EXISTS idx_deliveries_message ON deliveries(message_id);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("database is not connected")
        return self._conn

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.execute("PRAGMA journal_mode = WAL")
        await self._conn.executescript(_SCHEMA)
        await self._conn.commit()
        await self._set_version()
        log.info("sqlite ready at %s", self.path)

    async def _set_version(self) -> None:
        await self.conn.execute(
            "INSERT INTO meta(key, value) VALUES('schema_version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(SCHEMA_VERSION),),
        )
        await self.conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
