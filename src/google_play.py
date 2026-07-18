from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from google_play_scraper import Sort, reviews

from src.models import DEFAULT_COUNTRY, DEFAULT_LANGUAGE, ReviewItem


MAX_FETCH_REVIEWS = 1000
PROJECT_TIMEZONE = timezone(timedelta(hours=8))
FETCH_CACHE_VERSION = "fetch_v3_time_audit"


def extract_package_name(raw_input: str) -> str:
    value = raw_input.strip()
    if not value:
        raise ValueError("请输入 Google Play 链接或游戏包名。")

    if "://" not in value:
        return value

    parsed = urlparse(value)
    query = parse_qs(parsed.query)
    package_names = query.get("id")
    if not package_names or not package_names[0].strip():
        raise ValueError("链接中没有找到 id 参数，请确认 Google Play 链接是否正确。")

    return package_names[0].strip()


def fetch_reviews(
    package_name: str,
    count: int,
    lang: str = DEFAULT_LANGUAGE,
    country: str = DEFAULT_COUNTRY,
    start_date: date | None = None,
    end_date: date | None = None,
    max_fetch_reviews: int = MAX_FETCH_REVIEWS,
) -> list[ReviewItem]:
    items, _meta = fetch_reviews_with_meta(
        package_name,
        count,
        lang=lang,
        country=country,
        start_date=start_date,
        end_date=end_date,
        max_fetch_reviews=max_fetch_reviews,
    )
    return items


def fetch_reviews_with_meta(
    package_name: str,
    count: int,
    lang: str = DEFAULT_LANGUAGE,
    country: str = DEFAULT_COUNTRY,
    start_date: date | None = None,
    end_date: date | None = None,
    max_fetch_reviews: int = MAX_FETCH_REVIEWS,
) -> tuple[list[ReviewItem], dict]:
    if count <= 0:
        raise ValueError("评论数量必须大于 0。")

    time_filtered_items = []
    raw_review_times: list[datetime] = []
    filtered_review_times: list[datetime] = []
    raw_fetched_count = 0
    valid_datetime_count = 0
    invalid_datetime_count = 0
    before_start_count = 0
    after_end_count = 0
    page_count_seen = 0
    page_diagnostics: list[dict] = []
    continuation_token = None
    reached_before_start = False
    stop_reason = "unknown"
    start_dt, end_dt = _resolve_datetime_bounds(start_date, end_date)
    is_unlimited = start_dt is None and end_dt is None

    while raw_fetched_count < max_fetch_reviews:
        if is_unlimited and len(time_filtered_items) >= count:
            stop_reason = "target_reached"
            break
        page_count = min(200, max_fetch_reviews - raw_fetched_count)
        raw_reviews, continuation_token = reviews(
            package_name,
            lang=lang,
            country=country,
            sort=Sort.NEWEST,
            count=page_count,
            filter_score_with=None,
            continuation_token=continuation_token,
        )
        page_count_seen += 1
        if not raw_reviews:
            stop_reason = "no_more_pages"
            break
        raw_fetched_count += len(raw_reviews)
        page_times: list[datetime] = []
        page_filtered_count = 0
        page_invalid_count = 0
        page_before_start_count = 0
        page_after_end_count = 0
        for item in raw_reviews:
            review_dt = _parse_review_datetime(item.get("at"))
            if review_dt:
                valid_datetime_count += 1
                raw_review_times.append(review_dt)
                page_times.append(review_dt)
            else:
                invalid_datetime_count += 1
                page_invalid_count += 1
                if not is_unlimited:
                    continue
            if not is_unlimited and review_dt:
                if start_dt and review_dt < start_dt:
                    reached_before_start = True
                    before_start_count += 1
                    page_before_start_count += 1
                    continue
                if end_dt and review_dt >= end_dt:
                    after_end_count += 1
                    page_after_end_count += 1
                    continue
                filtered_review_times.append(review_dt)
                page_filtered_count += 1
            elif review_dt:
                filtered_review_times.append(review_dt)
                page_filtered_count += 1
            time_filtered_items.append(item)
        page_diagnostics.append(
            {
                "page": page_count_seen,
                "raw_count": len(raw_reviews),
                "valid_datetime_count": len(page_times),
                "invalid_datetime_count": page_invalid_count,
                "time_filtered_count": page_filtered_count,
                "before_start_count": page_before_start_count,
                "after_end_count": page_after_end_count,
                "earliest_review_time": _format_datetime(min(page_times) if page_times else None),
                "latest_review_time": _format_datetime(max(page_times) if page_times else None),
                "has_continuation_token": continuation_token is not None,
            }
        )
        if reached_before_start:
            stop_reason = "crossed_start_boundary"
            break
        if continuation_token is None:
            stop_reason = "no_more_pages"
            break
    if raw_fetched_count >= max_fetch_reviews and stop_reason == "unknown":
        stop_reason = "max_fetch_reviews_reached"
    if stop_reason == "unknown":
        stop_reason = "target_reached" if is_unlimited else "completed"
    analysis_items = time_filtered_items[:count]
    time_filter_valid = _validate_time_filter_result(
        time_filtered_items,
        start_dt,
        end_dt,
        raw_fetched_count,
        is_unlimited,
    )

    return [
        ReviewItem(
            review_id=str(item.get("reviewId", "")),
            user_name=str(item.get("userName", "")),
            score=item.get("score"),
            content=str(item.get("content", "")),
            date=_format_review_item_date(item.get("at")),
        )
        for item in analysis_items
    ], {
        "raw_fetched_count": raw_fetched_count,
        "raw_api_count": raw_fetched_count,
        "valid_datetime_count": valid_datetime_count,
        "time_filtered_count": len(time_filtered_items),
        "target_sample_count": count,
        "analysis_sample_count": len(analysis_items),
        "reached_before_start": reached_before_start,
        "before_start_count": before_start_count,
        "after_end_count": after_end_count,
        "max_fetch_reviews": max_fetch_reviews,
        "page_count": page_count_seen,
        "stop_reason": stop_reason,
        "time_filter_mode": "unlimited" if is_unlimited else "bounded",
        "resolved_start_datetime": _format_datetime(start_dt),
        "resolved_end_datetime": _format_datetime(end_dt - timedelta(microseconds=1) if end_dt else None),
        "earliest_raw_review_time": _format_datetime(min(raw_review_times) if raw_review_times else None),
        "latest_raw_review_time": _format_datetime(max(raw_review_times) if raw_review_times else None),
        "earliest_filtered_review_time": _format_datetime(min(filtered_review_times) if filtered_review_times else None),
        "latest_filtered_review_time": _format_datetime(max(filtered_review_times) if filtered_review_times else None),
        "invalid_datetime_count": invalid_datetime_count,
        "time_filter_valid": time_filter_valid,
        "page_diagnostics": page_diagnostics,
        "fetch_cache_version": FETCH_CACHE_VERSION,
    }


