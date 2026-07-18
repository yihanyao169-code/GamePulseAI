from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from src import google_play


class Token:
    pass


def _raw_review(index: int, at) -> dict:
    return {
        "reviewId": f"review-{index}",
        "userName": f"user-{index}",
        "score": 5,
        "content": f"content-{index}",
        "at": at,
    }


def _run_with_page(monkeypatch, page: list[dict], count: int = 100, start_date=None, end_date=None):
    def fake_reviews(*args, **kwargs):
        return page, None

    monkeypatch.setattr(google_play, "reviews", fake_reviews)
    return google_play.fetch_reviews_with_meta(
        "pkg",
        count,
        start_date=start_date,
        end_date=end_date,
        max_fetch_reviews=500,
    )


def test_time_filtered_count_is_not_truncated_to_target(monkeypatch) -> None:
    page = [_raw_review(index, datetime(2026, 7, 10)) for index in range(150)]

    def fake_reviews(*args, **kwargs):
        return page, None

    monkeypatch.setattr(google_play, "reviews", fake_reviews)

    items, meta = google_play.fetch_reviews_with_meta(
        "pkg",
        100,
        start_date=datetime(2026, 7, 1).date(),
        end_date=datetime(2026, 7, 18).date(),
    )

    assert meta["raw_fetched_count"] == 150
    assert meta["time_filtered_count"] == 150
    assert meta["target_sample_count"] == 100
    assert meta["analysis_sample_count"] == 100
    assert len(items) == 100


def test_target_300_fetches_multiple_pages_instead_of_fixed_200(monkeypatch) -> None:
    calls = []
    pages = [
        [_raw_review(index, datetime(2026, 7, 10)) for index in range(200)],
        [_raw_review(index, datetime(2026, 7, 9)) for index in range(200, 400)],
    ]

    def fake_reviews(*args, **kwargs):
        calls.append(kwargs.get("count"))
        page_index = len(calls) - 1
        next_token = Token() if page_index == 0 else None
        return pages[page_index], next_token

    monkeypatch.setattr(google_play, "reviews", fake_reviews)

    items, meta = google_play.fetch_reviews_with_meta(
        "pkg",
        300,
        start_date=datetime(2026, 7, 1).date(),
        end_date=datetime(2026, 7, 18).date(),
    )

    assert calls == [200, 200]
    assert meta["raw_fetched_count"] == 400
    assert meta["time_filtered_count"] == 400
    assert meta["target_sample_count"] == 300
    assert meta["analysis_sample_count"] == 300
    assert len(items) == 300


def test_bounded_time_range_counts_all_pages_until_start_boundary(monkeypatch) -> None:
    calls = []
    pages = [
        [_raw_review(index, datetime(2026, 7, 10)) for index in range(200)],
        [_raw_review(index, datetime(2026, 7, 9)) for index in range(200, 400)],
        [_raw_review(index, datetime(2026, 6, 1)) for index in range(400, 420)],
    ]

    def fake_reviews(*args, **kwargs):
        calls.append(kwargs.get("continuation_token"))
        page_index = len(calls) - 1
        next_token = Token() if page_index < 2 else None
        return pages[page_index], next_token

    monkeypatch.setattr(google_play, "reviews", fake_reviews)

    items, meta = google_play.fetch_reviews_with_meta(
        "pkg",
        100,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 18),
        max_fetch_reviews=500,
    )

    assert len(items) == 100
    assert meta["raw_fetched_count"] == 420
    assert meta["time_filtered_count"] == 400
    assert meta["before_start_count"] == 20
    assert meta["page_count"] == 3
    assert meta["stop_reason"] == "crossed_start_boundary"


def test_unlimited_time_stops_after_target_reached(monkeypatch) -> None:
    calls = []
    pages = [
        [_raw_review(index, datetime(2026, 7, 10)) for index in range(200)],
        [_raw_review(index, datetime(2026, 7, 9)) for index in range(200, 400)],
    ]

    def fake_reviews(*args, **kwargs):
        calls.append(kwargs.get("continuation_token"))
        return pages[len(calls) - 1], Token()

    monkeypatch.setattr(google_play, "reviews", fake_reviews)

    items, meta = google_play.fetch_reviews_with_meta("pkg", 100, max_fetch_reviews=500)

    assert len(calls) == 1
    assert len(items) == 100
    assert meta["time_filtered_count"] == 200
    assert meta["stop_reason"] == "target_reached"


def test_continuation_token_is_local_to_each_market_call(monkeypatch) -> None:
    calls = []

    def fake_reviews(*args, **kwargs):
        calls.append((kwargs.get("country"), kwargs.get("continuation_token")))
        return [_raw_review(len(calls), datetime(2026, 7, 10))], None

    monkeypatch.setattr(google_play, "reviews", fake_reviews)

    google_play.fetch_reviews_with_meta("pkg", 1, country="jp", start_date=date(2026, 7, 1), end_date=date(2026, 7, 18))
    google_play.fetch_reviews_with_meta("pkg", 1, country="kr", start_date=date(2026, 7, 1), end_date=date(2026, 7, 18))

    assert calls == [("jp", None), ("kr", None)]


