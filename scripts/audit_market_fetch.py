from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.market_diagnostics import dry_run_market_fetch


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Google Play market fetch and time filtering without Claude.")
    parser.add_argument("package_id", help="Google Play package id, e.g. com.example.game")
    parser.add_argument("--today", default="", help="Reference date in YYYY-MM-DD. Defaults to local today.")
    parser.add_argument("--count", type=int, default=10, help="Target sample count per market.")
    parser.add_argument("--max-fetch", type=int, default=400, help="Maximum raw reviews fetched per market per mode.")
    args = parser.parse_args()

    today = date.fromisoformat(args.today) if args.today else None
    rows = dry_run_market_fetch(args.package_id, count=args.count, today=today, max_fetch_reviews=args.max_fetch)

    print("| 市场 | country | lang | raw | 7d | 30d | 90d | 最早评论 | 最新评论 | 页数 | 停止原因 | 状态 |")
    print("|------|---------|------|-----|----|-----|-----|----------|----------|------|----------|------|")
    for row in rows:
        print(
            "| {market_label} | {requested_country} | {requested_lang} | {raw_api_count} | "
            "{count_7d} | {count_30d} | {count_90d} | {earliest_review_time} | "
            "{latest_review_time} | {page_count} | {stop_reason} | {status} |".format(**row)
        )
        if row.get("exception_type"):
            print(f"  - {row['market_label']} error: {row['exception_type']} {row['exception_message']}")
        diagnostics = row.get("page_diagnostics") or []
        if diagnostics:
            first_page = diagnostics[0]
            print(
                "  - page1: raw={raw_count}, valid_dt={valid_datetime_count}, invalid_dt={invalid_datetime_count}, "
                "filtered={time_filtered_count}, latest={latest_review_time}, earliest={earliest_review_time}".format(**first_page)
            )


if __name__ == "__main__":
    main()
