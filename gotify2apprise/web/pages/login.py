from __future__ import annotations

from nicegui import app, ui

from gotify2apprise.runtime import get_runtime
from gotify2apprise.web.theme import bind_dark_mode, dark_mode_toggle


@ui.page("/login")
def login_page() -> None:
    if app.storage.user.get("authenticated"):
        ui.navigate.to("/")
        return

    ui.page_title("Login")
    dark = bind_dark_mode()
    with ui.header().classes("items-center justify-between px-4"):
        ui.label("gotify2apprise").classes("text-h6 text-white")
        dark_mode_toggle(dark)
    with ui.card().classes("absolute-center w-80 q-pa-lg"):
        ui.label("Sign in").classes("text-h5")
        ui.label("Single-user console").classes("g2a-muted")
        username = ui.input("Username").props("outlined").classes("w-full")
        password = ui.input("Password", password=True, password_toggle_button=True).props(
            "outlined"
        ).classes("w-full")
        status = ui.label("").classes("text-negative")

        async def submit() -> None:
            auth = get_runtime().bridge.auth
            if await auth.verify(username.value or "", password.value or ""):
                app.storage.user["authenticated"] = True
                app.storage.user["username"] = username.value
                ui.navigate.to("/")
            else:
                status.set_text("Invalid username or password")

        password.on("keydown.enter", submit)
        ui.button("Sign in", on_click=submit).props("unelevated").classes("w-full")
