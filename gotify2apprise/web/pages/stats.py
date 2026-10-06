from __future__ import annotations

from collections import defaultdict

from nicegui import ui

from gotify2apprise.runtime import get_runtime
from gotify2apprise.web.layout import page_frame, require_auth
from gotify2apprise.web.theme import is_dark


@ui.page("/stats")
async def stats_page() -> None:
    if not require_auth():
        return
    page_frame("Stats")
    bridge = get_runtime().bridge
    rows = await bridge.stats.range_days(7)
    by_day: dict[str, dict[str, int]] = defaultdict(lambda: {"ok": 0, "fail": 0})
    for row in rows:
        day = str(row["date"])
        by_day[day]["ok"] += int(row["sent_ok"])
        by_day[day]["fail"] += int(row["sent_fail"])
    for row in rows:
        row["key"] = f"{row['date']}:{row['listener_id']}:{row['receiver_id']}"
    days = sorted(by_day)
    dark = is_dark()
    fg = "#eeeeee" if dark else "#1a1a1a"
    split = "#555555" if dark else "#c5cdd8"
    ui.echart(
        {
            "textStyle": {"color": fg},
            "tooltip": {"trigger": "axis"},
            "legend": {"data": ["ok", "fail"], "textStyle": {"color": fg}},
            "xAxis": {
                "type": "category",
                "data": days,
                "axisLabel": {"color": fg},
                "axisLine": {"lineStyle": {"color": fg}},
            },
            "yAxis": {
                "type": "value",
                "axisLabel": {"color": fg},
                "splitLine": {"lineStyle": {"color": split}},
            },
            "series": [
                {"name": "ok", "type": "bar", "data": [by_day[d]["ok"] for d in days]},
                {"name": "fail", "type": "bar", "data": [by_day[d]["fail"] for d in days]},
            ],
        }
    ).classes("w-full h-80 q-pa-md")

    columns = [
        {"name": "date", "label": "Date", "field": "date"},
        {"name": "listener_id", "label": "Listener", "field": "listener_id"},
        {"name": "receiver_id", "label": "Receiver", "field": "receiver_id"},
        {"name": "sent_ok", "label": "OK", "field": "sent_ok"},
        {"name": "sent_fail", "label": "Fail", "field": "sent_fail"},
    ]
    ui.table(
        columns=columns,
        rows=rows,
        row_key="key",
    ).classes("w-full q-pa-md")
