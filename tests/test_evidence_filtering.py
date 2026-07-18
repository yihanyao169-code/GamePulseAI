from __future__ import annotations

from src.evaluation import build_game_evidence
from src.models import AnalysisResult, ClassifiedReview


def _result(contents: list[str]) -> AnalysisResult:
    reviews = [
        ClassifiedReview(content, "BUG", "negative", "", "S2", False, (), review_id=index, schema_version="eval_v2_labels")
        for index, content in enumerate(contents, start=1)
    ]
    return AnalysisResult(reviews, {"BUG": len(reviews)}, [], [], "")


def _terms(evidence: dict) -> set[str]:
    output = {row["term"] for row in evidence.get("top_terms", [])}
    for rows in evidence.get("by_category", {}).values():
        output.update(row["term"] for row in rows)
    return {str(item).lower() for item in output}


def test_invalid_evidence_terms_are_filtered() -> None:
    evidence = build_game_evidence(
        _result([
            "The game is good. They said It's fine. I've played on Google Play.",
            "Arknights by YOSTAR PLEASE MAKE this better.",
        ]),
        excluded_terms=["Arknights", "YOSTAR", "Google Play"],
    )

    terms = _terms(evidence)
    assert "the" not in terms
    assert "they" not in terms
    assert "it's" not in terms
    assert "i've" not in terms
    assert "google play" not in terms
    assert "arknights" not in terms
    assert "yostar" not in terms


def test_meaningful_evidence_phrases_are_kept() -> None:
    evidence = build_game_evidence(
        _result([
            "login failure caused account lost and connection error",
            "frame drops and low gacha rates are the biggest issue",
        ])
    )

    terms = _terms(evidence)
    assert "login failure" in terms
    assert "account lost" in terms
    assert "frame drops" in terms
    assert "low gacha rates" in terms
