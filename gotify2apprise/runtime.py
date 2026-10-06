from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass

from gotify2apprise.auth import bootstrap_user
from gotify2apprise.bridge import Bridge
from gotify2apprise.config.manager import ConfigV1Error
from gotify2apprise.settings import Settings
from gotify2apprise.storage.db import Database

log = logging.getLogger(__name__)


@dataclass
class Runtime:
    settings: Settings
    db: Database
    bridge: Bridge


runtime: Runtime | None = None


def get_runtime() -> Runtime:
    if runtime is None:
        raise RuntimeError("runtime is not started")
    return runtime


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if os.environ.get("TITLE_TEMPLATE") or os.environ.get("MESSAGE_TEMPLATE"):
        log.warning(
            "TITLE_TEMPLATE / MESSAGE_TEMPLATE env vars are deprecated; "
            "set defaults.title_template / defaults.message_template in YAML"
        )


async def start_runtime(settings: Settings) -> Runtime:
    global runtime
    db = Database(settings.db_path)
    await db.connect()
    bridge = Bridge(settings, db)
    await bootstrap_user(bridge.auth, settings)
    try:
        await bridge.start()
    except ConfigV1Error:
        await db.close()
        raise
    runtime = Runtime(settings=settings, db=db, bridge=bridge)
    return runtime


async def stop_runtime() -> None:
    global runtime
    if runtime is None:
        return
    try:
        await runtime.bridge.stop()
    except asyncio.CancelledError:
        pass
    except Exception:
        log.exception("bridge stop failed")
    try:
        await runtime.db.close()
    except Exception:
        log.exception("database close failed")
    runtime = None
