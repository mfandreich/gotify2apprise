from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def dump_yaml(data: dict[str, Any]) -> str:
    return yaml.safe_dump(
        data,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
    )


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
