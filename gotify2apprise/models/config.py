from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from gotify2apprise.datetime_fmt import DEFAULT_DATETIME_FORMAT, format_datetime

PriorityKeyword = Literal["info", "warn", "crit"]
BackoffKind = Literal["fixed", "exponential"]

INFO_PRIORITIES = (0, 1, 2, 3)
WARN_PRIORITIES = (4, 5, 6, 7)
CRIT_PRIORITIES = (8, 9, 10)

KEYWORD_MIN: dict[str, int] = {"info": 0, "warn": 4, "crit": 8}
KEYWORD_RANGE: dict[str, tuple[int, ...]] = {
    "info": INFO_PRIORITIES,
    "warn": WARN_PRIORITIES,
    "crit": CRIT_PRIORITIES,
}


def priority_bucket(priority: int) -> str:
    if priority < 4:
        return "info"
    if priority < 8:
        return "warn"
    return "crit"


def min_priority_value(value: int | str) -> int:
    if isinstance(value, int):
        return value
    key = str(value).lower()
    if key not in KEYWORD_MIN:
        raise ValueError(f"unknown priority keyword: {value}")
    return KEYWORD_MIN[key]


def normalize_mailbox(value: str) -> str:
    """Lowercase SMTP addr-spec without angle brackets. Keeps domain if present."""
    return value.strip().strip("<>").strip().lower()


def mailbox_local_part(value: str) -> str:
    text = normalize_mailbox(value)
    if "@" in text:
        return text.split("@", 1)[0]
    return text


def mailbox_domain(value: str) -> str | None:
    text = normalize_mailbox(value)
    if "@" not in text:
        return None
    return text.split("@", 1)[1] or None


def reject_unlimited_exponential_without_cap(policy: DeliveryPolicy) -> None:
    if (
        policy.max_attempts == 0
        and policy.backoff == "exponential"
        and "max_delay_sec" not in policy.model_fields_set
    ):
        raise ValueError(
            "max_delay_sec is required when backoff is exponential and max_attempts is 0"
        )


def expand_priority_entry(value: int | str) -> set[int]:
    if isinstance(value, int):
        return {value}
    key = str(value).lower()
    if key not in KEYWORD_RANGE:
        raise ValueError(f"unknown priority keyword: {value}")
    return set(KEYWORD_RANGE[key])


class GotifyOptions(BaseModel):
    host: str
    client_token: str
    ssl: bool = False
    app_tokens: list[str] = Field(default_factory=lambda: ["all"])

    @field_validator("host")
    @classmethod
    def host_without_scheme(cls, value: str) -> str:
        stripped = value.strip()
        if stripped.lower().startswith(("http://", "https://", "ws://", "wss://")):
            raise ValueError("host must not include a URL scheme")
        if not stripped:
            raise ValueError("host is required")
        return stripped


