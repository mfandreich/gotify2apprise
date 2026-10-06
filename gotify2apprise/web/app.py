from __future__ import annotations

import logging

from nicegui import app, ui

from gotify2apprise.config.manager import ConfigV1Error
from gotify2apprise.runtime import start_runtime, stop_runtime
from gotify2apprise.settings import Settings

log = logging.getLogger(__name__)


def run_ui(settings: Settings) -> None:
    import gotify2apprise.web.pages.config_page  # noqa: F401
    import gotify2apprise.web.pages.dashboard  # noqa: F401
    import gotify2apprise.web.pages.login  # noqa: F401
    import gotify2apprise.web.pages.messages  # noqa: F401
    import gotify2apprise.web.pages.settings_page  # noqa: F401
    import gotify2apprise.web.pages.stats  # noqa: F401

    @app.on_startup
    async def _startup() -> None:
        try:
            await start_runtime(settings)
        except ConfigV1Error as exc:
            log.error("%s", exc)
            raise SystemExit(1) from exc

    @app.on_shutdown
    async def _shutdown() -> None:
        try:
            await stop_runtime()
        except Exception:
            log.exception("shutdown failed")

    try:
        ui.run(
            host=settings.ui_host,
            port=settings.ui_port,
            reload=False,
            show=False,
            storage_secret=settings.storage_secret,
            title="gotify2apprise",
            favicon=None,
            uvicorn_reload_excludes="*.db,*.db-wal,*.db-shm",
        )
    except KeyboardInterrupt:
        log.info("stopped")
