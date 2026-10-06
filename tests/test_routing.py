from gotify2apprise.models.config import AppConfig
from gotify2apprise.models.message import NormalizedMessage
from gotify2apprise.routing.engine import RoutingEngine, from_candidates, to_candidates

ENGINE = RoutingEngine()


def _config(**kwargs) -> AppConfig:
    base = {
        "version": 2,
        "listeners": [
            {
                "id": "gotify-main",
                "type": "gotify",
                "tags": ["alerts"],
                "options": {"host": "localhost", "client_token": "c"},
            },
            {
                "id": "gotify-legacy",
                "type": "gotify",
                "tags": [],
                "options": {"host": "localhost", "client_token": "c"},
            },
            {
                "id": "smtp-local",
                "type": "smtp",
                "tags": ["smtp", "mail"],
                "options": {"port": 2525},
            },
        ],
        "receivers": [
            {
                "id": "telegram",
                "type": "apprise",
                "tags": ["alerts"],
                "options": {"urls": ["json://localhost"]},
            },
            {
                "id": "email",
                "type": "apprise",
                "tags": ["mail"],
                "options": {"urls": ["mailto://x:y@example.com"]},
            },
        ],
        "routes": [
            {
                "id": "r1",
                "from": {"listeners": ["gotify-main"]},
                "to": {"receivers": ["telegram"]},
            }
        ],
    }
    base.update(kwargs)
    return AppConfig.model_validate(base)


def test_id_only_from() -> None:
    cfg = _config()
    ids = from_candidates(cfg.routes[0], cfg)
    assert ids == {"gotify-main"}


def test_tag_or_union() -> None:
    cfg = _config(
        routes=[
            {
                "id": "fanout",
                "from": {
                    "listeners": ["gotify-legacy"],
                    "listener_tags": ["smtp"],
                },
                "to": {"receiver_tags": ["alerts"]},
            }
        ]
    )
    ids = from_candidates(cfg.routes[0], cfg)
    assert ids == {"gotify-legacy", "smtp-local"}
    receivers = {r.id for r in to_candidates(cfg.routes[0], cfg)}
    assert receivers == {"telegram"}


def test_tag_list_is_or() -> None:
    cfg = _config(
        routes=[
            {
                "id": "tags",
                "from": {"listener_tags": ["alerts", "mail"]},
                "to": {"receivers": ["telegram"]},
            }
        ]
    )
    ids = from_candidates(cfg.routes[0], cfg)
    assert ids == {"gotify-main", "smtp-local"}


def test_route_message() -> None:
    cfg = _config()
    msg = NormalizedMessage(
        source_listener_id="gotify-main",
        title="t",
        body="b",
        priority=5,
    )
    targets = ENGINE.route(msg, cfg)
    assert len(targets) == 1
    assert targets[0].receiver.id == "telegram"

    other = NormalizedMessage(
        source_listener_id="smtp-local",
        title="t",
        body="b",
        priority=5,
    )
    assert ENGINE.route(other, cfg) == []


def test_route_requires_from_and_to() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AppConfig.model_validate(
            {
                "version": 2,
                "listeners": [
                    {
                        "id": "gotify-main",
                        "type": "gotify",
                        "options": {"host": "localhost", "client_token": "c"},
                    }
                ],
                "receivers": [
                    {
                        "id": "telegram",
                        "type": "apprise",
                        "options": {"urls": ["json://localhost"]},
                    }
                ],
                "routes": [
                    {
                        "id": "bad",
                        "from": {},
                        "to": {"receivers": ["telegram"]},
                    }
                ],
            }
        )
