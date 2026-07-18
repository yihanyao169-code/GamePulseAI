from __future__ import annotations

from types import SimpleNamespace

from src import session_manager


def _payload(package: str, country: str = "us", language: str = "en", score: float = 70.0) -> dict:
    return {
        "type": "single",
        "package_name": package,
        "raw_input": package,
        "scope": country,
        "country": country,
        "language": language,
        "time_mode": "最近30天",
        "time_display": "最近30天",
        "review_count": 100,
        "analysis_timestamp": f"2026-07-18 20:{int(score):02d}",
        "prepared": {
            "raw_fetched_count": 200,
            "time_filtered_count": 120,
            "language_filtered_count": 98,
        },
        "report": {
            "overall_score": score,
            "grade": "B",
            "confidence_level": "数据基本充分，可作为辅助参考",
        },
    }


def _patch_state(monkeypatch):
    fake_st = SimpleNamespace(session_state={})
    monkeypatch.setattr(session_manager, "st", fake_st)
    return fake_st.session_state


def test_analysis_history_keeps_latest_five(monkeypatch) -> None:
    _patch_state(monkeypatch)
    for index in range(6):
        session_manager.save_single_report(_payload(f"pkg.{index}", score=60 + index))

    records = session_manager.get_single_reports()
    assert len(records) == 5
    assert records[0]["package_name"] == "pkg.5"
    assert records[-1]["package_name"] == "pkg.1"


def test_same_parameters_replace_existing_record(monkeypatch) -> None:
    _patch_state(monkeypatch)
    session_manager.save_single_report(_payload("pkg.same", score=60))
    session_manager.save_single_report(_payload("pkg.same", score=88))

    records = session_manager.get_single_reports()
    assert len(records) == 1
    assert records[0]["report"]["overall_score"] == 88


def test_consecutive_game_analyses_keep_both_history_records(monkeypatch) -> None:
    _patch_state(monkeypatch)
    signature = session_manager.AnalysisSignature.from_config({})

    session_manager.save_analysis(_payload("pkg.first", score=71), signature)
    session_manager.clear_analysis()
    session_manager.save_analysis(_payload("pkg.second", score=82), signature)

    records = session_manager.get_single_reports()
    assert [record["package_name"] for record in records] == ["pkg.second", "pkg.first"]
    assert records[0]["record_id"] != records[1]["record_id"]


def test_distinct_raw_game_inputs_do_not_dedupe_when_package_identity_is_missing(monkeypatch) -> None:
    _patch_state(monkeypatch)
    first = _payload("")
    first["raw_input"] = "https://play.google.com/store/apps/details?id=pkg.first"
    second = _payload("")
    second["raw_input"] = "https://play.google.com/store/apps/details?id=pkg.second"

    session_manager.save_single_report(first)
    session_manager.save_single_report(second)

    records = session_manager.get_single_reports()
    assert len(records) == 2
    assert records[0]["record_id"] != records[1]["record_id"]


def test_delete_and_clear_history(monkeypatch) -> None:
    _patch_state(monkeypatch)
    session_manager.save_single_report(_payload("pkg.a"))
    session_manager.save_single_report(_payload("pkg.b"))
    record_id = session_manager.get_single_reports()[0]["record_id"]

    session_manager.delete_single_report(record_id)
    assert len(session_manager.get_single_reports()) == 1

    session_manager.clear_single_reports()
    assert session_manager.get_single_reports() == []


def test_restore_analysis_does_not_clear_history(monkeypatch) -> None:
    state = _patch_state(monkeypatch)
    payload = _payload("pkg.restore")
    session_manager.save_single_report(payload)
    record = session_manager.get_single_reports()[0]

    session_manager.restore_analysis(record)

    assert state[session_manager.ANALYSIS_STATE_KEY]["payload"]["package_name"] == "pkg.restore"
    assert state[session_manager.CURRENT_REPORT_KEY]["package_name"] == "pkg.restore"
    assert state[session_manager.CURRENT_ANALYSIS_RECORD_ID_KEY] == record["record_id"]
    assert len(session_manager.get_single_reports()) == 1


def test_saved_history_is_deep_copied(monkeypatch) -> None:
    _patch_state(monkeypatch)
    payload = _payload("pkg.copy", score=70)
    session_manager.save_single_report(payload)
    payload["prepared"]["language_filtered_count"] = 1
    payload["report"]["overall_score"] = 1

    record = session_manager.get_single_reports()[0]

    assert record["prepared"]["language_filtered_count"] == 98
    assert record["report"]["overall_score"] == 70


def test_save_analysis_immediately_persists_current_report_and_history(monkeypatch) -> None:
    state = _patch_state(monkeypatch)
    payload = _payload("pkg.persist", score=81.1)
    signature = session_manager.AnalysisSignature.from_config(
        {
            "mode": "单市场分析",
            "raw_input": "pkg.persist",
            "language": "en",
            "country": "us",
            "selected_items": ["us"],
            "analysis_level": "国家/地区对比",
            "comment_source": "指定语言评论（高级）",
            "specified_language": "en",
            "language_filter_mode": "strict",
            "keep_other_languages": False,
            "review_count": 100,
            "batch_size": 25,
            "time_mode": "最近30天",
            "start_date": "",
            "end_date": "",
        }
    )

    session_manager.save_analysis(payload, signature)

    assert state[session_manager.CURRENT_REPORT_KEY]["package_name"] == "pkg.persist"
    assert state[session_manager.CURRENT_ANALYSIS_RECORD_ID_KEY] == state[session_manager.CURRENT_REPORT_KEY]["record_id"]
    assert len(session_manager.get_single_reports()) == 1


def test_export_state_survives_rerun_and_does_not_mutate_current_report(monkeypatch) -> None:
    state = _patch_state(monkeypatch)
    payload = _payload("pkg.export", score=75)
    session_manager.save_single_report(payload)
    record = session_manager.get_single_reports()[0]
    session_manager.restore_analysis(record)
    record_id = record["record_id"]

    export_copy = session_manager.get_analysis()["payload"]
    export_copy["report"]["overall_score"] = 1
    session_manager.save_export(record_id, "pptx", "report.pptx", b"ppt")

    assert session_manager.get_analysis()["payload"]["report"]["overall_score"] == 75
    assert session_manager.get_export(record_id, "pptx")["data"] == b"ppt"


def test_clear_analysis_does_not_clear_saved_history_or_generated_exports(monkeypatch) -> None:
    state = _patch_state(monkeypatch)
    payload = _payload("pkg.keep")
    session_manager.save_single_report(payload)
    record = session_manager.get_single_reports()[0]
    session_manager.restore_analysis(record)
    session_manager.save_export(record["record_id"], "pptx", "report.pptx", b"ppt")

    session_manager.clear_analysis()

    assert session_manager.get_single_reports()[0]["package_name"] == "pkg.keep"
    assert session_manager.get_export(record["record_id"], "pptx")["data"] == b"ppt"
    assert session_manager.CURRENT_REPORT_KEY not in state
