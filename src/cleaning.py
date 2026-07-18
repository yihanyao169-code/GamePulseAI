from __future__ import annotations

import re

from src.models import ReviewItem


WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    cleaned = WHITESPACE_RE.sub(" ", text.replace("\u200b", " ")).strip()
    return cleaned


def clean_reviews(
    reviews: list[ReviewItem],
    min_length: int = 2,
    max_length: int = 1200,
) -> list[ReviewItem]:
    seen: set[str] = set()
    cleaned_reviews: list[ReviewItem] = []

    for review in reviews:
        content = normalize_text(review.content)
        if len(content) < min_length:
            continue

        content = content[:max_length]
        dedupe_key = content.lower()
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        cleaned_reviews.append(
            ReviewItem(
                review_id=review.review_id,
                user_name=review.user_name,
                score=review.score,
                content=content,
                date=review.date,
            )
        )

    return cleaned_reviews