def test_last_7_days_filters_by_review_at_and_excludes_invalid_dates(monkeypatch) -> None:
    today = date(2026, 7, 18)
    page = [
        _raw_review(1, datetime(2026, 7, 18, 12)),
        _raw_review(2, datetime(2026, 7, 15, 12)),
        _raw_review(3, datetime(2026, 7, 11, 12)),
        _raw_review(4, datetime(2026, 7, 10, 12)),
        _raw_review(5, None),
        _raw_review(6, "not-a-date"),
        _raw_review(7, datetime(2026, 7, 18, 4, tzinfo=timezone.utc)),
    ]

    items, meta = _run_with_page(
        monkeypatch,
        page,
        start_date=today - timedelta(days=6),
        end_date=today,
    )

    assert [item.review_id for item in items] == ["review-1", "review-2", "review-7"]
    assert meta["raw_fetched_count"] == 7
    assert meta["time_filtered_count"] == 3
    assert meta["invalid_datetime_count"] == 2
    assert meta["time_filter_valid"] is True


def test_last_30_days_includes_start_and_end_natural_days(monkeypatch) -> None:
    today = date(2026, 7, 18)
    page = [
        _raw_review(1, datetime(2026, 7, 18, 23, 59)),
        _raw_review(2, datetime(2026, 6, 19, 0, 0)),
        _raw_review(3, datetime(2026, 6, 18, 23, 59)),
        _raw_review(4, datetime(2026, 7, 19, 0, 0)),
    ]

    items, meta = _run_with_page(
        monkeypatch,
        page,
        start_date=today - timedelta(days=29),
        end_date=today,
    )

    assert [item.review_id for item in items] == ["review-1", "review-2"]
    assert meta["time_filtered_count"] == 2


def test_last_90_days_boundary(monkeypatch) -> None:
    today = date(2026, 7, 18)
    page = [
        _raw_review(1, datetime(2026, 4, 20, 0, 0)),
        _raw_review(2, datetime(2026, 4, 19, 23, 59)),
        _raw_review(3, datetime(2026, 7, 18, 23, 0)),
    ]

    items, meta = _run_with_page(
        monkeypatch,
        page,
        start_date=today - timedelta(days=89),
        end_date=today,
    )

    assert [item.review_id for item in items] == ["review-1", "review-3"]
    assert meta["time_filtered_count"] == 2


def test_custom_range_includes_start_and_end_dates(monkeypatch) -> None:
    page = [
        _raw_review(1, datetime(2026, 7, 1, 0, 0)),
        _raw_review(2, datetime(2026, 7, 16, 23, 59)),
        _raw_review(3, datetime(2026, 6, 30, 23, 59)),
        _raw_review(4, datetime(2026, 7, 17, 0, 0)),
    ]

    items, meta = _run_with_page(
        monkeypatch,
        page,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 16),
    )

    assert [item.review_id for item in items] == ["review-1", "review-2"]
    assert meta["time_filtered_count"] == 2
    assert meta["resolved_start_datetime"]
    assert meta["resolved_end_datetime"]


def test_unlimited_time_does_not_filter_invalid_or_missing_dates(monkeypatch) -> None:
    page = [
        _raw_review(1, datetime(2026, 7, 18)),
        _raw_review(2, None),
        _raw_review(3, "not-a-date"),
        _raw_review(4, datetime(2026, 1, 1)),
    ]

    items, meta = _run_with_page(monkeypatch, page, count=10)

    assert len(items) == 4
    assert meta["raw_fetched_count"] == 4
    assert meta["time_filtered_count"] == 4
    assert meta["invalid_datetime_count"] == 2
    assert meta["time_filter_mode"] == "unlimited"
    assert meta["time_filter_valid"] is True


def test_time_filtered_shortage_does_not_fill_with_out_of_range_reviews(monkeypatch) -> None:
    today = date(2026, 7, 18)
    page = [
        _raw_review(1, datetime(2026, 7, 18)),
        _raw_review(2, datetime(2026, 7, 17)),
        _raw_review(3, datetime(2026, 6, 1)),
        _raw_review(4, datetime(2026, 5, 1)),
    ]

    items, meta = _run_with_page(
        monkeypatch,
        page,
        count=10,
        start_date=today - timedelta(days=6),
        end_date=today,
    )

    assert [item.review_id for item in items] == ["review-1", "review-2"]
    assert meta["time_filtered_count"] == 2
    assert meta["analysis_sample_count"] == 2


def test_timezone_aware_and_naive_datetimes_are_compared_consistently(monkeypatch) -> None:
    page = [
        _raw_review(1, datetime(2026, 7, 18, 1, 0, tzinfo=timezone.utc)),
        _raw_review(2, datetime(2026, 7, 18, 1, 0)),
    ]

    items, meta = _run_with_page(
        monkeypatch,
        page,
        start_date=date(2026, 7, 18),
        end_date=date(2026, 7, 18),
    )

    assert [item.review_id for item in items] == ["review-1", "review-2"]
    assert meta["time_filtered_count"] == 2
