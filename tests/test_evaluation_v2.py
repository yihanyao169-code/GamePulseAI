from __future__ import annotations

import time

import src.evaluation as evaluation
from src.evaluation import build_category_sentiment_table, build_evaluation_score, build_single_market_report
from src.models import AnalysisResult, ClassifiedReview, REVIEW_CATEGORIES


def _result(reviews: list[ClassifiedReview]) -> AnalysisResult:
    counts = {category: 0 for category in REVIEW_CATEGORIES}
    for review in reviews:
        counts[review.category] = counts.get(review.category, 0) + 1
    return AnalysisResult(reviews, counts, [], [], "")


def _positive(content: str = "combat is fun", tags: tuple[str, ...] = ("核心玩法",)) -> ClassifiedReview:
    return ClassifiedReview(content, "游戏玩法", "正面", "positive evidence", None, False, tags)


def _neutral(content: str = "average") -> ClassifiedReview:
    return ClassifiedReview(content, "整体评价", "中性", "neutral", None, False, ())


def _risk(severity: str, blocking: bool = False, category: str = "BUG") -> ClassifiedReview:
    return ClassifiedReview(f"{severity} issue", category, "负面", "risk evidence", severity, blocking, ())


def test_evaluation_v2_is_deterministic() -> None:
    result = _result([_positive(), _positive("art is great", ("美术表现",)), _neutral(), _risk("S2")])
    first = build_evaluation_score(result, 4)
    second = build_evaluation_score(result, 4)
    assert first == second


def test_strength_bonus_is_capped_at_five() -> None:
    reviews = [_positive(f"specific positive {index}", ("核心玩法", "美术表现", "角色设计")) for index in range(80)]
    score = build_evaluation_score(_result(reviews), len(reviews))
    assert score["strength_bonus"] <= 5.0


def test_confidence_factor_and_overall_are_bounded() -> None:
    score = build_evaluation_score(_result([_positive(), _neutral(), _risk("S1")]), 3)
    assert 0.70 <= score["confidence_factor"] <= 1.0
    assert 0 <= score["overall_score"] <= 100


def test_s4_significantly_reduces_product_health() -> None:
    mostly_positive = _result([_positive() for _ in range(19)] + [_risk("S1")])
    with_blocking = _result([_positive() for _ in range(19)] + [_risk("S4", blocking=True)])
    healthy = build_evaluation_score(mostly_positive, 20)
    blocked = build_evaluation_score(with_blocking, 20)
    assert blocked["product_health"] < healthy["product_health"]
    assert blocked["blocking_penalty"] >= 0


def test_s4_ratio_uses_continuous_penalty() -> None:
    reviews = [_positive() for _ in range(18)] + [_risk("S4", True), _risk("S4", True)]
    score = build_evaluation_score(_result(reviews), len(reviews))
    assert score["s4_blocking_ratio"] > 0.05
    assert score["blocking_penalty"] == 15.0


def test_s4_ratio_around_four_percent_has_continuous_penalty() -> None:
    reviews = [_positive() for _ in range(23)] + [_risk("S4", False)]
    score = build_evaluation_score(_result(reviews), len(reviews))
    assert score["s4_ratio"] == 0.042
    assert score["blocking_penalty"] == 8.3


def test_low_confidence_discounts_final_score() -> None:
    result = _result([_positive(), _positive(), _positive()])
    score = build_evaluation_score(result, 3)
    assert 0.70 <= score["confidence_factor"] < 1.0
    assert score["overall_score"] < score["base_score"]


