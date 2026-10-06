import pytest
from pydantic import ValidationError

from gotify2apprise.models.config import AppConfig, DeliveryPolicy
from gotify2apprise.storage.queue import next_delay, next_retry_at


def test_exponential_backoff() -> None:
    row = {"initial_delay_sec": 30, "max_delay_sec": 3600, "backoff": "exponential"}
    assert next_delay(row, 1) == 30
    assert next_delay(row, 2) == 60
    assert next_delay(row, 3) == 120
    assert next_delay({"initial_delay_sec": 30, "max_delay_sec": 50, "backoff": "exponential"}, 4) == 50


def test_fixed_backoff() -> None:
    row = {"initial_delay_sec": 15, "max_delay_sec": 100, "backoff": "fixed"}
    assert next_delay(row, 1) == 15
    assert next_delay(row, 8) == 15


def test_next_retry_at_uses_policy() -> None:
    policy = DeliveryPolicy(initial_delay_sec=10, backoff="fixed", max_delay_sec=10)
    nxt = next_retry_at(policy, 1)
    assert nxt.tzinfo is not None


def test_unlimited_exponential_requires_max_delay_sec() -> None:
    with pytest.raises(ValidationError, match="max_delay_sec is required"):
        AppConfig.model_validate(
            {
                "version": 2,
                "defaults": {"delivery": {"max_attempts": 0, "backoff": "exponential"}},
            }
        )


def test_unlimited_exponential_with_cap_ok() -> None:
    cfg = AppConfig.model_validate(
        {
            "version": 2,
            "defaults": {
                "delivery": {
                    "max_attempts": 0,
                    "backoff": "exponential",
                    "max_delay_sec": 120,
                }
            },
        }
    )
    assert cfg.defaults.delivery.max_attempts == 0
    assert cfg.defaults.delivery.max_delay_sec == 120


def test_unlimited_fixed_without_cap_ok() -> None:
    cfg = AppConfig.model_validate(
        {"version": 2, "defaults": {"delivery": {"max_attempts": 0, "backoff": "fixed"}}}
    )
    assert cfg.defaults.delivery.max_attempts == 0


def test_route_unlimited_exponential_inherits_cap() -> None:
    cfg = AppConfig.model_validate(
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
            "defaults": {
                "delivery": {
                    "backoff": "exponential",
                    "max_delay_sec": 90,
                }
            },
            "routes": [
                {
                    "id": "r1",
                    "from": {"listeners": ["gotify-main"]},
                    "to": {"receivers": ["telegram"]},
                    "delivery": {"max_attempts": 0},
                }
            ],
        }
    )
    assert cfg.effective_delivery(cfg.routes[0]).max_attempts == 0
    assert cfg.effective_delivery(cfg.routes[0]).max_delay_sec == 90


def test_route_unlimited_exponential_without_cap_fails() -> None:
    with pytest.raises(ValidationError, match="max_delay_sec is required"):
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
                        "id": "r1",
                        "from": {"listeners": ["gotify-main"]},
                        "to": {"receivers": ["telegram"]},
                        "delivery": {"max_attempts": 0, "backoff": "exponential"},
                    }
                ],
            }
        )

