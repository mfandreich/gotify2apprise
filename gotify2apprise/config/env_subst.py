from __future__ import annotations

import os
import re
from typing import Any

_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def substitute(value: Any, env: dict[str, str] | None = None) -> Any:
    """Replace ${VAR} and ${VAR:-default} in strings, recursively."""
    mapping = os.environ if env is None else env
    if isinstance(value, str):
        def repl(match: re.Match[str]) -> str:
            name = match.group(1)
            default = match.group(2)
            if name in mapping:
                return mapping[name]
            if default is not None:
                return default
            return ""

        return _PATTERN.sub(repl, value)
    if isinstance(value, dict):
        return {k: substitute(v, env=dict(mapping)) for k, v in value.items()}
    if isinstance(value, list):
        return [substitute(v, env=dict(mapping)) for v in value]
    return value
