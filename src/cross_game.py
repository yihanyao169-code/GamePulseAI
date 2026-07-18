from __future__ import annotations

from collections import Counter
from typing import Any

from src.evaluation import build_single_market_report


def build_cross_game_rows(saved_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for payload in saved_reports:
        if payload.get("type") != "single":
            continue
        result = payload.get("result")
        reviews = list(getattr(result, "classified_reviews", []) or [])
        if not reviews:
            continue
        score = build_single_market_report(result, len(reviews))

        positive_count = sum(1 for review in reviews if _sentiment(review) == "正面")
        negative_count = sum(1 for review in reviews if _sentiment(review) == "负面")
        total = max(len(reviews), 1)
        top_risk = _top_risk_category(reviews)
        top_strength = _top_strength_tag(reviews)

        rows.append(
            {
                "Game": _game_label(payload),
                "Overall Score": _round1(score.get("overall_score", 0)),
                "Player Satisfaction": _round1(score.get("player_satisfaction", 0)),
                "Product Health": _round1(score.get("product_health", 0)),
                "Strength Bonus": _round1(score.get("strength_bonus", 0)),
                "Confidence": _round1(float(score.get("confidence_factor", 0)) * 100),
                "Positive %": _round1(positive_count / total * 100),
                "Negative %": _round1(negative_count / total * 100),
                "Top Risk": top_risk,
                "Top Strength": top_strength,
                "_radar": {
                    "Overall": _round1(score.get("overall_score", 0)),
                    "Health": _round1(score.get("product_health", 0)),
                    "Satisfaction": _round1(score.get("player_satisfaction", 0)),
                    "Strength": _round1(float(score.get("strength_bonus", 0)) * 20),
                    "Confidence": _round1(float(score.get("confidence_factor", 0)) * 100),
                },
            }
        )
    return rows


def build_cross_game_summary(rows: list[dict[str, Any]]) -> str:
    if len(rows) < 2:
        return "请选择至少两个已保存分析结果进行对比。"
    best_health = max(rows, key=lambda row: float(row.get("Product Health", 0)))
    best_overall = max(rows, key=lambda row: float(row.get("Overall Score", 0)))
    highest_negative = max(rows, key=lambda row: float(row.get("Negative %", 0)))
    return (
        f"{best_overall['Game']} 在本次已保存游戏中综合评分最高（{best_overall['Overall Score']:.1f}），"
        f"{best_health['Game']} 的产品健康度最高（{best_health['Product Health']:.1f}）；"
        f"{highest_negative['Game']} 负面占比最高（{highest_negative['Negative %']:.1f}%），"
        f"主要风险集中在{highest_negative['Top Risk']}。"
    )


def public_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not key.startswith("_")}


def _game_label(payload: dict[str, Any]) -> str:
    package_name = str(payload.get("package_name") or "Unknown Game")
    scope = str(payload.get("scope") or "")
    timestamp = str(payload.get("analysis_timestamp") or payload.get("fetch_time") or "")
    return " · ".join(part for part in [package_name, scope, timestamp] if part)


def _top_risk_category(reviews: list[Any]) -> str:
    risk_reviews = [review for review in reviews if _sentiment(review) == "负面"]
    counts = Counter(getattr(review, "category", "其他") for review in risk_reviews)
    return counts.most_common(1)[0][0] if counts else "暂无集中风险"


def _top_strength_tag(reviews: list[Any]) -> str:
    counts = Counter(
        tag
        for review in reviews
        if _sentiment(review) == "正面"
        for tag in (getattr(review, "strength_tags", ()) or ())
    )
    return counts.most_common(1)[0][0] if counts else "暂无明确优势"


def _sentiment(review: Any) -> str:
    mapping = {
        "positive": "正面",
        "neutral": "中性",
        "negative": "负面",
        "正面": "正面",
        "中性": "中性",
        "负面": "负面",
    }
    return mapping.get(str(getattr(review, "sentiment", "")).strip().lower(), str(getattr(review, "sentiment", "")))


def _round1(value: Any) -> float:
    try:
        return round(float(value), 1)
    except (TypeError, ValueError):
        return 0.0
