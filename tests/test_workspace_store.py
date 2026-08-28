from __future__ import annotations

from types import SimpleNamespace

from src import workspace_store
from src.models import AnalysisResult, ClassifiedReview


def _patch_state(monkeypatch):
    fake_st = SimpleNamespace(session_state={})
    monkeypatch.setattr(workspace_store, "st", fake_st)
    return fake_st.session_state


def _single_payload(package: str = "com.example.game", score: float = 70.0, timestamp: str = "2026-07-18 20:00") -> dict:
    result = AnalysisResult(
        classified_reviews=[
            ClassifiedReview(content="很好玩", category="游戏玩法", sentiment="positive", reason="上手快", strength_tags=("上手快",)),
            ClassifiedReview(content="有点卡", category="性能优化", sentiment="negative", reason="低端机卡顿"),
        ],
        category_counts={"游戏玩法": 1, "性能优化": 1},
        most_satisfied=["游戏玩法"],
        most_unsatisfied=["性能优化"],
        summary="总体评价积极。",
    )
    return {
        "type": "single",
        "package_name": package,
        "raw_input": package,
        "scope": "美国",
        "country": "us",
        "language": "en",
        "time_mode": "最近30天",
        "start_date": "2026-06-19",
        "end_date": "2026-07-18",
        "review_count": 100,
        "analysis_timestamp": timestamp,
        "prepared": {"raw_fetched_count": 200, "time_filtered_count": 120, "language_filtered_count": 98, "filtered_reviews": ()},
        "result": result,
        "report": {"overall_score": score, "grade": "B", "confidence_level": "数据基本充分，可作为辅助参考"},
    }


def _market_payload(package: str = "com.example.game") -> dict:
    return {
        "type": "market",
        "package_name": package,
        "analysis_level": "国家/地区对比",
        "rows": [{"市场": "美国", "综合评分": 70.0}],
        "market_results": [],
        "comparison_summary": "美国市场表现更好。",
    }


def test_create_list_get_project(monkeypatch) -> None:
    _patch_state(monkeypatch)
    project_id = workspace_store.create_project("原神竞品分析", research_goal="对比同类开放世界手游")

    assert project_id
    projects = workspace_store.list_projects()
    assert len(projects) == 1
    assert projects[0]["name"] == "原神竞品分析"

    fetched = workspace_store.get_project(project_id)
    assert fetched["research_goal"] == "对比同类开放世界手游"


def test_create_project_rejects_blank_name(monkeypatch) -> None:
    _patch_state(monkeypatch)
    assert workspace_store.create_project("   ") is None
    assert workspace_store.list_projects() == []


def test_update_project(monkeypatch) -> None:
    _patch_state(monkeypatch)
    project_id = workspace_store.create_project("项目A")

    assert workspace_store.update_project(project_id, notes="新增备注")
    fetched = workspace_store.get_project(project_id)
    assert fetched["notes"] == "新增备注"
    assert fetched["name"] == "项目A"


def test_update_missing_project_returns_false(monkeypatch) -> None:
    _patch_state(monkeypatch)
    assert workspace_store.update_project("does-not-exist", notes="x") is False


def test_save_and_read_single_analysis(monkeypatch) -> None:
    _patch_state(monkeypatch)
    project_id = workspace_store.create_project("项目A")
    payload = _single_payload()

    outcome = workspace_store.save_analysis_to_project(project_id, payload)
    assert outcome["created"] is True

    saved = workspace_store.list_saved_analyses(project_id)
    assert len(saved) == 1
    assert saved[0]["game_name"] == "com.example.game"
    assert saved[0]["overall_score"] == 70.0

    restored = workspace_store.get_saved_analysis(outcome["record_id"])
    assert restored["package_name"] == "com.example.game"
    assert isinstance(restored["result"], AnalysisResult)
    assert isinstance(restored["result"].classified_reviews[0], ClassifiedReview)
    assert restored["result"].classified_reviews[0].strength_tags == ("上手快",)
    assert restored["result"].category_counts == {"游戏玩法": 1, "性能优化": 1}


def test_save_market_analysis_roundtrip(monkeypatch) -> None:
    _patch_state(monkeypatch)
    project_id = workspace_store.create_project("项目A")
    payload = _market_payload()

    outcome = workspace_store.save_analysis_to_project(project_id, payload)
    assert outcome["created"] is True

    restored = workspace_store.get_saved_analysis(outcome["record_id"])
    assert restored["type"] == "market"
    assert restored["comparison_summary"] == "美国市场表现更好。"


def test_saving_identical_result_twice_updates_instead_of_duplicating(monkeypatch) -> None:
    _patch_state(monkeypatch)
    project_id = workspace_store.create_project("项目A")
    payload = _single_payload(score=70.0)

    first = workspace_store.save_analysis_to_project(project_id, payload)
    second = workspace_store.save_analysis_to_project(project_id, payload)

    assert first["created"] is True
    assert second["created"] is False
    assert first["record_id"] == second["record_id"]
    assert len(workspace_store.list_saved_analyses(project_id)) == 1


def test_distinct_analysis_runs_are_not_deduped(monkeypatch) -> None:
    _patch_state(monkeypatch)
    project_id = workspace_store.create_project("项目A")
    first_payload = _single_payload(score=70.0, timestamp="2026-07-18 20:00")
    second_payload = _single_payload(score=88.0, timestamp="2026-08-01 09:00")

    workspace_store.save_analysis_to_project(project_id, first_payload)
    workspace_store.save_analysis_to_project(project_id, second_payload)

    assert len(workspace_store.list_saved_analyses(project_id)) == 2


def test_save_to_missing_project_fails_without_crashing(monkeypatch) -> None:
    _patch_state(monkeypatch)
    result = workspace_store.save_analysis_to_project("does-not-exist", _single_payload())
    assert result is None


def test_delete_saved_analysis(monkeypatch) -> None:
    _patch_state(monkeypatch)
    project_id = workspace_store.create_project("项目A")
    outcome = workspace_store.save_analysis_to_project(project_id, _single_payload())

    assert workspace_store.delete_saved_analysis(outcome["record_id"])
    assert workspace_store.list_saved_analyses(project_id) == []


def test_delete_project_cascades_saved_analyses(monkeypatch) -> None:
    _patch_state(monkeypatch)
    project_id = workspace_store.create_project("项目A")
    outcome = workspace_store.save_analysis_to_project(project_id, _single_payload())

    assert workspace_store.delete_project(project_id)
    assert workspace_store.list_projects() == []
    assert workspace_store.get_saved_analysis(outcome["record_id"]) is None


def test_get_saved_analysis_missing_record_returns_none(monkeypatch) -> None:
    _patch_state(monkeypatch)
    assert workspace_store.get_saved_analysis("does-not-exist") is None
