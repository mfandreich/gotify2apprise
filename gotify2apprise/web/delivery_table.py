from __future__ import annotations

import html
import inspect
import json
from collections.abc import Callable
from typing import Any

from nicegui import ui

from gotify2apprise.display import PRIORITY_ICONS, as_plain_text

FILTER_KEYS = ("priority_bucket", "listener_id", "receiver_id", "status")
PRIO_FILTER_OPTIONS = (("", "any prio"), ("info", "info"), ("warn", "warn"), ("crit", "crit"))
STATUS_FILTER_OPTIONS = (
    ("", "any status"),
    ("pending", "pending"),
    ("failed", "failed"),
    ("success", "success"),
    ("dead", "dead"),
)

_TITLE_SLOT = """
<q-td :props="props">
  <span class="g2a-title-link">{{ props.row.title }}</span>
</q-td>
"""

_ACTIONS_SLOT = """
<q-td :props="props">
  <div class="g2a-row-actions">
    <span class="g2a-prio-icon" @click.stop>
      <q-icon :name="props.row.priority_icon"
        :class="'g2a-prio g2a-prio-' + props.row.priority_bucket" />
      <q-tooltip>Prio {{ props.row.priority_label }}</q-tooltip>
    </span>
    <q-btn dense flat round size="xs" icon="replay" aria-label="Retry"
      @click.stop="$parent.$emit('retry', props.row.id)">
      <q-tooltip>Retry</q-tooltip>
    </q-btn>
    <q-btn dense flat round size="xs" icon="title" aria-label="Copy title"
      @click.stop="$parent.$emit('copy-text', props.row.title_full || props.row.title || '')">
      <q-tooltip>Copy title</q-tooltip>
    </q-btn>
    <q-btn dense flat round size="xs" icon="notes" aria-label="Copy body"
      @click.stop="$parent.$emit('copy-text', props.row.body_full || '')">
      <q-tooltip>Copy body</q-tooltip>
    </q-btn>
  </div>
</q-td>
"""


def empty_delivery_filters() -> dict[str, str]:
    return {key: "" for key in FILTER_KEYS}


def delivery_filter_kwargs(filters: dict[str, str]) -> dict[str, str | None]:
    return {key: (filters.get(key) or None) for key in FILTER_KEYS}


def delivery_columns() -> list[dict[str, Any]]:
    return [
        {
            "name": "actions",
            "label": "",
            "field": "actions",
            "align": "left",
            "style": "width: 1%",
        },
        {"name": "created_at", "label": "Time", "field": "created_at"},
        {"name": "listener_id", "label": "From", "field": "listener_id"},
        {"name": "receiver_id", "label": "To", "field": "receiver_id"},
        {"name": "status", "label": "Status", "field": "status", "align": "left"},
        {"name": "attempt", "label": "Attempt", "field": "attempt", "align": "left"},
        {"name": "title", "label": "Title", "field": "title", "align": "left"},
    ]


def _copy_payload(payload: object) -> str:
    if isinstance(payload, (list, tuple)):
        payload = payload[0] if payload else ""
    if payload is None:
        return ""
    return str(payload)


def _copy_text(text: str) -> None:
    ui.clipboard.write(text)
    ui.notify("Copied")


def _plain_section(label: str, text: str, *, body: bool = False) -> None:
    shown = text or "(empty)"
    ui.label(label).classes("text-caption g2a-muted g2a-plain-head")
    ui.label(shown).classes("g2a-plain g2a-plain--body" if body else "g2a-plain g2a-plain--title")


def _meta_item(label: str, value: object) -> None:
    shown = as_plain_text(value) or "—"
    with ui.column().classes("g2a-message-meta-item"):
        ui.label(label).classes("text-caption g2a-muted")
        ui.label(shown)


