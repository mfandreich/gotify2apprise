from gotify2apprise.models.message import NormalizedMessage
from gotify2apprise.routing.templates import render_template


def test_placeholders() -> None:
    msg = NormalizedMessage(
        source_listener_id="l",
        title="Hello",
        body="World",
        priority=9,
        extra={"appid": 7},
    )
    assert render_template("[$priorityStr] $title $appid $priority $message", msg) == (
        "[crit] Hello 7 9 World"
    )
