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
.g2a-header {
  padding-left: 8px;
  padding-right: 8px;
  flex-wrap: nowrap;
  min-height: 48px;
}
.g2a-header-left,
.g2a-header-actions,
.g2a-header-nav {
  gap: 8px;
  flex-wrap: nowrap;
}
.g2a-menu-btn {
  display: inline-flex !important;
}
.g2a-header-nav {
  display: none !important;
}
.g2a-brand {
  font-size: 1.05rem;
  font-weight: 500;
  white-space: nowrap;
}
@media (min-width: 1024px) {
  .g2a-header {
    padding-left: 16px;
    padding-right: 16px;
  }
  .g2a-header-nav {
    display: flex !important;
    gap: 16px;
    margin-left: 16px;
  }
  .g2a-menu-btn {
    display: none !important;
  }
  .g2a-brand {
    font-size: 1.25rem;
  }
  .g2a-drawer {
    display: none !important;
  }
}
.g2a-github {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  white-space: nowrap;
  font-weight: 500;
}
.g2a-github svg {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
}
.g2a-drawer .g2a-drawer-link,
.g2a-drawer .g2a-footer-link {
  display: block;
  padding: 12px 4px;
  min-height: 44px;
  line-height: 20px;
  text-decoration: none;
  font-weight: 500;
}
.g2a-footer {
  min-height: 40px;
  gap: 0;
}
.g2a-footer-link {
  font-weight: 500;
  text-decoration: none;
}
.g2a-footer-link:hover {
  text-decoration: underline;
}
body.body--light .g2a-drawer,
body.body--light .g2a-footer {
  background: #e8edf4;
  color: #1a1a1a;
}
body.body--dark .g2a-drawer,
body.body--dark .g2a-footer {
  background: #1e1e1e;
  color: #eeeeee;
}
body.body--light .g2a-drawer-link,
body.body--light .g2a-footer-link {
  color: #0d47a1 !important;
}
body.body--dark .g2a-drawer-link,
body.body--dark .g2a-footer-link {
  color: #90caf9 !important;
}
html, body {
  height: 100%;
}
.q-layout,
.q-page-container,
.q-page {
  min-width: 0;
  max-width: 100%;
}
body.g2a-fill {
  overflow: hidden;
}
body.g2a-fill .q-layout {
  height: 100dvh;
  max-height: 100dvh;
  min-height: 0;
  overflow: hidden;
}
body.g2a-fill .q-page-container {
  position: absolute;
  inset: 0;
  overflow: hidden;
}
body.g2a-fill .q-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}
body.g2a-fill .nicegui-content {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  width: 100%;
  max-width: 100%;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}
.g2a-table-host {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  min-height: 12rem;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}
body.g2a-fill .g2a-table-host {
  flex: 1 1 auto;
  min-height: 0;
  height: auto;
}
.g2a-table-host .q-table__container {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  height: 100%;
  max-height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.g2a-table-host .q-table__middle {
  flex: 1 1 auto;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  min-height: 0;
  overflow: auto !important;
}
.g2a-table-host .q-table__middle > table {
  min-width: 44rem;
}
.g2a-table-host--dashboard .q-table__middle > table {
  min-width: 42rem;
}
.g2a-table-host .q-table th,
.g2a-table-host .q-table td {
  white-space: nowrap;
  padding: 4px 8px !important;
}
.g2a-row-actions {
  display: inline-flex;
  align-items: center;
  gap: 0;
  white-space: nowrap;
}
.g2a-row-actions .q-btn {
  min-height: 1.5rem;
  min-width: 1.5rem;
  padding: 0;
}
.g2a-row-actions .q-btn .q-icon {
  font-size: 1.05rem;
}
.g2a-prio-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  cursor: default;
}
.g2a-prio-icon .q-icon {
  font-size: 1.15rem;
}
.g2a-th-filter {
  font-weight: 500;
  padding: 0 2px;
  min-height: 1.5rem;
  font-size: inherit;
}
.g2a-th-filter--on .q-btn__content > span:first-child {
  text-decoration: underline;
  text-underline-offset: 3px;
}
.g2a-prio-muted {
  opacity: 0.55;
}
.g2a-filter-clear--idle {
  opacity: 0.35;
}
.g2a-table-host .q-table thead .g2a-th-filter,
.g2a-table-host .q-table thead .g2a-th-filter .q-icon {
  color: inherit !important;
}
.g2a-table-host .q-table thead tr th {
  position: sticky;
  top: 0;
  z-index: 3;
}
body.body--light .g2a-table-host .q-table thead tr th {
  background: #ffffff;
}
body.body--dark .g2a-table-host .q-table thead tr th {
  background: #1e1e1e;
}
.g2a-login {
  min-height: calc(100vh - 120px);
  justify-content: center;
}
.g2a-login-card {
  max-width: 20rem;
}
.g2a-title-link {
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
  max-width: 22rem;
  display: inline-block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}
