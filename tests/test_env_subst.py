from gotify2apprise.config.env_subst import substitute


def test_simple_var() -> None:
    assert substitute("http://${HOST}/x", env={"HOST": "a.example"}) == "http://a.example/x"


def test_default() -> None:
    assert substitute("${MISSING:-fallback}", env={}) == "fallback"


def test_nested_structures() -> None:
    data = {"a": ["${X}", 1], "b": {"c": "${Y:-z}"}}
    out = substitute(data, env={"X": "yes"})
    assert out == {"a": ["yes", 1], "b": {"c": "z"}}


def test_missing_becomes_empty() -> None:
    assert substitute("${NOPE}", env={}) == ""
