from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


TIME_MODE_LAST_7 = "最近7天"
TIME_MODE_LAST_30 = "最近30天"
TIME_MODE_LAST_90 = "最近90天"
TIME_MODE_CUSTOM = "自定义"
TIME_MODE_UNLIMITED = "最新评论（不限制时间）"

TIME_MODE_OPTIONS = [
    TIME_MODE_LAST_7,
    TIME_MODE_LAST_30,
    TIME_MODE_LAST_90,
    TIME_MODE_CUSTOM,
    TIME_MODE_UNLIMITED,
]


@dataclass(frozen=True)
class TimeScope:
    mode: str
    start_date: date | None
    end_date: date | None

    @property
    def start_key(self) -> str:
        return self.start_date.isoformat() if self.start_date else ""

    @property
    def end_key(self) -> str:
        return self.end_date.isoformat() if self.end_date else ""

    @property
    def display(self) -> str:
        if not self.start_date and not self.end_date:
            return "最新评论（不限制时间）"
        return f"{self.start_date.isoformat()} ～ {self.end_date.isoformat()}"


def resolve_time_scope(
    mode: str,
    today: date,
    custom_start: date | None = None,
    custom_end: date | None = None,
) -> TimeScope:
    if mode == TIME_MODE_LAST_7:
        return TimeScope(mode, today - timedelta(days=6), today)
    if mode == TIME_MODE_LAST_30:
        return TimeScope(mode, today - timedelta(days=29), today)
    if mode == TIME_MODE_LAST_90:
        return TimeScope(mode, today - timedelta(days=89), today)
    if mode == TIME_MODE_UNLIMITED:
        return TimeScope(mode, None, None)
    if mode == TIME_MODE_CUSTOM:
        return TimeScope(mode, custom_start, custom_end)
    raise ValueError(f"未知评论时间范围：{mode}")


def parse_date_key(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def validate_time_scope(scope: TimeScope) -> tuple[bool, str]:
    if scope.start_date and scope.end_date and scope.start_date > scope.end_date:
        return False, "开始日期不得晚于结束日期。"
    if (scope.start_date is None) ^ (scope.end_date is None):
        return False, "开始日期和结束日期必须同时存在。"
    return True, ""