def _row_actions(
    row: dict[str, Any],
    *,
    on_retry: Callable[[str], Any] | None = None,
) -> None:
    bucket = as_plain_text(row.get("priority_bucket") or row.get("priority_label") or "info")
    icon_name = as_plain_text(row.get("priority_icon")) or PRIORITY_ICONS.get(bucket, "info")
    title = as_plain_text(row.get("title_full") or row.get("title"))
    body = as_plain_text(row.get("body_full"))
    delivery_id = as_plain_text(row.get("id"))

    async def retry() -> None:
        if not delivery_id or on_retry is None:
            return
        result = on_retry(delivery_id)
        if inspect.isawaitable(result):
            await result

    with ui.row().classes("g2a-row-actions items-center"):
        with ui.element("span").classes("g2a-prio-icon"):
            ui.icon(icon_name).classes(f"g2a-prio g2a-prio-{bucket}")
            ui.tooltip(f"Prio {bucket}")
        ui.button(icon="replay", on_click=retry).props(
            'dense flat round size=xs aria-label="Retry"'
        ).tooltip("Retry")
        ui.button(icon="title", on_click=lambda: _copy_text(title)).props(
            'dense flat round size=xs aria-label="Copy title"'
        ).tooltip("Copy title")
        ui.button(icon="notes", on_click=lambda: _copy_text(body)).props(
            'dense flat round size=xs aria-label="Copy body"'
        ).tooltip("Copy body")


def open_message_dialog(
    row: dict[str, Any],
    *,
    on_retry: Callable[[str], Any] | None = None,
) -> None:
    title = as_plain_text(row.get("title_full") or row.get("title"))
    body = as_plain_text(row.get("body_full"))
    with ui.dialog() as dialog, ui.card(align_items="stretch").classes("g2a-message-dialog"):
        ui.label("Message").classes("text-h6")
        _row_actions(row, on_retry=on_retry)
        with ui.row().classes("g2a-message-meta"):
            _meta_item("Time", row.get("created_at"))
            _meta_item("From", row.get("listener_id"))
            _meta_item("To", row.get("receiver_id"))
            _meta_item("Status", row.get("status"))
            _meta_item("Attempt", row.get("attempt"))
        _plain_section("Title", title)
        _plain_section("Body", body, body=True)
        with ui.row().classes("q-mt-md"):
            ui.button("Close", on_click=dialog.close).props("flat")
    dialog.open()


def _row_from_event(payload: object) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, (list, tuple)):
        for item in payload:
            if isinstance(item, dict) and ("title_full" in item or "title" in item):
                return item
            if isinstance(item, dict) and "id" in item and "priority" in item:
                return item
    return None


def parse_filter_event(payload: object) -> tuple[str, str] | None:
    if isinstance(payload, (list, tuple)):
        if len(payload) >= 2 and not isinstance(payload[0], (list, tuple)):
            key, value = payload[0], payload[1]
        elif payload and isinstance(payload[0], (list, tuple)) and len(payload[0]) >= 2:
            key, value = payload[0][0], payload[0][1]
        else:
            return None
        key_text = str(key)
        if key_text not in FILTER_KEYS:
            return None
        return key_text, "" if value is None else str(value)
    return None


def _menu_item(key: str, value: str, label: str, *, selected: bool = False) -> str:
    payload = json.dumps([key, value])
    check = (
        '<q-item-section side><q-icon name="check" size="xs" /></q-item-section>'
        if selected
        else ""
    )
    return (
        "<q-item clickable v-close-popup "
        f"""@click.stop='$parent.$emit("set-filter", {payload})'>"""
        f"<q-item-section>{html.escape(label)}</q-item-section>{check}</q-item>"
    )


def _prio_menu_item(value: str, label: str, *, selected: bool) -> str:
    if value in PRIORITY_ICONS:
        avatar = (
            '<q-item-section avatar>'
            f'<q-icon name="{PRIORITY_ICONS[value]}" class="g2a-prio g2a-prio-{value}" />'
            "</q-item-section>"
        )
    else:
        avatar = ""
    payload = json.dumps(["priority_bucket", value])
    check = (
        '<q-item-section side><q-icon name="check" size="xs" /></q-item-section>'
        if selected
        else ""
    )
    return (
        "<q-item clickable v-close-popup "
        f"""@click.stop='$parent.$emit("set-filter", {payload})'>"""
        f"{avatar}<q-item-section>{html.escape(label)}</q-item-section>{check}</q-item>"
    )


