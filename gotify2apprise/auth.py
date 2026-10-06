from __future__ import annotations

import logging
import secrets

from gotify2apprise.settings import Settings
from gotify2apprise.storage.auth_repo import AuthRepo

log = logging.getLogger(__name__)


async def bootstrap_user(auth: AuthRepo, settings: Settings) -> None:
    existing = await auth.get_user()
    if existing is not None:
        return
    username = settings.admin_user or "admin"
    password = settings.admin_password
    generated = False
    if not password:
        password = secrets.token_urlsafe(16)
        generated = True
    await auth.upsert_user(username, password)
    if generated:
        log.warning(
            "Created UI user %r with generated password: %s  "
            "(change it in Settings; set ADMIN_USER/ADMIN_PASSWORD to choose on first boot)",
            username,
            password,
        )
    else:
        log.info("Created UI user %r from ADMIN_* env", username)
