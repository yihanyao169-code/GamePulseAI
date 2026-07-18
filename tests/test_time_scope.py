from __future__ import annotations

from datetime import date

from src import time_scope


def test_last_30_days_scope() -> None:
    scope = time_scope.resolve_time_scope(time_scope.TIME_MODE_LAST_30, date(2026, 7, 18))
    assert scope.start_date == date(2026, 6, 19)
    assert scope.end_date == date(2026, 7, 18)
    assert time_scope.validate_time_scope(scope)[0] is True


def test_last_90_days_scope() -> None:
    scope = time_scope.resolve_time_scope(time_scope.TIME_MODE_LAST_90, date(2026, 7, 18))
    assert scope.start_date == date(2026, 4, 20)
    assert scope.end_date == date(2026, 7, 18)


def test_custom_scope() -> None:
    scope = time_scope.resolve_time_scope(
        time_scope.TIME_MODE_CUSTOM,
        date(2026, 7, 18),
        date(2026, 7, 1),
        date(2026, 7, 16),
    )
    assert scope.display == "2026-07-01 ～ 2026-07-16"


def test_invalid_custom_scope() -> None:
    scope = time_scope.resolve_time_scope(
        time_scope.TIME_MODE_CUSTOM,
        date(2026, 7, 18),
        date(2026, 7, 16),
        date(2026, 7, 1),
    )
    valid, message = time_scope.validate_time_scope(scope)
    assert valid is False
    assert "开始日期不得晚于结束日期" in message


def test_unlimited_scope_has_empty_cache_keys() -> None:
    scope = time_scope.resolve_time_scope(time_scope.TIME_MODE_UNLIMITED, date(2026, 7, 18))
    assert scope.start_date is None
    assert scope.end_date is None
    assert scope.start_key == ""
    assert scope.end_key == ""
