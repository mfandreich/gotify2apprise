from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from gotify2apprise.datetime_fmt import (
    DEFAULT_DATETIME_FORMAT,
    format_datetime,
    format_delivery_rows,
)
from gotify2apprise.models.config import AppConfig, DefaultsConfig

SAMPLE = datetime(2026, 10, 6, 17, 51, 7, 160702, tzinfo=timezone.utc)


def test_default_three_millisecond_digits() -> None:
    assert format_datetime(SAMPLE) == "2026-10-06 17:51:07.160"
    assert DEFAULT_DATETIME_FORMAT == "%Y-%m-%d %H:%M:%S.%f"


def test_iso_string_and_zulu() -> None:
    assert format_datetime("2026-10-06T17:51:07.160702+00:00") == "2026-10-06 17:51:07.160"
    assert format_datetime("2026-10-06T17:51:07.160702Z") == "2026-10-06 17:51:07.160"


def test_custom_format() -> None:
    assert format_datetime(SAMPLE, "%Y/%m/%d %H:%M") == "2026/10/06 17:51"


def test_literal_percent_and_unparsed() -> None:
    assert format_datetime(SAMPLE, "%%f %f") == "%f 160"
    assert format_datetime("not-a-date") == "not-a-date"
    assert format_datetime(None) == ""


def test_format_delivery_rows() -> None:
    rows = format_delivery_rows(
        [{"id": "1", "created_at": SAMPLE.isoformat(), "status": "ok"}]
    )
    assert rows[0]["created_at"] == "2026-10-06 17:51:07.160"
    assert rows[0]["status"] == "ok"


def test_config_default_and_custom() -> None:
    cfg = AppConfig.model_validate({"version": 2})
    assert cfg.defaults.datetime_format == DEFAULT_DATETIME_FORMAT
    custom = DefaultsConfig(datetime_format="%d.%m.%Y %H:%M:%S")
    assert custom.datetime_format == "%d.%m.%Y %H:%M:%S"


def test_empty_datetime_format_rejected() -> None:
    with pytest.raises(ValidationError):
        DefaultsConfig(datetime_format="  ")