.g2a-delivery-table tbody tr {
  cursor: pointer;
}
.g2a-title-link:hover {
  opacity: 0.85;
}
.g2a-prio {
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  font-weight: 500;
}
body.body--light .g2a-prio-info,
body.body--light .g2a-prio-info .q-icon { color: #1565c0; }
body.body--dark .g2a-prio-info,
body.body--dark .g2a-prio-info .q-icon { color: #90caf9; }
body.body--light .g2a-prio-warn,
body.body--light .g2a-prio-warn .q-icon { color: #e65100; }
body.body--dark .g2a-prio-warn,
body.body--dark .g2a-prio-warn .q-icon { color: #ffcc80; }
body.body--light .g2a-prio-crit,
body.body--light .g2a-prio-crit .q-icon { color: #b71c1c; }
body.body--dark .g2a-prio-crit,
body.body--dark .g2a-prio-crit .q-icon { color: #ef9a9a; }
body.body--light .g2a-table-host .q-table thead .g2a-prio-info,
body.body--light .g2a-table-host .q-table thead .g2a-prio-info .q-icon { color: #1565c0 !important; }
body.body--dark .g2a-table-host .q-table thead .g2a-prio-info,
body.body--dark .g2a-table-host .q-table thead .g2a-prio-info .q-icon { color: #90caf9 !important; }
body.body--light .g2a-table-host .q-table thead .g2a-prio-warn,
body.body--light .g2a-table-host .q-table thead .g2a-prio-warn .q-icon { color: #e65100 !important; }
body.body--dark .g2a-table-host .q-table thead .g2a-prio-warn,
body.body--dark .g2a-table-host .q-table thead .g2a-prio-warn .q-icon { color: #ffcc80 !important; }
body.body--light .g2a-table-host .q-table thead .g2a-prio-crit,
body.body--light .g2a-table-host .q-table thead .g2a-prio-crit .q-icon { color: #b71c1c !important; }
body.body--dark .g2a-table-host .q-table thead .g2a-prio-crit,
body.body--dark .g2a-table-host .q-table thead .g2a-prio-crit .q-icon { color: #ef9a9a !important; }
.g2a-message-dialog {
  width: min(48rem, 95vw) !important;
  max-width: 95vw !important;
  min-width: min(36rem, 95vw);
  box-sizing: border-box;
}
.g2a-message-dialog .g2a-row-actions {
  margin: 4px 0 2px;
}
.g2a-message-dialog .g2a-row-actions .q-btn {
  min-height: 1.5rem;
  min-width: 1.5rem;
  padding: 0;
}
.g2a-message-dialog .g2a-row-actions .q-btn .q-icon {
  font-size: 1.05rem;
}
body.body--dark .g2a-message-dialog .g2a-row-actions .q-btn {
  color: #90caf9 !important;
}
body.body--light .g2a-message-dialog .g2a-row-actions .q-btn {
  color: inherit !important;
}
.g2a-message-meta {
  gap: 12px 24px;
  flex-wrap: wrap;
  margin: 8px 0 4px;
}
.g2a-message-meta-item {
  min-width: 6rem;
}
.g2a-plain-head {
  margin-top: 8px;
}
.g2a-plain {
  display: block;
  width: 100%;
  box-sizing: border-box;
  align-self: stretch;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 0.85rem;
  line-height: 1.4;
  overflow: auto;
  margin: 0;
  padding: 8px;
  border-radius: 4px;
}
.g2a-plain--title {
  min-height: 2.75rem;
  max-height: min(20vh, 8rem);
}
.g2a-plain--body {
  min-height: 10rem;
  max-height: min(50vh, 28rem);
}
body.body--light .g2a-plain {
  background: #f4f6f9;
  color: #1a1a1a;
}
body.body--dark .g2a-plain {
  background: #2a2a2a;
  color: #f5f5f5;
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
