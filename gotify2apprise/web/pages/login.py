from __future__ import annotations

from nicegui import app, ui

from gotify2apprise.runtime import get_runtime


@ui.page("/login")
def login_page() -> None:
    if app.storage.user.get("authenticated"):
        ui.navigate.to("/")
        return

    ui.page_title("Login")
    with ui.column().classes("absolute-center items-center gap-4"):
        ui.label("gotify2apprise").classes("text-h5")
        ui.label("Sign in").classes("text-grey")
        username = ui.input("Username").props("outlined").classes("w-64")
        password = ui.input("Password", password=True, password_toggle_button=True).props(
            "outlined"
        ).classes("w-64")
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
        ui.button("Sign in", on_click=submit).classes("w-64")
