from __future__ import annotations

from nicegui import app, ui

from gotify2apprise.runtime import get_runtime
from gotify2apprise.web.layout import page_frame, require_auth


@ui.page("/settings")
async def settings_page() -> None:
    if not require_auth():
        return
    page_frame("Settings")
    rt = get_runtime()
    user = await rt.bridge.auth.get_user()
    username = user[0] if user else ""

    with ui.column().classes("q-pa-md gap-4").style("max-width: 420px"):
        ui.label("Single user").classes("text-h6")
        ui.label(f"Username: {username}")
        new_password = ui.input("New password", password=True, password_toggle_button=True).props(
            "outlined"
        )
        confirm = ui.input("Confirm password", password=True).props("outlined")
        pwd_status = ui.label("")

        async def change_password() -> None:
            if not new_password.value or new_password.value != confirm.value:
                pwd_status.set_text("Passwords do not match")
                pwd_status.classes(replace="text-negative")
                return
            if len(new_password.value) < 8:
                pwd_status.set_text("Use at least 8 characters")
                pwd_status.classes(replace="text-negative")
                return
            await rt.bridge.auth.update_password(new_password.value)
            pwd_status.set_text("Password updated")
            pwd_status.classes(replace="text-positive")
            new_password.value = ""
            confirm.value = ""

        ui.button("Change password", on_click=change_password)

        ui.separator()
        ui.label("Retention").classes("text-h6")
        ui.label(f"MESSAGE_RETENTION_DAYS = {rt.settings.message_retention_days}")
        ui.label(f"MAX_MESSAGES_PER_CHANNEL = {rt.settings.max_messages_per_channel}")
        ui.label("Change these via environment variables (container restart).").classes("g2a-muted")

        ui.separator()
        ui.label("This UI is not production-grade auth. Put it behind a reverse proxy.").classes(
            "g2a-muted"
        )
        ui.label(f"Signed in as {app.storage.user.get('username') or username}").classes("g2a-muted")