class SmtpOptions(BaseModel):
    host: str = "0.0.0.0"
    port: int = 2525
    hostname: str | None = None
    default_priority: int = 5
    mailboxes: list[str] = Field(default_factory=list)

    @field_validator("mailboxes")
    @classmethod
    def mailboxes_normalized(cls, value: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for item in value:
            name = normalize_mailbox(item)
            if not name or not mailbox_local_part(name):
                raise ValueError("mailbox must not be empty")
            if name.endswith("@"):
                raise ValueError(f"mailbox {item!r} needs a domain after @")
            if name in seen:
                raise ValueError(f"duplicate mailbox {name!r}")
            seen.add(name)
            out.append(name)
        return out


class AppriseOptions(BaseModel):
    urls: list[str]

    @field_validator("urls")
    @classmethod
    def urls_not_empty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("at least one Apprise URL is required")
        return value


class ListenerConfig(BaseModel):
    id: str
    type: Literal["gotify", "smtp"]
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_options(self) -> ListenerConfig:
        if self.type == "gotify":
            GotifyOptions.model_validate(self.options)
        elif self.type == "smtp":
            SmtpOptions.model_validate(self.options)
        return self

    def gotify(self) -> GotifyOptions:
        return GotifyOptions.model_validate(self.options)

    def smtp(self) -> SmtpOptions:
        return SmtpOptions.model_validate(self.options)


class ReceiverConfig(BaseModel):
    id: str
    type: Literal["apprise"]
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_options(self) -> ReceiverConfig:
        if self.type == "apprise":
            AppriseOptions.model_validate(self.options)
        return self

    def apprise(self) -> AppriseOptions:
        return AppriseOptions.model_validate(self.options)


class RouteFrom(BaseModel):
    listeners: list[str] = Field(default_factory=list)
    listener_tags: list[str] = Field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.listeners and not self.listener_tags


class RouteTo(BaseModel):
    receivers: list[str] = Field(default_factory=list)
    receiver_tags: list[str] = Field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.receivers and not self.receiver_tags


class RouteFilter(BaseModel):
    min_priority: int | str | None = None
    priorities: list[int | str] | None = None


class RouteTemplates(BaseModel):
    title: str | None = None
    body: str | None = None


class DeliveryPolicy(BaseModel):
    max_attempts: int = 5
    initial_delay_sec: int = 30
    backoff: BackoffKind = "exponential"
    max_delay_sec: int = 3600

    @field_validator("max_attempts")
    @classmethod
    def attempts_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("max_attempts must be >= 0 (0 = unlimited)")
        return value


class RouteConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    enabled: bool = True
    from_: RouteFrom = Field(alias="from")
    to: RouteTo
    filter: RouteFilter | None = None
    templates: RouteTemplates | None = None
    delivery: DeliveryPolicy | None = None

    @model_validator(mode="after")
    def from_to_required(self) -> RouteConfig:
        if self.from_.is_empty():
            raise ValueError(
                f"route {self.id}: from needs listeners or listener_tags"
            )
        if self.to.is_empty():
            raise ValueError(
                f"route {self.id}: to needs receivers or receiver_tags"
            )
        return self


class DefaultsConfig(BaseModel):
    title_template: str = "$title"
    message_template: str = "$message"
    datetime_format: str = DEFAULT_DATETIME_FORMAT
    delivery: DeliveryPolicy = Field(default_factory=DeliveryPolicy)

    @field_validator("datetime_format")
    @classmethod
    def datetime_format_usable(cls, value: str) -> str:
        pattern = value.strip()
        if not pattern:
            raise ValueError("datetime_format must not be empty")
        probe = datetime(2026, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc)
        try:
            format_datetime(probe, pattern)
        except Exception as exc:
            raise ValueError(f"invalid datetime_format: {exc}") from exc
        return pattern

    @model_validator(mode="after")
    def unlimited_exponential_needs_cap(self) -> DefaultsConfig:
        reject_unlimited_exponential_without_cap(self.delivery)
        return self


class AppConfig(BaseModel):
    version: Literal[2] = 2
    listeners: list[ListenerConfig] = Field(default_factory=list)
    receivers: list[ReceiverConfig] = Field(default_factory=list)
    routes: list[RouteConfig] = Field(default_factory=list)
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)

    @model_validator(mode="after")
    def unique_ids(self) -> AppConfig:
        for label, items in (
            ("listener", self.listeners),
            ("receiver", self.receivers),
            ("route", self.routes),
        ):
            ids = [item.id for item in items]
            dupes = {i for i in ids if ids.count(i) > 1}
            if dupes:
                raise ValueError(f"duplicate {label} id(s): {sorted(dupes)}")
        return self

    @model_validator(mode="after")
    def unlimited_exponential_routes(self) -> AppConfig:
        for route in self.routes:
            try:
                self.effective_delivery(route)
            except ValueError as exc:
                raise ValueError(f"route {route.id}: {exc}") from exc
        return self

    @model_validator(mode="after")
    def smtp_shared_binds(self) -> AppConfig:
        groups: dict[tuple[str, int], list[ListenerConfig]] = defaultdict(list)
        for item in self.listeners:
            if item.type != "smtp" or not item.enabled:
                continue
            opts = item.smtp()
            groups[(opts.host, opts.port)].append(item)
        for (host, port), items in groups.items():
            if len(items) < 2:
                continue
            missing = [item.id for item in items if not item.smtp().mailboxes]
            if missing:
                raise ValueError(
                    "SMTP listeners "
                    + ", ".join(missing)
                    + f" share {host}:{port} but have empty mailboxes; "
                    "set options.mailboxes to split by recipient, or use different ports"
                )
            owners: dict[str, str] = {}
            for item in items:
                for box in item.smtp().mailboxes:
                    if box in owners:
                        raise ValueError(
                            f"mailbox {box!r} is used by both {owners[box]} and {item.id}"
                        )
                    owners[box] = item.id
        return self

    def listener_by_id(self, listener_id: str) -> ListenerConfig | None:
        for item in self.listeners:
            if item.id == listener_id:
                return item
        return None

    def receiver_by_id(self, receiver_id: str) -> ReceiverConfig | None:
        for item in self.receivers:
            if item.id == receiver_id:
                return item
        return None

    def route_by_id(self, route_id: str) -> RouteConfig | None:
        for item in self.routes:
            if item.id == route_id:
                return item
        return None

    def effective_delivery(self, route: RouteConfig) -> DeliveryPolicy:
        base = self.defaults.delivery
        if route.delivery is None:
            return base
        merged = base.model_copy(update=route.delivery.model_dump(exclude_unset=True))
        reject_unlimited_exponential_without_cap(merged)
        return merged
