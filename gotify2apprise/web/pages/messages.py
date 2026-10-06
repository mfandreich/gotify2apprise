from __future__ import annotations

from nicegui import ui

from gotify2apprise.datetime_fmt import datetime_format_from_config
from gotify2apprise.display import DELIVERY_PAGE_SIZE, present_delivery_rows
from gotify2apprise.runtime import get_runtime
from gotify2apprise.web.delivery_table import (
    apply_header_filters,
    delivery_columns,
    delivery_filter_kwargs,
    empty_delivery_filters,
    parse_filter_event,
    table_scroll_box,
    wire_delivery_table,
)
from gotify2apprise.web.layout import page_frame, require_auth


@ui.page("/messages")
async def messages_page() -> None:
    if not require_auth():
        return
    page_frame("Messages", fill=True)
    bridge = get_runtime().bridge
    cfg = bridge.config
    listener_ids = [item.id for item in cfg.listeners] if cfg else []
    receiver_ids = [item.id for item in cfg.receivers] if cfg else []
    filters = empty_delivery_filters()

    with ui.row().classes("q-px-md q-py-sm items-center gap-3 flex-wrap"):
        refresh_btn = ui.button("Refresh").props("dense")
        summary = ui.label("").classes("g2a-muted")
        pager = ui.pagination(1, 1, direction_links=True).props("boundary-links dense")

    async def retry(delivery_id: str) -> None:
        await bridge.retry_delivery(delivery_id)
        ui.notify("Queued for retry")
        await reload_rows()

    columns = delivery_columns()
    with table_scroll_box():
        table = ui.table(columns=columns, rows=[], row_key="id").classes("w-full")
        wire_delivery_table(table, on_retry=retry)
        apply_header_filters(table, filters, listener_ids, receiver_ids)

    def render_filters() -> None:
        apply_header_filters(table, filters, listener_ids, receiver_ids)

    async def reload_rows() -> None:
        flt = delivery_filter_kwargs(filters)
        total = await bridge.queue.count_deliveries(**flt)
        pages = max(1, (total + DELIVERY_PAGE_SIZE - 1) // DELIVERY_PAGE_SIZE)
        current = int(pager.value or 1)
        if current > pages:
            current = pages
            pager.value = pages
        pager._props["max"] = pages
        pager.update()
        offset = (current - 1) * DELIVERY_PAGE_SIZE
        rows = await bridge.queue.list_recent(
            limit=DELIVERY_PAGE_SIZE,
            offset=offset,
            **flt,
        )
        table.rows = present_delivery_rows(rows, datetime_format_from_config(bridge.config))
        table.update()
        if total == 0:
            summary.set_text("No deliveries")
        else:
            start = offset + 1
            end = offset + len(rows)
            summary.set_text(f"{start}–{end} of {total}")

    async def on_filter_change() -> None:
        if pager.value == 1:
            await reload_rows()
            return
        pager.value = 1

    async def on_set_filter(e) -> None:  # noqa: ANN001
        parsed = parse_filter_event(e.args)
        if parsed is None:
            return
        key, value = parsed
        if filters.get(key) == value:
            return
        filters[key] = value
        render_filters()
        await on_filter_change()

    async def on_clear_filters() -> None:
        if not any(filters.values()):
            return
        for key in filters:
            filters[key] = ""
        render_filters()
        await on_filter_change()

    table.on("set-filter", on_set_filter)
    table.on("clear-filters", on_clear_filters)
    pager.on_value_change(reload_rows)
    refresh_btn.on_click(reload_rows)
    await reload_rows()
