from __future__ import annotations

from dataclasses import dataclass

from gotify2apprise.models.config import (
    AppConfig,
    DeliveryPolicy,
    ListenerConfig,
    ReceiverConfig,
    RouteConfig,
    RouteFilter,
    expand_priority_entry,
    min_priority_value,
)
from gotify2apprise.models.message import NormalizedMessage
from gotify2apprise.routing.templates import render_template


@dataclass(frozen=True)
class RoutedTarget:
    route: RouteConfig
    receiver: ReceiverConfig
    title: str
    body: str
    delivery: DeliveryPolicy


def matches_priority(priority: int, filt: RouteFilter | None) -> bool:
    if filt is None:
        return True
    if filt.priorities is not None:
        allowed: set[int] = set()
        for entry in filt.priorities:
            allowed |= expand_priority_entry(entry)
        if priority not in allowed:
            return False
    if filt.min_priority is not None:
        if priority < min_priority_value(filt.min_priority):
            return False
    return True


def _tagged_ids(
    items: list[ListenerConfig] | list[ReceiverConfig],
    tags: list[str],
) -> set[str]:
    wanted = set(tags)
    result: set[str] = set()
    for item in items:
        if not item.enabled:
            continue
        if wanted.intersection(item.tags):
            result.add(item.id)
    return result


def from_candidates(route: RouteConfig, config: AppConfig) -> set[str]:
    enabled = {item.id: item for item in config.listeners if item.enabled}
    ids: set[str] = set()
    for listener_id in route.from_.listeners:
        if listener_id in enabled:
            ids.add(listener_id)
    if route.from_.listener_tags:
        ids |= _tagged_ids(config.listeners, route.from_.listener_tags)
    return ids


def to_candidates(route: RouteConfig, config: AppConfig) -> list[ReceiverConfig]:
    enabled = {item.id: item for item in config.receivers if item.enabled}
    ids: set[str] = set()
    for receiver_id in route.to.receivers:
        if receiver_id in enabled:
            ids.add(receiver_id)
    if route.to.receiver_tags:
        ids |= _tagged_ids(config.receivers, route.to.receiver_tags)
    return [enabled[i] for i in ids]


class RoutingEngine:
    def route(self, message: NormalizedMessage, config: AppConfig) -> list[RoutedTarget]:
        targets: list[RoutedTarget] = []
        seen: set[tuple[str, str]] = set()
        for route in config.routes:
            if not route.enabled:
                continue
            if message.source_listener_id not in from_candidates(route, config):
                continue
            if not matches_priority(message.priority, route.filter):
                continue
            for receiver in to_candidates(route, config):
                key = (route.id, receiver.id)
                if key in seen:
                    continue
                seen.add(key)
                title_tpl = (
                    (route.templates.title if route.templates else None)
                    or config.defaults.title_template
                )
                body_tpl = (
                    (route.templates.body if route.templates else None)
                    or config.defaults.message_template
                )
                targets.append(
                    RoutedTarget(
                        route=route,
                        receiver=receiver,
                        title=render_template(title_tpl, message),
                        body=render_template(body_tpl, message),
                        delivery=config.effective_delivery(route),
                    )
                )
        return targets
