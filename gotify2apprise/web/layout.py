from __future__ import annotations

from nicegui import app, ui

from gotify2apprise.runtime import get_runtime


def require_auth() -> bool:
    if app.storage.user.get("authenticated"):
        return True
    ui.navigate.to("/login")
    return False


def logout() -> None:
    app.storage.user.clear()
    ui.navigate.to("/login")


def page_frame(title: str) -> None:
    ui.page_title(title)
    with ui.header().classes("items-center justify-between px-4"):
        ui.label("gotify2apprise").classes("text-h6")
        with ui.row().classes("items-center gap-4"):
            ui.link("Dashboard", "/")
            ui.link("Messages", "/messages")
            ui.link("Stats", "/stats")
            ui.link("Config", "/config")
            ui.link("Settings", "/settings")
            ui.button("Logout", on_click=logout).props("flat dense")
    error = None
    try:
        error = get_runtime().bridge.last_error
    except RuntimeError:
        error = "runtime not started"
    if error:
        ui.label(error).classes("text-negative q-pa-md")
