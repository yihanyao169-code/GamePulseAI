from __future__ import annotations

from dataclasses import dataclass


REVIEW_CATEGORIES = [
    "游戏玩法",
    "BUG",
    "性能优化",
    "氪金",
    "UI体验",
    "美术",
    "活动运营",
    "新手引导",
    "社交",
    "整体评价",
    "其他",
]


DEFAULT_LANGUAGE = "en"
DEFAULT_COUNTRY = "us"
DEFAULT_REVIEW_COUNT = 100
CLAUDE_MODEL = "claude-sonnet-5"


@dataclass(frozen=True)
class ReviewItem:
    review_id: str
    user_name: str
    score: int | None
    content: str
    date: str


@dataclass(frozen=True)
class ClassifiedReview:
    content: str
    category: str
    sentiment: str
    reason: str
    severity: str | None = None
    is_blocking: bool | None = None
    strength_tags: tuple[str, ...] = ()
    source_batch: int | None = None
    review_id: int | str | None = None
    score: int | None = None
    date: str = ""
    version: str = ""
    country: str = ""
    schema_version: str = ""


@dataclass(frozen=True)
class AnalysisResult:
    classified_reviews: list[ClassifiedReview]
    category_counts: dict[str, int]
    most_satisfied: list[str]
    most_unsatisfied: list[str]
    summary: str
    batch_diagnostics: list[dict] | None = None
    failed_review_ids: list[int | str] | None = None
    cache_hit: bool = False
    classify_calls: int = 0
    summary_calls: int = 0
    elapsed_seconds: float = 0.0
