from __future__ import annotations

from nicegui import ui

from gotify2apprise.runtime import get_runtime
from gotify2apprise.web.layout import page_frame, require_auth


@ui.page("/messages")
async def messages_page() -> None:
    if not require_auth():
        return
    page_frame("Messages")
    bridge = get_runtime().bridge

    with ui.row().classes("q-pa-md items-end gap-4"):
        status = ui.select(
            {"": "any status", "pending": "pending", "failed": "failed", "success": "success", "dead": "dead"},
            value="",
            label="Status",
        ).props("outlined").classes("w-40")
        refresh_btn = ui.button("Refresh")

    columns = [
        {"name": "created_at", "label": "Time", "field": "created_at"},
        {"name": "listener_id", "label": "Listener", "field": "listener_id"},
        {"name": "receiver_id", "label": "Receiver", "field": "receiver_id"},
        {"name": "route_id", "label": "Route", "field": "route_id"},
        {"name": "status", "label": "Status", "field": "status"},
        {"name": "attempt", "label": "Attempt", "field": "attempt"},
        {"name": "title", "label": "Title", "field": "title"},
        {"name": "last_error", "label": "Error", "field": "last_error"},
        {"name": "actions", "label": "", "field": "actions"},
    ]
    table = ui.table(columns=columns, rows=[], row_key="id").classes("w-full q-px-md")

    async def reload_rows() -> None:
        flt = status.value or None
        rows = await bridge.queue.list_recent(limit=200, status=flt)
        table.rows = rows
        table.update()

    async def retry(delivery_id: str) -> None:
        await bridge.retry_delivery(delivery_id)
        ui.notify("Queued for retry")
        await reload_rows()

    async def on_retry(e) -> None:  # noqa: ANN001
        delivery_id = e.args
        if isinstance(delivery_id, (list, tuple)):
            delivery_id = delivery_id[0]
        await retry(str(delivery_id))

    table.add_slot(
        "body-cell-actions",
        r'''
        <q-td :props="props">
            <q-btn dense flat label="Retry" @click="$parent.$emit('retry', props.row.id)" />
        </q-td>
        ''',
    )
    table.on("retry", on_retry)

    refresh_btn.on_click(reload_rows)
    status.on_value_change(reload_rows)
    await reload_rows()
