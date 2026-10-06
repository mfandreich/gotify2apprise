from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path


def _truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


@dataclass
class Settings:
    conf_file: Path
    data_dir: Path
    ui_host: str
    ui_port: int
    storage_secret: str
    admin_user: str | None
    admin_password: str | None
    auto_migrate_v1: bool
    message_retention_days: int
    max_messages_per_channel: int
    title_template: str | None
    message_template: str | None

    @property
    def db_path(self) -> Path:
        return self.data_dir / "bridge.db"

    @classmethod
    def from_env(cls) -> Settings:
        data_dir = Path(os.environ.get("DATA_DIR", "/var/lib/gotify2apprise"))
        data_dir.mkdir(parents=True, exist_ok=True)

        secret = os.environ.get("STORAGE_SECRET")
        if not secret:
            secret_file = data_dir / ".storage_secret"
            if secret_file.exists():
                secret = secret_file.read_text(encoding="utf-8").strip()
            else:
                secret = secrets.token_hex(32)
                secret_file.write_text(secret, encoding="utf-8")

        return cls(
            conf_file=Path(
                os.environ.get("CONF_FILE", "/etc/gotify2apprise/config.yaml")
            ),
            data_dir=data_dir,
            ui_host=os.environ.get("UI_HOST", "0.0.0.0"),
            ui_port=_int_env("UI_PORT", 8080),
            storage_secret=secret,
            admin_user=os.environ.get("ADMIN_USER") or None,
            admin_password=os.environ.get("ADMIN_PASSWORD") or None,
            auto_migrate_v1=_truthy(os.environ.get("AUTO_MIGRATE_V1")),
            message_retention_days=_int_env("MESSAGE_RETENTION_DAYS", 30),
            max_messages_per_channel=_int_env("MAX_MESSAGES_PER_CHANNEL", 500),
            title_template=os.environ.get("TITLE_TEMPLATE"),
            message_template=os.environ.get("MESSAGE_TEMPLATE"),
        )
