from pathlib import Path

import yaml

from gotify2apprise.config.manager import ConfigManager, ConfigV1Error
from gotify2apprise.legacy.migrate_v1 import convert_v1, is_v1_config
from gotify2apprise.models.config import AppConfig
from gotify2apprise.settings import Settings

V1 = {
    "applications": [
        {
            "tokens": ["all"],
            "receivers": [
                {"urls": ["tgram://bot/chat"]},
                {"urls": ["mailto://a:b@example.com"], "minPriority": 4},
            ],
        },
        {
            "tokens": ["APP1", "APP2"],
            "receivers": [
                {
                    "urls": ["discord://id/token"],
                    "priorities": ["info", 9, 10],
                    "titleTemplate": "[$priorityStr] $title",
                }
            ],
        },
    ]
}


def test_is_v1() -> None:
    assert is_v1_config(V1)
    assert not is_v1_config({"version": 2, "listeners": []})


def test_convert_structure() -> None:
    v2 = convert_v1(V1)
    cfg = AppConfig.model_validate(
        yaml.safe_load(
            yaml.safe_dump(v2).replace("${GOTIFY_HOST}", "localhost").replace(
                "${GOTIFY_TOKEN}", "tok"
            )
        )
    )
    assert len(cfg.listeners) == 2
    assert cfg.listeners[0].gotify().app_tokens == ["all"]
    assert cfg.listeners[1].gotify().app_tokens == ["APP1", "APP2"]
    assert len(cfg.receivers) == 3
    assert len(cfg.routes) == 3
    assert cfg.routes[1].filter is not None
    assert cfg.routes[1].filter.min_priority == 4
    assert cfg.routes[2].templates is not None
    assert cfg.routes[2].templates.title == "[$priorityStr] $title"


def _settings(tmp: Path, *, auto: bool = False) -> Settings:
    return Settings(
        conf_file=tmp / "config.yaml",
        data_dir=tmp / "data",
        ui_host="127.0.0.1",
        ui_port=8080,
        storage_secret="test-secret",
        admin_user="admin",
        admin_password="secretsecret",
        auto_migrate_v1=auto,
        message_retention_days=30,
        max_messages_per_channel=500,
        title_template=None,
        message_template=None,
    )


def test_auto_migrate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GOTIFY_HOST", "gotify.local")
    monkeypatch.setenv("GOTIFY_TOKEN", "client")
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(V1), encoding="utf-8")
    mgr = ConfigManager(_settings(tmp_path, auto=True))
    cfg = mgr.load()
    assert cfg.version == 2
    assert path.with_name("config.yaml.bak.v1").exists() or Path(str(path) + ".bak.v1").exists()
    reloaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert reloaded["version"] == 2


def test_v1_without_flag_raises(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(V1), encoding="utf-8")
    mgr = ConfigManager(_settings(tmp_path, auto=False))
    try:
        mgr.load()
    except ConfigV1Error:
        return
    raise AssertionError("expected ConfigV1Error")
