from __future__ import annotations

import logging
import sys

from dotenv import load_dotenv

from gotify2apprise import __version__
from gotify2apprise.config.manager import ConfigManager, ConfigV1Error
from gotify2apprise.runtime import configure_logging
from gotify2apprise.settings import Settings

log = logging.getLogger(__name__)


def preflight(settings: Settings) -> None:
    if not settings.conf_file.exists():
        log.warning("config file %s not found; UI will start without listeners", settings.conf_file)
        return
    manager = ConfigManager(settings)
    raw = manager.read_raw()
    if manager.detect_v1(raw) and not settings.auto_migrate_v1:
        print(
            "Config v1 detected. Run:\n"
            f"  python -m gotify2apprise.legacy.migrate_v1 --in-place {settings.conf_file}\n"
            "or set AUTO_MIGRATE_V1=true",
            file=sys.stderr,
        )
        raise SystemExit(1)


def main() -> None:
    load_dotenv()
    configure_logging()
    log.info("gotify2apprise %s", __version__)
    settings = Settings.from_env()
    preflight(settings)
    from gotify2apprise.web.app import run_ui

    try:
        run_ui(settings)
    except KeyboardInterrupt:
        log.info("stopped")


if __name__ == "__main__":
    main()