def _resolve_datetime_bounds(
    start_date: date | None,
    end_date: date | None,
    tz: timezone = PROJECT_TIMEZONE,
) -> tuple[datetime | None, datetime | None]:
    if not start_date and not end_date:
        return None, None
    if not start_date or not end_date:
        raise ValueError("开始日期和结束日期必须同时存在。")
    start_local = datetime.combine(start_date, time.min, tzinfo=tz)
    end_exclusive_local = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=tz)
    return start_local.astimezone(timezone.utc), end_exclusive_local.astimezone(timezone.utc)


def _parse_review_datetime(value: object, tz: timezone = PROJECT_TIMEZONE) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        raw = value.strip()
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return parsed.astimezone(timezone.utc)


def _format_datetime(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def _format_review_item_date(value: object) -> str:
    parsed = _parse_review_datetime(value)
    if not parsed:
        return ""
    return parsed.astimezone(PROJECT_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")


def _validate_time_filter_result(
    time_filtered_items: list[dict],
    start_dt: datetime | None,
    end_dt: datetime | None,
    raw_fetched_count: int,
    is_unlimited: bool,
) -> bool:
    if is_unlimited:
        return len(time_filtered_items) == raw_fetched_count
    for item in time_filtered_items:
        review_dt = _parse_review_datetime(item.get("at"))
        if not review_dt:
            return False
        if start_dt and review_dt < start_dt:
            return False
        if end_dt and review_dt >= end_dt:
            return False
    return True
