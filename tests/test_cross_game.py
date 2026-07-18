from __future__ import annotations

from src.cross_game import build_cross_game_rows, build_cross_game_summary, public_row
from src.models import AnalysisResult, ClassifiedReview


def _payload(name: str, overall: float, health: float, satisfaction: float, bonus: float, confidence: float) -> dict:
    reviews = [
        ClassifiedReview("great combat", "游戏玩法", "positive", "", None, False, ("核心玩法",)),
        ClassifiedReview("bad gacha", "氪金", "negative", "", "S2", False, ()),
    ]
    return {
        "type": "single",
        "package_name": name,
        "scope": "美国",
        "analysis_timestamp": "2026-07-18 12:00:00",
        "result": AnalysisResult(reviews, {"游戏玩法": 1, "氪金": 1}, [], [], ""),
        "report": {
            "score": {
                "overall_score": overall,
                "product_health": health,
                "player_satisfaction": satisfaction,
                "strength_bonus": bonus,
                "confidence_factor": confidence,
            }
        },
    }


def test_cross_game_reads_multiple_saved_reports() -> None:
    rows = build_cross_game_rows([
        _payload("Arknights", 82.2, 74.0, 88.0, 3.0, 0.91),
        _payload("Endfield", 79.4, 86.0, 77.0, 2.0, 0.88),
    ])
    assert len(rows) == 2
    assert rows[0]["Overall Score"] > 0
    assert rows[1]["Product Health"] > 0
    assert rows[0]["Top Risk"] == "氪金"
    assert rows[0]["Top Strength"] == "核心玩法"


def test_cross_game_public_row_removes_chart_metadata() -> None:
    row = build_cross_game_rows([_payload("Arknights", 82.2, 74.0, 88.0, 3.0, 0.91)])[0]
    assert "_radar" in row
    assert "_radar" not in public_row(row)


def test_cross_game_generates_python_summary_without_claude() -> None:
    rows = build_cross_game_rows([
        _payload("Arknights", 82.2, 74.0, 88.0, 3.0, 0.91),
        _payload("Endfield", 79.4, 86.0, 77.0, 2.0, 0.88),
    ])
    summary = build_cross_game_summary(rows)
    assert "Arknights" in summary or "Endfield" in summary
    assert "产品健康度最高" in summary
