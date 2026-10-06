from gotify2apprise.web.delivery_table import (
    _actions_header_slot,
    _title_filter_slot,
    empty_delivery_filters,
    parse_filter_event,
)


def test_parse_filter_event_accepts_nested_payloads() -> None:
    assert parse_filter_event(["status", "failed"]) == ("status", "failed")
    assert parse_filter_event([["listener_id", "smtp-a"]]) == ("listener_id", "smtp-a")
    assert parse_filter_event(["priority_bucket", None]) == ("priority_bucket", "")
    assert parse_filter_event(["unknown", "x"]) is None
    assert parse_filter_event("status") is None


def test_header_slots_use_titles_and_clear_control() -> None:
    idle = _title_filter_slot(
        "status",
        "Status",
        "",
        [("", "any status"), ("failed", "failed")],
    )
    assert 'label="Status"' in idle
    assert "g2a-th-filter--on" not in idle
    assert "filter_alt_off" not in idle

    active = _title_filter_slot(
        "listener_id",
        "From",
        "smtp-a",
        [("", "any from"), ("smtp-a", "smtp-a")],
    )
    assert 'label="smtp-a"' in active
    assert "g2a-th-filter--on" in active
    assert "set-filter" in active

    clear_idle = _actions_header_slot(empty_delivery_filters())
    assert "filter_alt_off" in clear_idle
    assert " disable" in clear_idle
    assert "g2a-filter-clear--idle" in clear_idle

    clear_active = _actions_header_slot(
        {
            "priority_bucket": "crit",
            "listener_id": "",
            "receiver_id": "",
            "status": "",
        }
    )
    assert " disable" not in clear_active
    assert 'icon="error"' in clear_active
    assert "clear-filters" in clear_active
