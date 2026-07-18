from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from src.google_play import fetch_reviews_with_meta
from src.market_config import MARKET_CONFIG


def dry_run_market_fetch(
    package_id: str,
    count: int = 10,
    today: date | None = None,
    max_fetch_reviews: int = 400,
) -> list[dict[str, Any]]:
    today = today or date.today()
    rows: list[dict[str, Any]] = []
    for country, config in MARKET_CONFIG.items():
        lang = config["default_language"]
        row = {
            "market_label": config["label"],
            "requested_country": country,
            "requested_lang": lang,
            "raw_api_count": 0,
            "count_7d": 0,
            "count_30d": 0,
            "count_90d": 0,
            "unlimited_count": 0,
            "earliest_review_time": "",
            "latest_review_time": "",
            "page_count": 0,
            "stop_reason": "",
            "exception_type": "",
            "exception_message": "",
            "app_available": None,
            "status": "request_failed",
            "page_diagnostics": [],
        }
        try:
            _, unlimited_meta = fetch_reviews_with_meta(
                package_id,
                count,
                country=country,
                lang=lang,
                max_fetch_reviews=max_fetch_reviews,
            )
            _, meta_7 = fetch_reviews_with_meta(
                package_id,
                count,
                country=country,
                lang=lang,
                start_date=today - timedelta(days=6),
                end_date=today,
                max_fetch_reviews=max_fetch_reviews,
            )
            _, meta_30 = fetch_reviews_with_meta(
                package_id,
                count,
                country=country,
                lang=lang,
                start_date=today - timedelta(days=29),
                end_date=today,
                max_fetch_reviews=max_fetch_reviews,
            )
            _, meta_90 = fetch_reviews_with_meta(
                package_id,
                count,
                country=country,
                lang=lang,
                start_date=today - timedelta(days=89),
                end_date=today,
                max_fetch_reviews=max_fetch_reviews,
            )
            row["raw_api_count"] = unlimited_meta.get("raw_api_count", 0)
            row["unlimited_count"] = unlimited_meta.get("time_filtered_count", 0)
            row["count_7d"] = meta_7.get("time_filtered_count", 0)
            row["count_30d"] = meta_30.get("time_filtered_count", 0)
            row["count_90d"] = meta_90.get("time_filtered_count", 0)
            row["earliest_review_time"] = unlimited_meta.get("earliest_raw_review_time", "")
            row["latest_review_time"] = unlimited_meta.get("latest_raw_review_time", "")
            row["page_count"] = meta_30.get("page_count", 0)
            row["stop_reason"] = meta_30.get("stop_reason", "")
            row["page_diagnostics"] = meta_30.get("page_diagnostics", [])
            row["status"] = "success" if row["raw_api_count"] else "no_reviews"
            row["app_available"] = bool(row["raw_api_count"])
        except Exception as exc:
            row["exception_type"] = type(exc).__name__
            row["exception_message"] = str(exc)
            lowered = str(exc).lower()
            if "not found" in lowered or "404" in lowered or "not exist" in lowered:
                row["status"] = "app_unavailable"
                row["app_available"] = False
            elif "language" in lowered or "lang" in lowered or "hl" in lowered:
                row["status"] = "unsupported_language"
            else:
                row["status"] = "request_failed"
        rows.append(row)
    return rows
