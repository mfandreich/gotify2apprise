from __future__ import annotations

from nicegui import ui

from gotify2apprise.runtime import get_runtime
from gotify2apprise.web.layout import page_frame, require_auth


@ui.page("/")
async def dashboard_page() -> None:
    if not require_auth():
        return
    page_frame("Dashboard")
    bridge = get_runtime().bridge
    counts = await bridge.queue.counts()
    totals_1d = await bridge.stats.totals(1)
    totals_7d = await bridge.stats.totals(7)
    recent = await bridge.queue.list_recent(limit=20)

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
    columns = [
        {"name": "created_at", "label": "Time", "field": "created_at", "sortable": True},
        {"name": "listener_id", "label": "Listener", "field": "listener_id"},
        {"name": "receiver_id", "label": "Receiver", "field": "receiver_id"},
        {"name": "status", "label": "Status", "field": "status"},
        {"name": "title", "label": "Title", "field": "title"},
        {"name": "last_error", "label": "Error", "field": "last_error"},
    ]
    ui.table(columns=columns, rows=recent, row_key="id").classes("w-full q-pa-md")


def _stat(label: str, value: int) -> None:
    with ui.column().classes("q-pa-md g2a-stat rounded-borders"):
        ui.label(str(value)).classes("text-h5")
        ui.label(label).classes("g2a-muted")
