from __future__ import annotations

from gotify2apprise.listeners.base import Listener, OnMessage
from gotify2apprise.listeners.gotify import GotifyListener
from gotify2apprise.listeners.smtp import SmtpListener
from gotify2apprise.models.config import ListenerConfig


def create_listener(config: ListenerConfig, on_message: OnMessage) -> Listener:
    if config.type == "gotify":
        return GotifyListener(config, on_message)
    if config.type == "smtp":
        return SmtpListener(config, on_message)
    raise ValueError(f"unknown listener type: {config.type}")
