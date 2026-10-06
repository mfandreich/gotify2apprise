from __future__ import annotations

from gotify2apprise.models.config import ReceiverConfig
from gotify2apprise.receivers.apprise import AppriseReceiver
from gotify2apprise.receivers.base import Receiver


def create_receiver(config: ReceiverConfig) -> Receiver:
    if config.type == "apprise":
        return AppriseReceiver(config)
    raise ValueError(f"unknown receiver type: {config.type}")
