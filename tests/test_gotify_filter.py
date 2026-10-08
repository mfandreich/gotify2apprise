from gotify2apprise.listeners.gotify import (
    accept_gotify_app,
    app_tokens_unusable_without_api_tokens,
)
from gotify2apprise.models.config import GotifyOptions


def test_empty_filters_accept_all() -> None:
    app = {"id": 1, "name": "NAS", "token": "x"}
    assert accept_gotify_app(app, app_tokens=[], app_names=[])


def test_all_in_app_tokens_accepts_any_app() -> None:
    app = {"id": 1, "name": "NAS", "token": "x"}
    assert accept_gotify_app(app, app_tokens=["all"], app_names=["Proxmox"])


def test_app_tokens_match_token_field_only() -> None:
    app = {"id": 1, "name": "NAS", "token": "Axxxxxxxx000001"}
    assert accept_gotify_app(app, app_tokens=["Axxxxxxxx000001"], app_names=[])
    assert not accept_gotify_app(app, app_tokens=["Axxxxxxxx000002"], app_names=[])
    assert not accept_gotify_app(app, app_tokens=["NAS"], app_names=[])


def test_app_names_match_name_only() -> None:
    app = {"id": 5, "name": "kuma"}
    assert accept_gotify_app(app, app_tokens=[], app_names=["kuma"])
    assert accept_gotify_app(app, app_tokens=[], app_names=["KUMA"])
    assert not accept_gotify_app(app, app_tokens=[], app_names=["NAS"])
    assert not accept_gotify_app(app, app_tokens=["kuma"], app_names=[])


def test_token_or_name_when_both_set() -> None:
    app = {"id": 1, "name": "NAS", "token": "Axxxxxxxx000001"}
    assert accept_gotify_app(app, app_tokens=["nope"], app_names=["NAS"])
    assert accept_gotify_app(app, app_tokens=["Axxxxxxxx000001"], app_names=["nope"])


def test_gotify3_tokenless_api_breaks_app_tokens() -> None:
    apps = {1: {"id": 1, "name": "NAS"}}
    assert app_tokens_unusable_without_api_tokens(apps, ["Axxxxxxxx000001"])
    assert not app_tokens_unusable_without_api_tokens(apps, ["all"])
    assert not app_tokens_unusable_without_api_tokens(apps, [])
    apps_with_token = {1: {"id": 1, "name": "NAS", "token": "Axxxxxxxx000001"}}
    assert not app_tokens_unusable_without_api_tokens(apps_with_token, ["Axxxxxxxx000001"])


def test_gotify_options_defaults() -> None:
    opts = GotifyOptions(host="gotify:80", client_token="tok")
    assert opts.app_tokens == []
    assert opts.app_names == []
