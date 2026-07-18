from __future__ import annotations

from collections import Counter


SEVERITY_RANK = {"S4": 4, "S3": 3, "S2": 2, "S1": 1, None: 0}
GENERIC = {"good", "nice", "ok", "okay", "good game", "不错", "好玩", "挺好玩"}


def select_representative_reviews(classified_reviews, positive_limit: int = 10, negative_limit: int = 10) -> dict[str, list]:
    positive_categories = Counter(review.category for review in classified_reviews if _sentiment(review) == "正面")
    negative_categories = Counter(review.category for review in classified_reviews if _sentiment(review) == "负面")

    positives = [
        review for review in classified_reviews
        if _sentiment(review) == "正面" and str(review.content).strip()
    ]
    negatives = [
        review for review in classified_reviews
        if _sentiment(review) == "负面" and str(review.content).strip()
    ]

    positives.sort(key=lambda review: _positive_score(review, positive_categories), reverse=True)
    negatives.sort(key=lambda review: _negative_score(review, negative_categories), reverse=True)
    return {
        "positive": _dedupe(positives, positive_limit),
        "negative": _dedupe(negatives, negative_limit),
    }


def _positive_score(review, category_counts: Counter) -> tuple[int, int, int, int]:
    content = str(review.content).strip()
    tags = getattr(review, "strength_tags", ()) or ()
    return (
        0 if content.lower() in GENERIC else 1,
        min(len(tags), 3),
        category_counts.get(review.category, 0),
        _length_score(content),
    )


def _negative_score(review, category_counts: Counter) -> tuple[int, int, int, int, int]:
    content = str(review.content).strip()
    return (
        SEVERITY_RANK.get(getattr(review, "severity", None), 0),
        1 if getattr(review, "is_blocking", False) else 0,
        category_counts.get(review.category, 0),
        0 if content.lower() in GENERIC else 1,
        _length_score(content),
    )


def _length_score(text: str) -> int:
    length = len(text)
    if 30 <= length <= 240:
        return 3
    if 10 <= length < 30 or 240 < length <= 420:
        return 2
    return 1


def _dedupe(reviews: list, limit: int) -> list:
    output = []
    seen = set()
    for review in reviews:
        key = " ".join(str(review.content).lower().split())
        if key in seen:
            continue
        seen.add(key)
        output.append(review)
        if len(output) >= limit:
            break
    return output


def _sentiment(review) -> str:
    mapping = {"positive": "正面", "neutral": "中性", "negative": "负面", "正面": "正面", "中性": "中性", "负面": "负面"}
    return mapping.get(str(review.sentiment).strip().lower(), "中性")
