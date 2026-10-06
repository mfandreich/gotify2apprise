from gotify2apprise.display import present_delivery_rows, truncate_title


def test_truncate_title_collapses_whitespace_and_caps() -> None:
    assert truncate_title("  hello\n\nworld  ") == "hello world"
    assert truncate_title("x" * 40) == "x" * 40
    assert truncate_title("x" * 41) == ("x" * 39) + "…"
    assert truncate_title(None) == ""


def test_present_delivery_rows_strips_body_and_adds_priority() -> None:
    rows = present_delivery_rows(
        [
            {
                "id": "1",
                "title": "<b>alert</b>\n**boom**",
                "body": "<script>alert(1)</script>\n# heading",
                "priority": 10,
                "status": "success",
            }
        ]
    )
    item = rows[0]
    assert item["title"] == "<b>alert</b> **boom**"
    assert item["title_full"] == "<b>alert</b>\n**boom**"
    assert item["body_full"] == "<script>alert(1)</script>\n# heading"
    assert "body" not in item
    assert item["priority"] == 10
    assert item["priority_bucket"] == "crit"
    assert item["priority_label"] == "crit"
    assert item["priority_icon"] == "error"
    assert item["status"] == "success"
