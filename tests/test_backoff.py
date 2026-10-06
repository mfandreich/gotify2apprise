from gotify2apprise.models.config import DeliveryPolicy
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