def test_base_score_72_with_confidence_070_becomes_50_4(monkeypatch) -> None:
    result = _result([_positive()])
    monkeypatch.setattr(evaluation, "_player_satisfaction", lambda _sentiments: 80.0)
    monkeypatch.setattr(
        evaluation,
        "_product_health",
        lambda _result: {
            "product_health": 60.0,
            "severity_distribution": {"S1": 0, "S2": 0, "S3": 0, "S4": 0},
            "raw_risk": 0,
            "risk_ratio": 0.0,
            "risk_penalty": 0.0,
            "blocking_penalty": 0.0,
            "s4_blocking_ratio": 0.0,
            "s4_ratio": 0.0,
            "s4_penalty": 0.0,
            "blocking_count": 0,
        },
    )
    monkeypatch.setattr(
        evaluation,
        "_strength_bonus",
        lambda _result: {
            "strength_bonus": 1.0,
            "strength_sources": [],
            "strength_breakdown": {"coverage": 0.0, "diversity": 0.0, "evidence": 0.0},
        },
    )
    monkeypatch.setattr(
        evaluation,
        "_confidence_factor",
        lambda _result, _sample_size: {
            "confidence_factor": 0.70,
            "confidence_level": "Very Low / 很低",
            "confidence_reason": "test",
            "confidence_breakdown": {"sample_factor": 0.0, "success_factor": 1.0, "specificity_factor": 1.0, "generic_review_ratio": 0.0},
        },
    )

    score = build_evaluation_score(result, 1)

    assert score["base_score"] == 72.0
    assert score["overall_score"] == 50.4


def test_confidence_changes_overall_score() -> None:
    result = _result([_positive(), _positive(), _positive()])
    low_confidence = build_evaluation_score(result, 100)
    higher_confidence = build_evaluation_score(result, 3)

    assert low_confidence["confidence_factor"] != higher_confidence["confidence_factor"]
    assert low_confidence["overall_score"] != higher_confidence["overall_score"]


def test_no_risk_category_keeps_health_high() -> None:
    score = build_evaluation_score(_result([_positive(), _positive("visual", ("美术表现",)), _neutral()]), 3)
    assert score["product_health"] == 100.0


def test_no_strength_signal_has_zero_bonus() -> None:
    score = build_evaluation_score(_result([ClassifiedReview("good game", "整体评价", "正面", "generic", None, False, ())]), 1)
    assert score["strength_bonus"] == 0.0


def test_strength_bonus_is_not_fixed_five() -> None:
    reviews = [_positive("combat has depth", ("核心玩法",)) for _ in range(10)] + [_neutral() for _ in range(90)]
    score = build_evaluation_score(_result(reviews), len(reviews))
    assert 0 < score["strength_bonus"] < 5.0


def test_generic_ratio_reduces_confidence() -> None:
    specific = _result([_positive("combat depth", ("核心玩法",)) for _ in range(50)] + [_risk("S1", category="BUG") for _ in range(50)])
    generic = _result([ClassifiedReview("okay", "整体评价", "中性", "", None, False, ()) for _ in range(70)] + [_positive("combat depth", ("核心玩法",)) for _ in range(30)])
    assert build_evaluation_score(generic, 100)["confidence_factor"] < build_evaluation_score(specific, 100)["confidence_factor"]


def test_category_sentiment_table_totals_match_review_count() -> None:
    reviews = [_positive(), _neutral(), _risk("S2", category="氪金"), _risk("S1", category="氪金")]
    table = build_category_sentiment_table(_result(reviews))
    assert sum(int(row["合计"]) for row in table) == len(reviews)
    monetization = next(row for row in table if row["类别"] == "氪金")
    assert monetization["负面"] == 2


def test_negative_focus_is_supported_by_cross_table() -> None:
    reviews = [_risk("S1", category="氪金") for _ in range(3)] + [_risk("S1", category="BUG")]
    report = build_single_market_report(_result(reviews), len(reviews))
    assert report["top_negative_categories"][0]["类别"] == "氪金"
    assert "氪金" in report["sentiment_conclusion"]


def test_recommendation_impacts_are_category_specific() -> None:
    reviews = [_risk("S2", category="氪金"), _risk("S3", category="BUG", blocking=True), _risk("S1", category="UI体验")]
    report = build_single_market_report(_result(reviews), len(reviews))
    impacts = [item["impact"] for items in report["recommendations"].values() for item in items]
    assert any("付费信任" in impact for impact in impacts)
    assert any("核心流程中断" in impact for impact in impacts)


