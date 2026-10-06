from __future__ import annotations

import bcrypt

from gotify2apprise.storage.db import Database


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


class AuthRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def get_user(self) -> tuple[str, str] | None:
        cursor = await self.db.conn.execute(
            "SELECT username, password_hash FROM user WHERE id = 1"
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return str(row["username"]), str(row["password_hash"])

    async def upsert_user(self, username: str, password: str) -> None:
        password_hash = hash_password(password)
        await self.db.conn.execute(
            "INSERT INTO user(id, username, password_hash) VALUES(1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET username=excluded.username, "
            "password_hash=excluded.password_hash",
            (username, password_hash),
        )
        await self.db.conn.commit()

    async def update_password(self, password: str) -> None:
        password_hash = hash_password(password)
        await self.db.conn.execute(
            "UPDATE user SET password_hash = ? WHERE id = 1",
            (password_hash,),
        )
        await self.db.conn.commit()

    async def verify(self, username: str, password: str) -> bool:
        user = await self.get_user()
        if user is None:
            return False
        stored_name, stored_hash = user
        if stored_name != username:
            return False
        return verify_password(password, stored_hash)
