from __future__ import annotations

import copy
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

import streamlit as st

WORKSPACE_PROJECTS_KEY = "workspace_projects"
WORKSPACE_SAVED_ANALYSES_KEY = "workspace_saved_analyses"


def _projects() -> dict[str, dict]:
    return dict(st.session_state.get(WORKSPACE_PROJECTS_KEY, {}))


def _save_projects(projects: dict[str, dict]) -> None:
    st.session_state[WORKSPACE_PROJECTS_KEY] = projects


def _saved_analyses() -> dict[str, dict]:
    return dict(st.session_state.get(WORKSPACE_SAVED_ANALYSES_KEY, {}))


def _save_analyses(records: dict[str, dict]) -> None:
    st.session_state[WORKSPACE_SAVED_ANALYSES_KEY] = records


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()


# --- projects -----------------------------------------------------------


def create_project(name: str, research_goal: str = "", notes: str = "") -> str | None:
    name = (name or "").strip()
    if not name:
        return None
    projects = _projects()
    project_id = uuid.uuid4().hex
    now = _now_iso()
    projects[project_id] = {
        "id": project_id,
        "name": name,
        "research_goal": research_goal or "",
        "notes": notes or "",
        "created_at": now,
        "updated_at": now,
    }
    _save_projects(projects)
    return project_id


def list_projects() -> list[dict[str, Any]]:
    projects = sorted(_projects().values(), key=lambda project: project["updated_at"], reverse=True)
    return copy.deepcopy(projects)


def get_project(project_id: str) -> dict[str, Any] | None:
    project = _projects().get(project_id)
    return copy.deepcopy(project) if project else None


def update_project(
    project_id: str,
    name: str | None = None,
    research_goal: str | None = None,
    notes: str | None = None,
) -> bool:
    projects = _projects()
    project = projects.get(project_id)
    if project is None:
        return False
    project = dict(project)
    if name is not None and name.strip():
        project["name"] = name.strip()
    if research_goal is not None:
        project["research_goal"] = research_goal
    if notes is not None:
        project["notes"] = notes
    project["updated_at"] = _now_iso()
    projects[project_id] = project
    _save_projects(projects)
    return True


def delete_project(project_id: str) -> bool:
    projects = _projects()
    projects.pop(project_id, None)
    _save_projects(projects)

    records = _saved_analyses()
    remaining = {rid: record for rid, record in records.items() if record["project_id"] != project_id}
    _save_analyses(remaining)
    return True


# --- saved analyses -------------------------------------------------------


def _dedup_key(project_id: str, payload: dict[str, Any]) -> str:
    parts = (
        project_id,
        _norm(payload.get("type")),
        _norm(payload.get("package_name")),
        _norm(payload.get("raw_input")),
        _norm(payload.get("scope") or payload.get("analysis_level")),
        _norm(payload.get("language")),
        _norm(payload.get("time_mode")),
        _norm(payload.get("start_date")),
        _norm(payload.get("end_date")),
        _norm(payload.get("review_count")),
        _norm(payload.get("analysis_timestamp") or payload.get("fetch_time")),
    )
    key = "|".join(parts)
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def _summary_fields(payload: dict[str, Any]) -> tuple[str, str, str, float | None, str | None, str | None]:
    report = payload.get("report") or {}
    game_name = str(payload.get("package_name") or "Unknown Game")
    package_name = str(payload.get("package_name") or "")
    if payload.get("type") == "single":
        market = str(payload.get("scope") or payload.get("country") or "")
    else:
        market = str(payload.get("analysis_level") or "")
    overall_score = report.get("overall_score")
    grade = report.get("grade")
    confidence = report.get("confidence_level") or report.get("confidence")
    return game_name, package_name, market, overall_score, grade, confidence


def save_analysis_to_project(project_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    if project_id not in _projects():
        return None

    records = _saved_analyses()
    dedup_key = _dedup_key(project_id, payload)
    existing_id = next(
        (rid for rid, record in records.items() if record["project_id"] == project_id and record["dedup_key"] == dedup_key),
        None,
    )
    game_name, package_name, market, overall_score, grade, confidence = _summary_fields(payload)
    now = _now_iso()
    record_id = existing_id or uuid.uuid4().hex
    records[record_id] = {
        "id": record_id,
        "project_id": project_id,
        "dedup_key": dedup_key,
        "analysis_type": str(payload.get("type") or ""),
        "game_name": game_name,
        "package_name": package_name,
        "market": market,
        "overall_score": overall_score,
        "grade": grade,
        "confidence": confidence,
        "created_at": now,
        "payload": copy.deepcopy(payload),
    }
    _save_analyses(records)

    projects = _projects()
    if project_id in projects:
        projects[project_id]["updated_at"] = now
        _save_projects(projects)

    return {"record_id": record_id, "created": existing_id is None}


def list_saved_analyses(project_id: str) -> list[dict[str, Any]]:
    records = [
        {key: value for key, value in record.items() if key != "payload"}
        for record in _saved_analyses().values()
        if record["project_id"] == project_id
    ]
    records.sort(key=lambda record: record["created_at"], reverse=True)
    return copy.deepcopy(records)


def get_saved_analysis(record_id: str) -> dict[str, Any] | None:
    record = _saved_analyses().get(record_id)
    if record is None:
        return None
    payload = copy.deepcopy(record["payload"])
    payload["record_id"] = record["id"]
    return payload


def delete_saved_analysis(record_id: str) -> bool:
    records = _saved_analyses()
    records.pop(record_id, None)
    _save_analyses(records)
    return True
