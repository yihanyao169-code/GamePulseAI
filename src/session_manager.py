from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
from typing import Any

import streamlit as st


ANALYSIS_STATE_KEY = "market_analysis_state"
PPT_STATE_KEY = "market_ppt_state"
SAVED_SINGLE_REPORTS_KEY = "saved_single_market_reports"
CURRENT_REPORT_KEY = "current_report"
CURRENT_ANALYSIS_RECORD_ID_KEY = "current_analysis_record_id"
GENERATED_EXPORTS_KEY = "generated_exports"


@dataclass(frozen=True)
class AnalysisSignature:
    mode: str
    raw_input: str
    language: str
    country: str
    selected_items: tuple[str, ...]
    analysis_level: str
    comment_source: str
    specified_language: str | None
    language_filter_mode: str
    keep_other_languages: bool
    review_count: int
    batch_size: int
    time_mode: str = ""
    start_date: str = ""
    end_date: str = ""

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "AnalysisSignature":
        return cls(
            mode=str(config.get("mode", "")),
            raw_input=str(config.get("raw_input", "")).strip(),
            language=str(config.get("language", "")),
            country=str(config.get("country", "")),
            selected_items=tuple(config.get("selected_items") or ()),
            analysis_level=str(config.get("analysis_level", "")),
            comment_source=str(config.get("comment_source", "")),
            specified_language=config.get("specified_language"),
            language_filter_mode=str(config.get("language_filter_mode", "")),
            keep_other_languages=bool(config.get("keep_other_languages", False)),
            review_count=int(config.get("review_count", 0)),
            batch_size=int(config.get("batch_size", 0)),
            time_mode=str(config.get("time_mode", "")),
            start_date=str(config.get("start_date", "")),
            end_date=str(config.get("end_date", "")),
        )


def save_analysis(payload: dict[str, Any], signature: AnalysisSignature) -> None:
    stored_payload = _with_record_metadata(payload) if payload.get("type") == "single" else copy.deepcopy(payload)
    st.session_state[ANALYSIS_STATE_KEY] = {"signature": signature, "payload": stored_payload}
    st.session_state[CURRENT_REPORT_KEY] = copy.deepcopy(stored_payload)
    if stored_payload.get("record_id"):
        st.session_state[CURRENT_ANALYSIS_RECORD_ID_KEY] = stored_payload["record_id"]
    st.session_state.pop(PPT_STATE_KEY, None)
    if stored_payload.get("type") == "single" and not stored_payload.get("summary_error"):
        save_single_report(stored_payload)


def save_single_report(payload: dict[str, Any]) -> None:
    saved = list(st.session_state.get(SAVED_SINGLE_REPORTS_KEY, []))
    record = _with_record_metadata(copy.deepcopy(payload))
    key = record["record_id"]
    saved = [item for item in saved if item.get("record_id") != key]
    saved.insert(0, record)
    st.session_state[SAVED_SINGLE_REPORTS_KEY] = saved[:5]


def get_single_reports() -> list[dict[str, Any]]:
    return copy.deepcopy(list(st.session_state.get(SAVED_SINGLE_REPORTS_KEY, [])))


def restore_analysis(payload: dict[str, Any]) -> None:
    restored = copy.deepcopy(payload)
    st.session_state[ANALYSIS_STATE_KEY] = {"signature": None, "payload": restored}
    st.session_state[CURRENT_REPORT_KEY] = copy.deepcopy(restored)
    if restored.get("record_id"):
        st.session_state[CURRENT_ANALYSIS_RECORD_ID_KEY] = restored["record_id"]
    st.session_state.pop(PPT_STATE_KEY, None)


def delete_single_report(record_id: str) -> None:
    saved = list(st.session_state.get(SAVED_SINGLE_REPORTS_KEY, []))
    st.session_state[SAVED_SINGLE_REPORTS_KEY] = [item for item in saved if item.get("record_id") != record_id]


def clear_single_reports() -> None:
    st.session_state[SAVED_SINGLE_REPORTS_KEY] = []


def get_analysis() -> dict[str, Any] | None:
    state = st.session_state.get(ANALYSIS_STATE_KEY)
    if state:
        return copy.deepcopy(state)
    current_report = st.session_state.get(CURRENT_REPORT_KEY)
    if current_report:
        return {"signature": None, "payload": copy.deepcopy(current_report)}
    return None


def clear_analysis() -> None:
    st.session_state.pop(ANALYSIS_STATE_KEY, None)
    st.session_state.pop(PPT_STATE_KEY, None)
    st.session_state.pop(CURRENT_REPORT_KEY, None)
    st.session_state.pop(CURRENT_ANALYSIS_RECORD_ID_KEY, None)


def has_current_analysis(signature: AnalysisSignature) -> bool:
    state = get_analysis()
    return bool(state and state.get("signature") == signature)


def config_changed(signature: AnalysisSignature) -> bool:
    state = get_analysis()
    return bool(state and state.get("signature") != signature)


def save_ppt(filename: str, data: bytes) -> None:
    st.session_state[PPT_STATE_KEY] = {"filename": filename, "data": data}


def get_ppt() -> dict[str, Any] | None:
    return st.session_state.get(PPT_STATE_KEY)


def save_export(record_id: str, export_type: str, filename: str, data: bytes) -> None:
    exports = dict(st.session_state.get(GENERATED_EXPORTS_KEY, {}))
    record_exports = dict(exports.get(record_id, {}))
    record_exports[export_type] = {"filename": filename, "data": data}
    exports[record_id] = record_exports
    st.session_state[GENERATED_EXPORTS_KEY] = exports


def get_export(record_id: str, export_type: str) -> dict[str, Any] | None:
    exports = st.session_state.get(GENERATED_EXPORTS_KEY, {})
    return exports.get(record_id, {}).get(export_type)


def _single_report_key(payload: dict[str, Any]) -> tuple:
    return (
        _normalized_key_part(payload.get("package_name")),
        _normalized_key_part(payload.get("raw_input")),
        _normalized_key_part(payload.get("country")),
        _normalized_key_part(payload.get("language")),
        _normalized_key_part(payload.get("time_mode")),
        _normalized_key_part(payload.get("start_date")),
        _normalized_key_part(payload.get("end_date")),
        int(payload.get("review_count") or 0),
    )


def _normalized_key_part(value: Any) -> str:
    return str(value or "").strip().casefold()


def _with_record_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    record = dict(payload)
    record_id = _record_id(record)
    prepared = record.get("prepared", {}) or {}
    report = record.get("report", {}) or {}
    record["record_id"] = record_id
    record["created_at"] = record.get("analysis_timestamp") or record.get("fetch_time") or ""
    record["metadata"] = {
        "record_id": record_id,
        "game_name": record.get("package_name", "Unknown Game"),
        "package_name": record.get("package_name", ""),
        "raw_input": record.get("raw_input", ""),
        "market": record.get("scope") or record.get("country", ""),
        "country": record.get("country", ""),
        "language": record.get("language", ""),
        "time_range": record.get("time_display") or record.get("time_mode", ""),
        "analysis_time": record.get("analysis_timestamp") or record.get("fetch_time", ""),
        "raw_fetched_count": prepared.get("raw_fetched_count", prepared.get("raw_count", 0)),
        "time_filtered_count": prepared.get("time_filtered_count", 0),
        "final_sample_count": prepared.get("language_filtered_count", 0),
        "overall_score": report.get("overall_score"),
        "grade": report.get("grade"),
        "confidence": report.get("confidence_level"),
    }
    return record


def _record_id(payload: dict[str, Any]) -> str:
    key = "|".join(str(item or "") for item in _single_report_key(payload))
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
