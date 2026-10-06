from __future__ import annotations

from nicegui import app, ui

from gotify2apprise.runtime import get_runtime
from gotify2apprise.web.theme import bind_dark_mode, dark_mode_toggle


def require_auth() -> bool:
    if app.storage.user.get("authenticated"):
        return True
    ui.navigate.to("/login")
    return False


def logout() -> None:
    dark = app.storage.user.get("dark")
    app.storage.user.clear()
    if dark is not None:
        app.storage.user["dark"] = dark
    ui.navigate.to("/login")


def page_frame(title: str) -> None:
    ui.page_title(title)
    dark = bind_dark_mode()
    with ui.header().classes("items-center justify-between px-4"):
        ui.label("gotify2apprise").classes("text-h6 text-white")
        with ui.row().classes("items-center gap-4"):
            ui.link("Dashboard", "/").classes("text-white")
            ui.link("Messages", "/messages").classes("text-white")
            ui.link("Stats", "/stats").classes("text-white")
            ui.link("Config", "/config").classes("text-white")
            ui.link("Settings", "/settings").classes("text-white")
            dark_mode_toggle(dark)
            ui.button("Logout", on_click=logout).props("flat dense color=white")
    error = None
    try:
        error = get_runtime().bridge.last_error
    except RuntimeError:
        error = "runtime not started"
    if error:
        ui.label(error).classes("text-negative q-pa-md")
