from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from gotify2apprise.config.yaml_io import dump_yaml
from gotify2apprise.settings import Settings


def is_v1_config(raw: Any) -> bool:
    if not isinstance(raw, dict):
        return False
    if raw.get("version") == 2:
        return False
    if "listeners" in raw:
        return False
    return "applications" in raw


def _receiver_id(index: int) -> str:
    return f"apprise-{index}"


def convert_v1(raw: dict[str, Any], settings: Settings | None = None) -> dict[str, Any]:
    applications = raw.get("applications") or []
    listeners: list[dict[str, Any]] = []
    receivers: list[dict[str, Any]] = []
    routes: list[dict[str, Any]] = []
    receiver_index = 0

    host = "${GOTIFY_HOST}"
    token = "${GOTIFY_TOKEN}"

    for i, block in enumerate(applications, start=1):
        tokens = list(block.get("tokens") or [])
        listener_id = f"gotify-{i}"
        listeners.append(
            {
                "id": listener_id,
                "type": "gotify",
                "enabled": True,
                "tags": [],
                "options": {
                    "host": host,
                    "client_token": token,
                    "ssl": False,
                    "app_tokens": tokens or ["all"],
                },
            }
        )
        for recv in block.get("receivers") or []:
            receiver_index += 1
            rid = _receiver_id(receiver_index)
            urls = list(recv.get("urls") or [])
            options: dict[str, Any] = {"urls": urls}
            receiver = {
                "id": rid,
                "type": "apprise",
                "enabled": True,
                "tags": [],
                "options": options,
            }
            receivers.append(receiver)

            filt: dict[str, Any] = {}
            if "minPriority" in recv:
                filt["min_priority"] = recv["minPriority"]
            if "priorities" in recv:
                filt["priorities"] = recv["priorities"]

            templates: dict[str, Any] = {}
            if recv.get("titleTemplate"):
                templates["title"] = recv["titleTemplate"]
            if recv.get("messageTemplate"):
                templates["body"] = recv["messageTemplate"]

            route: dict[str, Any] = {
                "id": f"route-{receiver_index}",
                "enabled": True,
                "from": {"listeners": [listener_id]},
                "to": {"receivers": [rid]},
            }
            if filt:
                route["filter"] = filt
            if templates:
                route["templates"] = templates
            routes.append(route)

    defaults: dict[str, Any] = {
        "title_template": "$title",
        "message_template": "$message",
        "datetime_format": "%Y-%m-%d %H:%M:%S.%f",
        "delivery": {
            "max_attempts": 5,
            "initial_delay_sec": 30,
            "backoff": "exponential",
            "max_delay_sec": 3600,
        },
    }
    if settings and settings.title_template:
        defaults["title_template"] = settings.title_template
    if settings and settings.message_template:
        defaults["message_template"] = settings.message_template

    return {
        "version": 2,
        "defaults": defaults,
        "listeners": listeners,
        "receivers": receivers,
        "routes": routes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrate gotify2apprise YAML v1 → v2")
    parser.add_argument("source", type=Path, help="path to v1 config.yaml")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="write v2 YAML here (default: stdout, or next to source as *.v2.yaml)",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="overwrite source after writing a .bak.v1 backup",
    )
    args = parser.parse_args(argv)

    raw = yaml.safe_load(args.source.read_text(encoding="utf-8"))
    if not is_v1_config(raw):
        print("Not a v1 config (expected applications[] without version: 2)", file=sys.stderr)
        return 1
    converted = convert_v1(raw)
    text = dump_yaml(converted)

    if args.in_place:
        bak = Path(str(args.source) + ".bak.v1")
        if bak.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            bak = Path(str(args.source) + f".bak.v1.{stamp}")
        bak.write_text(args.source.read_text(encoding="utf-8"), encoding="utf-8")
        args.source.write_text(text, encoding="utf-8")
        print(f"Wrote v2 to {args.source} (backup {bak})")
        return 0

    dest = args.output
    if dest is None and sys.stdout.isatty():
        dest = args.source.with_name(args.source.name + ".v2.yaml")
    if dest is not None:
        dest.write_text(text, encoding="utf-8")
        print(f"Wrote {dest}")
        return 0
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