def test_local_evaluation_for_100_reviews_is_fast() -> None:
    reviews = [_positive(f"specific combat {index}", ("核心玩法",)) for index in range(60)] + [_risk("S1", category="UI体验") for _ in range(40)]
    result = _result(reviews)
    started = time.perf_counter()
    build_single_market_report(result, len(reviews))
    elapsed_ms = (time.perf_counter() - started) * 1000
    assert elapsed_ms < 100


def test_report_prefers_specific_game_evidence() -> None:
    reviews = [
        ClassifiedReview("Silvy Live2D and voice acting are amazing", "美术", "positive", "", None, False, ("角色设计",)),
        ClassifiedReview("SSR pity and duplicate compensation feel unfair", "氪金", "negative", "", "S2", False, ()),
        ClassifiedReview("login crash caused 390 hours save loss", "BUG", "negative", "", "S4", True, ()),
    ]
    report = build_single_market_report(_result(reviews), len(reviews))
    combined = " ".join(
        [report["overall_summary"], report["score_reason"], report["evaluation_summary"]]
        + [item["detail"] for item in report["strengths"]]
        + [item["detail"] for item in report["pain_points"]]
        + [item["basis"] for items in report["recommendations"].values() for item in items]
    )
    assert "Silvy" in combined
    assert "SSR" in combined or "390 hours" in combined


def test_same_report_payload_renders_deterministic_scores() -> None:
    reviews = [_positive("combat depth", ("核心玩法",)), _neutral(), _risk("S2", category="BUG")]
    result = _result(reviews)
    first = build_single_market_report(result, len(reviews))
    second = build_single_market_report(result, len(reviews))
    fields = ["player_satisfaction", "product_health", "strength_bonus", "base_score", "confidence_factor", "overall_score", "grade"]
    assert {field: first[field] for field in fields} == {field: second[field] for field in fields}


def test_evidence_filtering_does_not_change_evaluation_score() -> None:
    reviews = [
        ClassifiedReview("The login failure happened in Arknights", "BUG", "negative", "", "S3", False, (), review_id=1, schema_version="eval_v2_labels"),
        ClassifiedReview("great combat depth", "游戏玩法", "positive", "", None, False, ("核心玩法",), review_id=2, schema_version="eval_v2_labels"),
    ]
    result = _result(reviews)
    base = build_single_market_report(result, len(reviews))
    filtered = build_single_market_report(result, len(reviews), excluded_evidence_terms=["Arknights", "The"])
    fields = ["player_satisfaction", "product_health", "strength_bonus", "base_score", "confidence_factor", "overall_score"]
    assert {field: base[field] for field in fields} == {field: filtered[field] for field in fields}


def test_legacy_report_without_v2_fields_is_not_faked() -> None:
    class LegacyReview:
        content = "crash"
        category = "BUG"
        sentiment = "负面"
        reason = "old"

    result = AnalysisResult([LegacyReview()], {"BUG": 1}, [], [], "")  # type: ignore[list-item]
    score = build_evaluation_score(result, 1)
    assert score["evaluation_available"] is False
    assert "需重新运行分析" in score["score_reason"]


def test_new_schema_with_english_sentiment_and_null_severity_evaluates() -> None:
    reviews = [
        ClassifiedReview("great combat", "游戏玩法", "positive", "", None, False, ("核心玩法",), review_id=1, schema_version="eval_v2_labels"),
        ClassifiedReview("nice art", "美术", "positive", "", None, False, ("美术表现",), review_id=2, schema_version="eval_v2_labels"),
        ClassifiedReview("bug but playable", "BUG", "negative", "", None, False, (), review_id=3, schema_version="eval_v2_labels"),
    ]
    result = _result(reviews)
    score = build_evaluation_score(result, len(reviews))
    assert score["evaluation_available"] is True
    assert score["overall_score"] > 0
