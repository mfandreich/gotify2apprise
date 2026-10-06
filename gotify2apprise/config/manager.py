from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from gotify2apprise.config.env_subst import substitute
from gotify2apprise.config.yaml_io import atomic_write, dump_yaml
from gotify2apprise.legacy.migrate_v1 import convert_v1, is_v1_config
from gotify2apprise.models.config import AppConfig
from gotify2apprise.settings import Settings


class ConfigError(Exception):
    pass


class ConfigV1Error(ConfigError):
    pass


def backup_v1_path(conf: Path) -> Path:
    bak = Path(str(conf) + ".bak.v1")
    if not bak.exists():
        return bak
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return Path(str(conf) + f".bak.v1.{stamp}")


class ConfigManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.path = settings.conf_file
        self._snapshot: AppConfig | None = None

    @property
    def snapshot(self) -> AppConfig | None:
        return self._snapshot

    def read_raw(self) -> Any:
        if not self.path.exists():
            raise ConfigError(f"config file not found: {self.path}")
        text = self.path.read_text(encoding="utf-8")
        return yaml.safe_load(text)

    def detect_v1(self, raw: Any | None = None) -> bool:
        if raw is None:
            raw = self.read_raw()
        return is_v1_config(raw)

    def migrate_inplace(self, raw: Any | None = None) -> AppConfig:
        if raw is None:
            raw = self.read_raw()
        if not is_v1_config(raw):
            raise ConfigError("AUTO_MIGRATE_V1 set but config is not v1")
        converted = convert_v1(raw, self.settings)
        backup = backup_v1_path(self.path)
        backup.write_text(self.path.read_text(encoding="utf-8"), encoding="utf-8")
        atomic_write(self.path, dump_yaml(converted))
        return self.parse(converted, substitute_env=True)

    def parse(self, raw: Any, *, substitute_env: bool = True) -> AppConfig:
        if raw is None:
            raise ConfigError("config is empty")
        if is_v1_config(raw):
            raise ConfigV1Error(
                "Config v1 detected. Run: python -m gotify2apprise.legacy.migrate_v1 "
                f"--in-place {self.path}  (or set AUTO_MIGRATE_V1=true)"
            )
        if not isinstance(raw, dict) or raw.get("version") != 2:
            raise ConfigError("unsupported config: expected version: 2")
        data = substitute(raw) if substitute_env else raw
        data = self._apply_env_template_defaults(data)
        try:
            config = AppConfig.model_validate(data)
        except Exception as exc:
            raise ConfigError(str(exc)) from exc
        return config

    def _apply_env_template_defaults(self, data: dict[str, Any]) -> dict[str, Any]:
        defaults = dict(data.get("defaults") or {})
        if self.settings.title_template and "title_template" not in defaults:
            defaults["title_template"] = self.settings.title_template
        if self.settings.message_template and "message_template" not in defaults:
            defaults["message_template"] = self.settings.message_template
        if defaults:
            data = dict(data)
            data["defaults"] = defaults
        return data

    def load(self) -> AppConfig:
        raw = self.read_raw()
        if is_v1_config(raw):
            if not self.settings.auto_migrate_v1:
                raise ConfigV1Error(
                    "Config v1 detected. Run: python -m gotify2apprise.legacy.migrate_v1 "
                    f"--in-place {self.path}  (or set AUTO_MIGRATE_V1=true)"
                )
            config = self.migrate_inplace(raw)
        else:
            config = self.parse(raw)
        self._snapshot = config
        return config

    def validate_text(self, text: str) -> AppConfig:
        raw = yaml.safe_load(text)
        return self.parse(raw)

    def save_text(self, text: str) -> AppConfig:
        config = self.validate_text(text)
        if self.path.exists():
            bak = Path(str(self.path) + ".bak")
            bak.write_text(self.path.read_text(encoding="utf-8"), encoding="utf-8")
        atomic_write(self.path, text if text.endswith("\n") else text + "\n")
        self._snapshot = config
        return config

    def dumps(self, config: AppConfig | None = None) -> str:
        target = config or self._snapshot
        if target is None:
            raise ConfigError("no config loaded")
        data = target.model_dump(by_alias=True, exclude_none=True)
        return dump_yaml(data)
