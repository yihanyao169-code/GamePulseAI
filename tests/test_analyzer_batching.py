from __future__ import annotations

import json
import re
from collections import Counter

from src.analyzer import CLASSIFICATION_SCHEMA_VERSION, classify_reviews
from src.models import ReviewItem


class FakeClaudeClient:
    def __init__(self, fail_once_batches: set[int] | None = None, fail_always_batches: set[int] | None = None, omit_review_id: int | None = None) -> None:
        self.fail_once_batches = fail_once_batches or set()
        self.fail_always_batches = fail_always_batches or set()
        self.omit_review_id = omit_review_id
        self.calls: list[tuple[list[int], int]] = []
        self.batch_attempts: Counter[int] = Counter()

    def complete(self, prompt: str, max_tokens: int = 4096) -> str:
        pairs = [(int(match.group(1)), match.group(2)) for match in re.finditer(r'^(\d+)\. rating=.*? text="(.*)"$', prompt, flags=re.MULTILINE)]
        ids = [review_id for review_id, _text in pairs]
        batch_key = ids[0] if ids else 0
        self.calls.append((ids, max_tokens))
        self.batch_attempts[batch_key] += 1
        if batch_key in self.fail_always_batches:
            raise ConnectionError("simulated Connection error")
        if batch_key in self.fail_once_batches and self.batch_attempts[batch_key] == 1:
            raise ConnectionError("simulated Connection error")
        payload = []
        for review_id, text in pairs:
            if review_id == self.omit_review_id:
                continue
            payload.append({
                "review_id": review_id,
                "category": "BUG" if "bug" in text else "游戏玩法",
                "sentiment": "negative" if "bug" in text else "positive",
                "severity": "S3" if "bug" in text else None,
                "is_blocking": False,
                "strength_tags": [] if "bug" in text else ["核心玩法"],
            })
        return json.dumps(payload, ensure_ascii=False)


def _reviews(count: int) -> list[ReviewItem]:
    return [
        ReviewItem(
            review_id=str(index),
            user_name=f"user-{index}",
            score=5,
            content=f"review-{index}",
            date="2026-07-16",
        )
        for index in range(count)
    ]


def test_97_reviews_batch_size_25_merges_all_batches_in_order() -> None:
    result = classify_reviews(_reviews(97), FakeClaudeClient(), batch_size=25, max_workers=2)

    assert len(result.classified_reviews) == 97
    assert [review.review_id for review in result.classified_reviews] == list(range(1, 98))
    assert sum(result.category_counts.values()) == 97
    assert [item["input_count"] for item in result.batch_diagnostics or []] == [25, 25, 25, 22]
    assert Counter(review.source_batch for review in result.classified_reviews) == {1: 25, 2: 25, 3: 25, 4: 22}
    assert all(review.schema_version == CLASSIFICATION_SCHEMA_VERSION for review in result.classified_reviews)


def test_connection_error_retries_failed_batch_only() -> None:
    client = FakeClaudeClient(fail_once_batches={26})
    result = classify_reviews(_reviews(50), client, batch_size=25, max_workers=1)

    assert len(result.classified_reviews) == 50
    diagnostics = result.batch_diagnostics or []
    second = next(item for item in diagnostics if item["batch"] == "2")
    assert second["retry_count"] == 1
    assert client.batch_attempts[1] == 1
    assert client.batch_attempts[26] == 2


def test_large_failed_batch_is_split_into_smaller_batches() -> None:
    client = FakeClaudeClient(fail_always_batches={26})
    result = classify_reviews(_reviews(60), client, batch_size=25, max_workers=1)

    diagnostics = result.batch_diagnostics or []
    assert any(item["batch"] == "2.1" for item in diagnostics)
    assert any(item["batch"] == "2.2" for item in diagnostics)
    assert any(item["batch"] == "2.3" for item in diagnostics)
    assert len(result.classified_reviews) == 50
    assert set(result.failed_review_ids or []) >= set(range(26, 36))


def test_single_batch_failure_does_not_drop_other_batches() -> None:
    result = classify_reviews(_reviews(65), FakeClaudeClient(fail_always_batches={26}), batch_size=25, max_workers=1)
    assert len(result.classified_reviews) == 55
    assert sum(result.category_counts.values()) == 55


def test_missing_review_id_is_detected_without_dropping_other_reviews() -> None:
    result = classify_reviews(_reviews(12), FakeClaudeClient(omit_review_id=5), batch_size=12, max_workers=1)

    assert len(result.classified_reviews) == 11
    assert 5 in (result.failed_review_ids or [])
    assert len({review.review_id for review in result.classified_reviews}) == 11


def test_severity_null_does_not_filter_non_risk_review() -> None:
    result = classify_reviews(_reviews(3), FakeClaudeClient(), batch_size=3, max_workers=1)
    assert len(result.classified_reviews) == 3
    assert all(review.severity is None for review in result.classified_reviews)
