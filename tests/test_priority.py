from gotify2apprise.models.config import RouteFilter
from gotify2apprise.routing.engine import matches_priority


def test_int_in_priorities_is_exact_value() -> None:
    filt = RouteFilter(priorities=[5])
    assert matches_priority(5, filt)
    assert not matches_priority(4, filt)
    assert not matches_priority(9, filt)


def test_keyword_priorities_expand_to_bucket() -> None:
    filt = RouteFilter(priorities=["info"])
    assert matches_priority(0, filt)
    assert matches_priority(3, filt)
    assert not matches_priority(4, filt)


def test_mixed_int_and_keyword() -> None:
    filt = RouteFilter(priorities=["info", 9, 10])
    assert matches_priority(2, filt)
    assert matches_priority(9, filt)
    assert not matches_priority(5, filt)


def test_min_priority_keyword() -> None:
    filt = RouteFilter(min_priority="warn")
    assert matches_priority(4, filt)
    assert matches_priority(10, filt)
    assert not matches_priority(3, filt)


def test_min_priority_and_allow_list() -> None:
    filt = RouteFilter(min_priority=8, priorities=["crit", 5])
    assert matches_priority(8, filt)
    assert not matches_priority(5, filt)