def _title_filter_slot(
    key: str,
    title: str,
    current: str,
    options: list[tuple[str, str]],
) -> str:
    shown = current or title
    on = " g2a-th-filter--on" if current else ""
    items = "".join(
        _menu_item(key, value, label, selected=(value == current))
        for value, label in options
    )
    return (
        '<q-th :props="props">'
        f'<q-btn-dropdown flat dense no-caps unelevated class="g2a-th-filter{on}" '
        f'label="{html.escape(shown)}">'
        f'<q-list dense>{items}</q-list>'
        "</q-btn-dropdown></q-th>"
    )


def _actions_header_slot(filters: dict[str, str]) -> str:
    current = filters.get("priority_bucket") or ""
    active = any(filters.get(key) for key in FILTER_KEYS)
    icon = PRIORITY_ICONS.get(current, "filter_list")
    prio_class = f"g2a-prio g2a-prio-{current}" if current else "g2a-prio-muted"
    disable = " disable" if not active else ""
    idle_class = ' class="g2a-filter-clear--idle"' if not active else ""
    items = "".join(
        _prio_menu_item(value, label, selected=(value == current))
        for value, label in PRIO_FILTER_OPTIONS
    )
    return (
        '<q-th :props="props"><div class="g2a-row-actions">'
        f'<q-btn dense flat round size="xs" icon="filter_alt_off"{disable}{idle_class} '
        'aria-label="Clear filters" '
        """@click.stop="$parent.$emit('clear-filters')">"""
        "<q-tooltip>Clear filters</q-tooltip></q-btn>"
        f'<q-btn dense flat round size="xs" icon="{icon}" class="{prio_class}" '
        'aria-label="Filter by priority">'
        f"<q-menu auto-close><q-list dense>{items}</q-list></q-menu>"
        "<q-tooltip>Prio</q-tooltip></q-btn></div></q-th>"
    )


def apply_header_filters(
    table: ui.table,
    filters: dict[str, str],
    listener_ids: list[str],
    receiver_ids: list[str],
) -> None:
    from_options = [("", "any from"), *[(item, item) for item in listener_ids]]
    to_options = [("", "any to"), *[(item, item) for item in receiver_ids]]
    table.add_slot("header-cell-actions", _actions_header_slot(filters))
    table.add_slot(
        "header-cell-listener_id",
        _title_filter_slot("listener_id", "From", filters.get("listener_id") or "", from_options),
    )
    table.add_slot(
        "header-cell-receiver_id",
        _title_filter_slot("receiver_id", "To", filters.get("receiver_id") or "", to_options),
    )
    table.add_slot(
        "header-cell-status",
        _title_filter_slot(
            "status",
            "Status",
            filters.get("status") or "",
            list(STATUS_FILTER_OPTIONS),
        ),
    )
    table.update()


def table_scroll_box(*, dashboard: bool = False):
    classes = "g2a-table-host q-px-md"
    if dashboard:
        classes += " g2a-table-host--dashboard"
    return ui.element("div").classes(classes)


def wire_delivery_table(
    table: ui.table,
    *,
    on_retry: Callable[[str], Any] | None = None,
) -> None:
    table.add_slot("body-cell-title", _TITLE_SLOT)
    table.add_slot("body-cell-actions", _ACTIONS_SLOT)
    table.classes("g2a-delivery-table w-full")
    table.props("flat dense")
    table.style("height: 100%; max-height: 100%")

    async def handle_retry(delivery_id: str) -> None:
        if on_retry is None or not delivery_id:
            return
        result = on_retry(delivery_id)
        if inspect.isawaitable(result):
            await result

    def on_copy(e) -> None:  # noqa: ANN001
        _copy_text(_copy_payload(e.args))

    async def on_retry_event(e) -> None:  # noqa: ANN001
        delivery_id = e.args
        if isinstance(delivery_id, (list, tuple)):
            delivery_id = delivery_id[0]
        await handle_retry(str(delivery_id))

    def on_row_click(e) -> None:  # noqa: ANN001
        row = _row_from_event(e.args)
        if row is not None:
            open_message_dialog(row, on_retry=handle_retry)

    table.on("copy-text", on_copy)
    table.on("retry", on_retry_event)
    table.on("rowClick", on_row_click)
