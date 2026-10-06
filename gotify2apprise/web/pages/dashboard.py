from __future__ import annotations

from nicegui import ui

from gotify2apprise.datetime_fmt import datetime_format_from_config
from gotify2apprise.display import DELIVERY_PAGE_SIZE, present_delivery_rows
from gotify2apprise.runtime import get_runtime
from gotify2apprise.web.delivery_table import delivery_columns, table_scroll_box, wire_delivery_table
from gotify2apprise.web.layout import page_frame, require_auth


@ui.page("/")
async def dashboard_page() -> None:
    if not require_auth():
        return
    page_frame("Dashboard", fill=True)
    bridge = get_runtime().bridge
    counts = await bridge.queue.counts()
    totals_1d = await bridge.stats.totals(1)
    totals_7d = await bridge.stats.totals(7)
    recent = present_delivery_rows(
        await bridge.queue.list_recent(limit=DELIVERY_PAGE_SIZE),
        datetime_format_from_config(bridge.config),
    )

    with ui.row().classes("q-pa-md gap-4 flex-wrap"):
        _stat("Pending", counts.get("pending", 0))
        _stat("Retrying", counts.get("failed", 0))
        _stat("Dead", counts.get("dead", 0))
        _stat("Sent 24h", totals_1d["sent_ok"])
        _stat("Failed 24h", totals_1d["sent_fail"])
        _stat("Sent 7d", totals_7d["sent_ok"])

    running = ", ".join(bridge.listeners) or "none"
    ui.label(f"Listeners running: {running}").classes("q-px-md")

    ui.label("Recent deliveries").classes("text-h6 q-px-md q-pt-md")
    columns = delivery_columns()

    async def retry(delivery_id: str) -> None:
        await bridge.retry_delivery(delivery_id)
        ui.notify("Queued for retry")
        table.rows = present_delivery_rows(
            await bridge.queue.list_recent(limit=DELIVERY_PAGE_SIZE),
            datetime_format_from_config(bridge.config),
        )
        table.update()

    with table_scroll_box(dashboard=True):
        table = ui.table(columns=columns, rows=recent, row_key="id").classes("w-full")
        wire_delivery_table(table, on_retry=retry)


def _stat(label: str, value: int) -> None:
    with ui.column().classes("q-pa-md g2a-stat rounded-borders"):
        ui.label(str(value)).classes("text-h5")
        ui.label(label).classes("g2a-muted")
