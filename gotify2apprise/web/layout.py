from __future__ import annotations

from nicegui import app, ui

from gotify2apprise import __version__
from gotify2apprise.runtime import get_runtime
from gotify2apprise.web.theme import bind_dark_mode, dark_mode_toggle

REPO_URL = "https://github.com/mfandreich/gotify2apprise"
_GITHUB_ICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" '
    'aria-hidden="true"><path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 '
    "6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94"
    "-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 "
    "1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82"
    "-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 "
    ".27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07"
    "-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 "
    '8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>'
)
NAV_LINKS = (
    ("Dashboard", "/"),
    ("Messages", "/messages"),
    ("Stats", "/stats"),
    ("Config", "/config"),
    ("Settings", "/settings"),
)


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


def github_link() -> None:
    with ui.link(target=REPO_URL, new_tab=True).classes(
        "g2a-github g2a-footer-link items-center no-underline"
    ).props('aria-label="GitHub repository" rel=noopener noreferrer'):
        ui.html(_GITHUB_ICON, sanitize=False, tag="span")
        ui.label("GitHub")


def site_footer() -> None:
    with ui.footer().classes("g2a-footer items-center justify-center"):
        ui.label(f"v{__version__}").classes("g2a-muted text-caption")
        ui.label("·").classes("g2a-muted q-px-xs")
        github_link()


def page_frame(title: str, *, fill: bool = False) -> None:
    ui.page_title(title)
    body = ui.query("body")
    if fill:
        body.classes(add="g2a-fill")
    else:
        body.classes(remove="g2a-fill")
    dark = bind_dark_mode()
    drawer = ui.left_drawer(value=False, fixed=False, elevated=True).classes("g2a-drawer")
    with drawer:
        ui.label("gotify2apprise").classes("text-h6")
        ui.label(f"v{__version__}").classes("g2a-muted text-caption q-mb-sm")
        for label, href in NAV_LINKS:
            ui.link(label, href).classes("g2a-drawer-link")
    with ui.header().classes("g2a-header items-center justify-between"):
        with ui.row().classes("items-center g2a-header-left"):
            ui.button(icon="menu", on_click=drawer.toggle).props(
                "flat round dense color=white"
            ).classes("g2a-menu-btn")
            ui.label("gotify2apprise").classes("g2a-brand text-white")
            with ui.row().classes("items-center g2a-header-nav"):
                for label, href in NAV_LINKS:
                    ui.link(label, href).classes("text-white")
        with ui.row().classes("items-center g2a-header-actions"):
            dark_mode_toggle(dark)
            ui.button(icon="logout", on_click=logout).props(
                "flat round dense color=white"
            ).tooltip("Logout")
    site_footer()
    error = None
    try:
        error = get_runtime().bridge.last_error
    except RuntimeError:
        error = "runtime not started"
    if error:
        ui.label(error).classes("text-negative q-pa-md")
