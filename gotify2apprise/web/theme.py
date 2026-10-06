from __future__ import annotations

from nicegui import app, ui
from nicegui.elements.dark_mode import DarkMode

THEME_CSS = """
:root {
  color-scheme: light;
}
body.body--light {
  color-scheme: light;
  background-color: #e8edf4 !important;
  color: #1a1a1a;
}
body.body--dark {
  color-scheme: dark;
  background-color: #121212 !important;
  color: #eeeeee;
}
.q-header .q-btn,
.q-header a,
.q-header .q-icon {
  color: #ffffff !important;
}
.q-header a {
  text-decoration: none;
  font-weight: 500;
}
.q-header a:hover {
  text-decoration: underline;
}
body.body--light .q-field--outlined .q-field__control,
body.body--light .q-select .q-field__control {
  background: #ffffff;
}
body.body--dark .q-field--outlined .q-field__control,
body.body--dark .q-select .q-field__control {
  background: #2a2a2a;
}
body.body--light .q-field--outlined .q-field__control:before {
  border-color: #8a93a0;
}
body.body--dark .q-field--outlined .q-field__control:before {
  border-color: #7a7a7a;
}
body.body--light .q-field__native,
body.body--light .q-field__input,
body.body--light .q-field__prefix,
body.body--light textarea,
body.body--light .q-select .q-field__native span {
  color: #1a1a1a !important;
  -webkit-text-fill-color: #1a1a1a;
}
body.body--dark .q-field__native,
body.body--dark .q-field__input,
body.body--dark .q-field__prefix,
body.body--dark textarea,
body.body--dark .q-select .q-field__native span {
  color: #f5f5f5 !important;
  -webkit-text-fill-color: #f5f5f5;
}
body.body--light .q-field__label,
body.body--light .q-field__marginal,
body.body--light .q-field__marginal .q-icon {
  color: #424242 !important;
}
body.body--dark .q-field__label,
body.body--dark .q-field__marginal,
body.body--dark .q-field__marginal .q-icon {
  color: #cfcfcf !important;
}
body.body--light .g2a-muted {
  color: #5f6368 !important;
}
body.body--dark .g2a-muted {
  color: #b0b8c1 !important;
}
body.body--light .g2a-stat {
  background: #ffffff;
  color: #1a1a1a;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.12);
}
body.body--dark .g2a-stat {
  background: #2a2a2a;
  color: #f5f5f5;
}
body.body--dark .q-table {
  color: #eeeeee;
  background: #1e1e1e;
}
body.body--light .q-table {
  color: #1a1a1a;
  background: #ffffff;
}
body.body--dark .q-table thead,
body.body--dark .q-table tbody td {
  color: #eeeeee;
}
body.body--dark .q-table tbody tr:hover {
  background: #2f2f2f;
}
body.body--dark .q-table .q-btn {
  color: #90caf9 !important;
}
body.body--dark .q-menu {
  background: #2a2a2a;
  color: #eeeeee;
}
body.body--light .q-menu {
  background: #ffffff;
  color: #1a1a1a;
}
body.body--dark .text-positive {
  color: #81c784 !important;
}
body.body--dark .text-negative {
  color: #ef9a9a !important;
}
body.body--light .text-positive {
  color: #1b5e20 !important;
}
body.body--light .text-negative {
  color: #b71c1c !important;
}
body.body--dark .q-card {
  background: #1e1e1e;
  color: #eeeeee;
}
"""


def configure_ui() -> None:
    app.colors(
        primary="#0d47a1",
        secondary="#00695c",
        accent="#6a1b9a",
        dark="#1e1e1e",
        dark_page="#121212",
        positive="#2e7d32",
        negative="#c62828",
        info="#0277bd",
        warning="#f9a825",
    )
    ui.add_css(THEME_CSS, shared=True)


def bind_dark_mode() -> DarkMode:
    stored = _stored_dark()
    dark = ui.dark_mode(bool(stored) if stored is not None else False)
    return dark


def dark_mode_toggle(dark: DarkMode) -> None:
    def toggle() -> None:
        new_value = not bool(dark.value)
        _persist_dark(new_value)
        dark.value = new_value
        ui.navigate.reload()

    ui.button(icon=_icon(dark), on_click=toggle).props("flat round dense color=white").tooltip(
        "Toggle dark mode"
    )


def is_dark() -> bool:
    stored = _stored_dark()
    return bool(stored) if stored is not None else False


def _icon(dark: DarkMode) -> str:
    return "light_mode" if dark.value else "dark_mode"


def _stored_dark() -> bool | None:
    for getter in (
        lambda: app.storage.user.get("dark"),
        lambda: app.storage.browser.get("dark"),
    ):
        try:
            stored = getter()
        except Exception:
            continue
        if stored is not None:
            return bool(stored)
    return None


def _persist_dark(value: bool) -> None:
    try:
        app.storage.user["dark"] = value
    except Exception:
        pass
    try:
        app.storage.browser["dark"] = value
    except Exception:
        pass
