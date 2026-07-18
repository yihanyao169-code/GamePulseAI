from __future__ import annotations

from src.market_config import MARKET_CONFIG, default_language
from src.models import AnalysisResult, ClassifiedReview


def _review(index: int, sentiment: str = "positive") -> ClassifiedReview:
    return ClassifiedReview(
        content=f"review {index}",
        category="整体评价",
        sentiment=sentiment,
        reason="ok",
        severity=None,
        is_blocking=False,
        strength_tags=(),
        review_id=index,
        schema_version="eval_v2_labels",
    )


def _result(count: int) -> AnalysisResult:
    reviews = [_review(index) for index in range(1, count + 1)]
    return AnalysisResult(
        classified_reviews=reviews,
        category_counts={"整体评价": count},
        most_satisfied=[],
        most_unsatisfied=[],
        summary="",
    )


def _prepared(count: int, filtered_records: tuple = ()) -> dict:
    return {
        "raw_count": count,
        "raw_fetched_count": count,
        "time_filtered_count": count,
        "cleaned_count": count,
        "language_filtered_count": count,
        "language_mismatch_count": 0,
        "filtered_reviews": filtered_records,
    }


def test_supported_markets_have_country_and_default_language() -> None:
    assert MARKET_CONFIG
    for country, config in MARKET_CONFIG.items():
        assert len(country) == 2
        assert config["label"]
        assert config["region"]
        assert config["default_language"]


def test_required_market_language_mappings() -> None:
    assert default_language("jp") == "ja"
    assert default_language("kr") == "ko"
    assert default_language("de") == "de"
    assert default_language("fr") == "fr"
    assert default_language("br") == "pt"
    assert default_language("vn") == "vi"


def test_classification_cache_key_is_isolated_by_country_and_language() -> None:
    import app

    records = (("1", "user", 5, "good", "2026-07-19"),)
    us = app._classification_cache_key("pkg", "us", "en", records, 25, "最近30天", "2026-06-20", "2026-07-19")
    jp = app._classification_cache_key("pkg", "jp", "ja", records, 25, "最近30天", "2026-06-20", "2026-07-19")
    jp_en = app._classification_cache_key("pkg", "jp", "en", records, 25, "最近30天", "2026-06-20", "2026-07-19")

    assert us != jp
    assert jp != jp_en


def test_fetch_cache_signature_contains_time_market_and_version_fields() -> None:
    import inspect
    import app

    params = inspect.signature(app._cached_fetch_prepare).parameters
    for name in [
        "package_name",
        "review_count",
        "request_lang",
        "country",
        "time_mode",
        "start_date",
        "end_date",
        "fetch_cache_version",
    ]:
        assert name in params


def test_zero_sample_market_does_not_call_evaluation(monkeypatch) -> None:
    import app

    def fail_evaluation(*args, **kwargs):
        raise AssertionError("Evaluation should not be called for unscorable markets")

    monkeypatch.setattr(app, "build_single_market_report", fail_evaluation)
    row = app._build_comparison_row(
        {
            "market_label": "日本",
            "language": "ja",
            "prepared": _prepared(0),
            "result": _result(0),
            "scoring_status": "no_reviews",
        }
    )

    assert row["Overall Score"] == "—"
    assert row["Grade"] == "N/A"
    assert row["评分状态"] == "无公开评论"


def test_insufficient_sample_market_does_not_call_evaluation(monkeypatch) -> None:
    import app

    def fail_evaluation(*args, **kwargs):
        raise AssertionError("Evaluation should not be called for insufficient samples")

    monkeypatch.setattr(app, "build_single_market_report", fail_evaluation)
    row = app._build_comparison_row(
        {
            "market_label": "韩国",
            "language": "ko",
            "prepared": _prepared(4),
            "result": _result(4),
            "scoring_status": "insufficient_sample",
        }
    )

    assert row["Overall Score"] == "—"
    assert row["Grade"] == "N/A"
    assert row["评分状态"] == "样本不足"


def test_valid_rows_exclude_unscorable_markets() -> None:
    import app

    rows = [
        {"市场": "美国", "Overall Score": "76.5"},
        {"市场": "日本", "Overall Score": "—"},
        {"市场": "韩国", "Overall Score": "需重新分析"},
    ]

    assert app._valid_comparison_rows(rows) == [{"市场": "美国", "Overall Score": "76.5"}]


def test_cross_market_loop_uses_each_country_and_local_language(monkeypatch) -> None:
    import app

    calls = []

    def fake_prepare(package_name, review_count, request_lang, country, filter_lang, language_filter_mode, *args):
        calls.append((country, request_lang, filter_lang, language_filter_mode))
        records = tuple((str(index), "user", 5, f"content {index}", "2026-07-19") for index in range(1, 11))
        return _prepared(10, records)

    def fake_classify(package_name, country, language, review_records, batch_size, *args):
        return _result(len(review_records))

    monkeypatch.setattr(app, "_cached_fetch_prepare", fake_prepare)
    monkeypatch.setattr(app, "_classify_reviews_with_cache", fake_classify)

    app._run_country_analysis("pkg", "jp", "东亚", "当地玩家评论（推荐）", None, False, 10, 25, "最近30天", "", "")
    app._run_country_analysis("pkg", "kr", "东亚", "当地玩家评论（推荐）", None, False, 10, 25, "最近30天", "", "")

    assert calls[0][:3] == ("jp", "ja", "ja")
    assert calls[1][:3] == ("kr", "ko", "ko")


def test_uniform_language_uses_same_lang_for_each_market(monkeypatch) -> None:
    import app

    calls = []

    def fake_prepare(package_name, review_count, request_lang, country, filter_lang, language_filter_mode, *args):
        calls.append((country, request_lang, filter_lang))
        records = tuple((str(index), "user", 5, f"content {index}", "2026-07-19") for index in range(1, 11))
        return _prepared(10, records)

    monkeypatch.setattr(app, "_cached_fetch_prepare", fake_prepare)
    monkeypatch.setattr(app, "_classify_reviews_with_cache", lambda *args, **kwargs: _result(10))

    app._run_country_analysis("pkg", "jp", "东亚", "指定语言评论（高级）", "en", False, 10, 25, "最近30天", "", "")
    app._run_country_analysis("pkg", "kr", "东亚", "指定语言评论（高级）", "en", False, 10, 25, "最近30天", "", "")

    assert calls == [("jp", "en", "en"), ("kr", "en", "en")]
