from __future__ import annotations

import tempfile
import time
import copy
import html
import hashlib
import json
import os
import re
from collections import Counter
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from src.analyzer import (
    CLASSIFICATION_PROMPT_VERSION,
    CLASSIFICATION_SCHEMA_VERSION,
    classify_reviews,
    summarize_market_comparison,
    summarize_single_market_report,
)
from src.charts import (
    create_bar_chart,
    create_market_bar_chart,
    create_market_category_distribution_chart,
    create_pie_chart,
)
from src.cleaning import clean_reviews
from src.claude_client import ClaudeClient
from src.cross_game import build_cross_game_rows, build_cross_game_summary, public_row
from src.google_play import FETCH_CACHE_VERSION, extract_package_name, fetch_reviews_with_meta
from src.language_filter import filter_reviews_by_language
from src.market_config import MARKET_CONFIG, REGION_MARKETS, default_language as market_default_language, market_label, market_region
from src.models import AnalysisResult, DEFAULT_COUNTRY, DEFAULT_LANGUAGE, DEFAULT_REVIEW_COUNT, REVIEW_CATEGORIES, ReviewItem
from src.evaluation import (
    FRAMEWORK_NAME,
    FRAMEWORK_VERSION,
    GRADE_SCALE,
    HEALTH_RISK_NORMALIZATION_FACTOR,
    HEALTH_WEIGHT,
    SATISFACTION_WEIGHT,
    SEVERITY_WEIGHTS,
    STRENGTH_BONUS_MAX,
    build_single_market_report,
)
from src.methodology import (
    category_standards,
    cleaning_steps,
    evaluation_limitations,
    score_formula_text,
    sentiment_standards,
    severity_standards,
)
from src.representative_reviews import select_representative_reviews
from src.ppt_exporter import export_market_comparison_ppt, export_ppt
from src import progress_ui
from src.reporting import sort_category_counts
from src import session_manager
from src import theme
from src import time_scope as time_scope_utils
from src import ui_components as ui


load_dotenv()

st.set_page_config(page_title="GamePulse AI", layout="wide")

DEBUG_MODE = os.getenv("DEBUG_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}


@st.cache_data(show_spinner=False)
def _get_evaluation_framework_pdf_bytes() -> bytes:
    return (Path(__file__).parent / "docs" / "GamePulse_AI_Evaluation_Framework_v2.0.pdf").read_bytes()


PDF_FILENAME = "GamePulse_AI_Evaluation_Framework_v2.0.pdf"

LANGUAGE_OPTIONS = {
    "all": "不限制语言（推荐）",
    "zh": "简体中文",
    "en": "English",
    "ja": "日本語",
    "ko": "한국어",
    "fr": "Français",
    "de": "Deutsch",
    "es": "Español",
    "pt": "Português",
}

UNRESTRICTED_LANGUAGE = "all"
LANGUAGE_FILTER_STRICT = "strict"
LANGUAGE_FILTER_NONE = "none"

COUNTRY_GROUPS = REGION_MARKETS
COUNTRY_OPTIONS = {
    code: {"name": config["label"], "region": config["region"]}
    for code, config in MARKET_CONFIG.items()
}
LOCAL_LANGUAGE_BY_COUNTRY = {code: config["default_language"] for code, config in MARKET_CONFIG.items()}

MIN_SCORABLE_REVIEWS = 10

ANALYSIS_RUNNING_KEY = "analysis_running"


def main() -> None:
    theme_choice = st.session_state.get("theme_choice", "跟随系统")
    ui.inject_theme_css(theme_choice)
    if not _ensure_authenticated():
        return
    config = _render_sidebar_config()
    st.session_state["theme_mode"] = config["theme_mode"]
    if config.get("analyze_button"):
        st.session_state[ANALYSIS_RUNNING_KEY] = True

    methodology_slot = st.empty()
    with methodology_slot.container():
        _render_methodology_entry()
    ui.product_header()
    if config["page"] == "首页":
        _render_homepage()
        return
    if config["page"] == "跨游戏对比（Beta）":
        _render_cross_game_beta_page(config)
        return
    if config["page"] == "分析记录":
        _render_analysis_history_page(config)
        return

    signature = session_manager.AnalysisSignature.from_config(config)

    if not config["analyze_button"]:
        saved = session_manager.get_analysis()
        expected_type = "single" if config["mode"] == "单市场分析" else "market"
        if saved and saved.get("payload", {}).get("type") == expected_type:
            saved_payload = dict(saved["payload"])
            saved_payload["from_session_state"] = True
            if session_manager.config_changed(signature):
                st.warning("配置已变化。当前仍显示上一次已完成报告；如需使用新配置，请点击开始分析。")
            _render_saved_analysis(saved_payload, config, show_progress=True, show_context=True)
        else:
            if session_manager.config_changed(signature):
                st.warning("配置已变化，请重新分析以生成当前包名、地区、语言和评论数量对应的报告。")
            _render_homepage()
        return

    if config["mode"] == "单市场分析":
        session_manager.clear_analysis()
        _render_analysis_running_anchor()
        try:
            _render_single_market_page(config)
        finally:
            st.session_state[ANALYSIS_RUNNING_KEY] = False
            methodology_slot.empty()
            with methodology_slot.container():
                _render_methodology_entry()
    else:
        session_manager.clear_analysis()
        _render_analysis_running_anchor()
        try:
            _render_market_comparison_page(config)
        finally:
            st.session_state[ANALYSIS_RUNNING_KEY] = False
            methodology_slot.empty()
            with methodology_slot.container():
                _render_methodology_entry()


def _render_homepage() -> None:
    features = [
        ("评论来源接入", "抓取 Google Play 评论，并预留 Steam、App Store、TapTap 扩展。"),
        ("AI 语义分析", "完成分类、情感识别、中文概括及高频问题聚合。"),
        ("跨市场洞察", "比较国家与区域玩家反馈，识别本地化差异。"),
        ("区域市场分析", "按代表国家等量采样，避免单一市场主导结论。"),
        ("AI 洞察总结", "输出共同优点、主要问题、商业化风险和运营建议。"),
        ("专业报告导出", "生成可直接汇报的 PPT，并预留更多导出格式。"),
    ]
    ui.section_label("CORE CAPABILITY MATRIX")
    ui.feature_grid(features)

    ui.section_label("ANALYSIS PIPELINE")
    _render_process_flow(-1)


def _render_cross_game_beta_page(config: dict) -> None:
    st.markdown("<div id='cross-game-beta'></div>", unsafe_allow_html=True)
    st.subheader("跨游戏对比（Beta）")
    st.info("当前版本仅支持比较本次会话中已完成分析的游戏，后续将支持实时多游戏分析。")

    saved_reports = session_manager.get_single_reports()
    if not saved_reports:
        st.warning("暂无已保存分析。请先完成至少两个单市场分析。")
        return

    option_indexes = list(range(len(saved_reports)))
    selected_indexes = st.multiselect(
        "已保存分析",
        options=option_indexes,
        default=option_indexes[-min(2, len(option_indexes)):],
        format_func=lambda index: _saved_report_label(saved_reports[index]),
        help="最多选择 4 个本次会话中已完成的单市场分析结果。",
    )
    if len(selected_indexes) > 4:
        st.warning("跨游戏对比（Beta）最多选择 4 个已保存分析。")
        return
    if len(selected_indexes) < 2:
        st.warning("请选择至少 2 个已保存分析。")
        return

    if not st.button("生成对比", type="primary"):
        return

    selected_payloads = [saved_reports[index] for index in selected_indexes]
    rows = build_cross_game_rows(selected_payloads)
    if len(rows) < 2:
        st.warning("所选结果缺少可比较的综合评分数据。")
        return

    st.markdown("#### 对比指标")
    st.dataframe(
        pd.DataFrame([_localize_cross_game_row(public_row(row)) for row in rows]),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("#### 雷达图")
    fig = _create_cross_game_radar_chart(rows, config.get("theme_mode", "light"))
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

    st.markdown("#### 自动总结")
    _render_text_panel(build_cross_game_summary(rows))


def _render_analysis_history_page(config: dict) -> None:
    st.subheader("分析记录")
    records = session_manager.get_single_reports()
    if not records:
        st.info("暂无分析记录。完成一次单市场分析后，报告会自动保存在这里。")
        return

    st.caption("最近 5 条单市场分析记录保存在当前浏览器会话中，不写入服务器数据库。")
    if st.checkbox("确认清空全部记录", key="confirm_clear_analysis_history"):
        if st.button("清空全部记录", type="secondary"):
            session_manager.clear_single_reports()
            st.success("已清空全部分析记录。")
            st.rerun()

    for index, record in enumerate(records, start=1):
        meta = record.get("metadata", {})
        title = _history_record_label(record)
        with st.expander(f"{index}. {title}", expanded=index == 1):
            cols = st.columns(4)
            cols[0].metric("最终样本数", meta.get("final_sample_count", 0))
            score_value = meta.get("overall_score")
            cols[1].metric("Overall Score", f"{float(score_value):.1f}" if score_value is not None else "--")
            cols[2].metric("Grade", meta.get("grade") or "--")
            cols[3].metric("可信度", meta.get("confidence") or "--")
            action_cols = st.columns([1, 1, 4])
            if action_cols[0].button("查看报告", key=f"view_history_{record.get('record_id')}"):
                session_manager.restore_analysis(record)
                st.session_state["history_view_record_id"] = record.get("record_id")
            confirm_delete = action_cols[1].checkbox("确认删除", key=f"confirm_delete_{record.get('record_id')}")
            if confirm_delete and action_cols[1].button("删除", key=f"delete_history_{record.get('record_id')}"):
                session_manager.delete_single_report(str(record.get("record_id")))
                st.success("已删除该分析记录。")
                st.rerun()

    selected_id = st.session_state.get("history_view_record_id")
    selected = next((record for record in session_manager.get_single_reports() if record.get("record_id") == selected_id), None)
    if selected:
        st.divider()
        st.subheader("已保存报告")
        _render_saved_analysis(selected, config, show_progress=True, show_context=True)


def _saved_report_label(payload: dict) -> str:
    parts = [
        str(payload.get("package_name") or "Unknown Game"),
        str(payload.get("scope") or ""),
        str(payload.get("time_display") or payload.get("time_mode") or ""),
        str(payload.get("analysis_timestamp") or ""),
    ]
    return " · ".join(part for part in parts if part)


def _history_record_label(payload: dict) -> str:
    meta = payload.get("metadata", {})
    return "｜".join(
        str(part)
        for part in [
            meta.get("game_name") or payload.get("package_name") or "Unknown Game",
            meta.get("market") or payload.get("scope") or "",
            _language_display(str(meta.get("language") or payload.get("language") or "")),
            meta.get("time_range") or payload.get("time_display") or "",
            f"{meta.get('final_sample_count', 0)}条",
            meta.get("analysis_time") or "",
        ]
        if str(part)
    )


def _localize_cross_game_row(row: dict) -> dict:
    labels = {
        "Game": "游戏",
        "Overall Score": "综合评分",
        "Player Satisfaction": "玩家满意度",
        "Product Health": "产品健康度",
        "Strength Bonus": "优势加成",
        "Confidence": "可信度",
        "Positive %": "正面占比",
        "Negative %": "负面占比",
        "Top Risk": "主要风险",
        "Top Strength": "主要优势",
    }
    return {labels.get(key, key): value for key, value in row.items()}


def _create_cross_game_radar_chart(rows: list[dict], theme_mode: str):
    labels = ["Overall Score", "Product Health", "Satisfaction", "Strengths", "Confidence"]
    metric_keys = ["Overall", "Health", "Satisfaction", "Strength", "Confidence"]
    angles = [index / float(len(labels)) * 2 * 3.141592653589793 for index in range(len(labels))]
    angles += angles[:1]
    is_dark = theme_mode == "dark"
    fig, ax = plt.subplots(figsize=(7.5, 5.5), subplot_kw={"polar": True})
    fig.patch.set_facecolor("#181818" if is_dark else "#FFFFFF")
    ax.set_facecolor("#181818" if is_dark else "#FFFFFF")
    palette = ["#F5C400", "#356CF6", "#2FBEC1", "#45B96A"]
    for index, row in enumerate(rows):
        values = [float(row["_radar"].get(key, 0)) for key in metric_keys]
        values += values[:1]
        ax.plot(angles, values, linewidth=2, label=str(row["Game"])[:28], color=palette[index % len(palette)])
        ax.fill(angles, values, alpha=0.08, color=palette[index % len(palette)])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, color="#F3F3F3" if is_dark else "#111111", fontsize=11)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], color="#B3B3B3" if is_dark else "#666666", fontsize=9)
    ax.grid(color="#303030" if is_dark else "#D7D7D2", linewidth=0.8)
    ax.spines["polar"].set_color("#303030" if is_dark else "#D7D7D2")
    legend = ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), frameon=False, fontsize=9)
    for text in legend.get_texts():
        text.set_color("#F3F3F3" if is_dark else "#111111")
    fig.tight_layout()
    return fig


def _ensure_authenticated() -> bool:
    access_password = os.getenv("APP_ACCESS_PASSWORD")
    if not access_password:
        return True
    if st.session_state.get("authenticated") is True:
        return True

    st.markdown("## GamePulse AI")
    st.caption("请输入访问密码以继续。")
    password = st.text_input("访问密码", type="password")
    if st.button("进入", type="primary"):
        if password == access_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("访问密码错误")
    return False


def _claude_api_key_configured() -> bool:
    if os.getenv("ANTHROPIC_API_KEY"):
        return True
    st.error("未配置 Claude API Key")
    st.caption("请在部署环境变量中配置 ANTHROPIC_API_KEY。")
    return False


def _render_analysis_running_anchor() -> None:
    st.markdown(
        """
        <div id="analysis-running" class="mi-report-item" style="margin-top:12px;">
          <strong>分析正在执行</strong>
          <small>正在获取评论、清洗数据并调用 Claude 进行结构化标注，请稍候。</small>
        </div>
        """,
        unsafe_allow_html=True,
    )
    components.html(
        """
        <script>
          const scrollToAnalysis = () => {
            const target = window.parent.document.getElementById("analysis-running");
            if (target) target.scrollIntoView({behavior: "smooth", block: "start"});
          };
          setTimeout(scrollToAnalysis, 80);
          setTimeout(scrollToAnalysis, 500);
        </script>
        """,
        height=0,
    )


def _sync_active_nav_page() -> None:
    st.session_state["active_page"] = st.session_state.get("nav_page", "首页")


def _open_analysis_history_page() -> None:
    st.session_state["active_page"] = "分析记录"
    st.session_state["nav_page"] = "首页"


def _render_sidebar_config() -> dict:
    with st.sidebar:
        ui.sidebar_branding()
        theme_choice = st.selectbox("主题", ["跟随系统", "浅色", "深色"], key="theme_choice")
        theme_mode = theme.resolve_theme_mode(theme_choice)

        ui.section_title("页面导航", "导航")
        page = st.radio(
            "页面",
            ["首页", "单市场分析", "跨市场分析", "跨游戏对比（Beta）"],
            horizontal=False,
            label_visibility="collapsed",
            key="nav_page",
            on_change=_sync_active_nav_page,
        )
        page = st.session_state.get("active_page", page)
        st.divider()
        ui.section_title("分析记录", "记录")
        st.button("查看分析记录", use_container_width=True, on_click=_open_analysis_history_page)
        page = st.session_state.get("active_page", page)

        if page in {"首页", "分析记录", "跨游戏对比（Beta）"}:
            return {
                "page": page,
                "theme_choice": theme_choice,
                "theme_mode": theme_mode,
                "analyze_button": False,
            }

        ui.section_title("评论来源", "数据来源")
        platform = st.selectbox("游戏平台", ["Google Play"], help="预留 Steam、App Store、TapTap 等评论来源。")
        raw_input = st.text_input("评论来源链接或包名", placeholder="com.example.game")

        st.divider()
        ui.section_title("分析模式", "分析模式")
        mode = page
        st.caption(mode)

        st.divider()
        ui.section_title("市场范围", "分析范围")
        if mode == "单市场分析":
            analysis_level = "国家/地区对比"
            country = _country_selectbox(DEFAULT_COUNTRY)
            selected_items = [country]
            market_data_source = "实时抓取分析"
            selected_record_ids: list[str] = []
        else:
            market_data_source = st.radio(
                "跨市场数据来源",
                ["实时抓取分析", "已保存分析记录"],
                help="选择已保存分析记录时，将直接读取分析记录，不重新抓取或调用 Claude。",
            )
            analysis_level = st.radio("分析层级", ["国家/地区对比", "区域对比"], horizontal=False)
            if analysis_level == "国家/地区对比":
                selected_items = st.multiselect(
                    "选择国家/地区（2-5 个）",
                    options=list(COUNTRY_OPTIONS),
                    default=["us", "jp", "kr"],
                    format_func=_format_country,
                )
            else:
                selected_items = st.multiselect(
                    "选择区域（自动覆盖代表国家，2-4 个）",
                    options=list(COUNTRY_GROUPS),
                    default=["东亚", "北美"],
                )
                st.caption("区域模式会自动抓取区域代表国家，用户无需逐个选择国家。")
            country = selected_items[0] if selected_items else DEFAULT_COUNTRY
            records = session_manager.get_single_reports()
            selected_record_ids = []
            if market_data_source == "已保存分析记录":
                record_options = [str(record.get("record_id")) for record in records]
                selected_record_ids = st.multiselect(
                    "选择已保存分析记录（2-5 条）",
                    options=record_options,
                    default=record_options[: min(2, len(record_options))],
                    format_func=lambda record_id: _history_record_label(next(record for record in records if str(record.get("record_id")) == record_id)),
                )

        st.divider()
        ui.section_title("语言策略", "评论来源")
        if mode == "单市场分析":
            comment_source = "指定语言评论（高级）"
            specified_language = _language_selectbox(DEFAULT_LANGUAGE)
            language = specified_language
            keep_other_languages = False
        else:
            comment_source, specified_language, keep_other_languages = _comment_source_controls()
            language = specified_language or DEFAULT_LANGUAGE
        language_filter_mode = LANGUAGE_FILTER_NONE if language == UNRESTRICTED_LANGUAGE or keep_other_languages else LANGUAGE_FILTER_STRICT

        st.divider()
        ui.section_title("分析参数", "分析参数")
        if mode == "单市场分析":
            st.caption("评论数量")
            review_count = st.number_input("评论数量", min_value=20, max_value=1000, value=DEFAULT_REVIEW_COUNT, step=20)
            st.caption("Claude 每批处理的评论数量")
            batch_size = st.slider("Claude 批处理数量", min_value=10, max_value=50, value=25, step=5)
            button_label = "开始分析"
        elif analysis_level == "区域对比":
            st.caption("区域模式下每个代表国家抓取相同数量")
            review_count = st.number_input("每个国家评论数量", min_value=20, max_value=100, value=30, step=10)
            st.caption("Claude 每批处理的评论数量")
            batch_size = st.slider("Claude 批处理数量", min_value=10, max_value=50, value=25, step=5)
            button_label = "生成区域洞察"
        else:
            st.caption("每个市场抓取相同数量")
            review_count = st.number_input("每个市场评论数量", min_value=20, max_value=1000, value=50, step=20)
            st.caption("Claude 每批处理的评论数量")
            batch_size = st.slider("Claude 批处理数量", min_value=10, max_value=50, value=25, step=5)
            button_label = "生成跨市场洞察"

        time_scope = _time_scope_controls()

        analyze_button = st.button(
            button_label,
            type="primary",
            use_container_width=True,
            disabled=not time_scope["time_valid"],
        )

    return {
        "page": page,
        "platform": platform,
        "theme_choice": theme_choice,
        "theme_mode": theme_mode,
        "raw_input": raw_input,
        "mode": mode,
        "analysis_level": analysis_level,
        "country": country,
        "selected_items": selected_items,
        "market_data_source": market_data_source,
        "selected_record_ids": selected_record_ids,
        "comment_source": comment_source,
        "specified_language": specified_language,
        "language": language,
        "language_filter_mode": language_filter_mode,
        "keep_other_languages": keep_other_languages,
        "review_count": review_count,
        "batch_size": batch_size,
        **time_scope,
        "analyze_button": analyze_button,
    }


def _time_scope_controls() -> dict:
    st.caption("评论时间范围")
    today = date.today()
    mode = st.radio(
        "评论时间范围",
        options=time_scope_utils.TIME_MODE_OPTIONS,
        index=time_scope_utils.TIME_MODE_OPTIONS.index(time_scope_utils.TIME_MODE_LAST_30),
        help="根据 Google Play 评论发布时间过滤样本，适合按版本周期观察反馈。",
    )
    custom_start = None
    custom_end = None
    if mode == time_scope_utils.TIME_MODE_CUSTOM:
        custom_start = st.date_input("开始日期", value=today - timedelta(days=29))
        custom_end = st.date_input("结束日期", value=today)
    scope = time_scope_utils.resolve_time_scope(mode, today, custom_start, custom_end)
    valid, error = time_scope_utils.validate_time_scope(scope)
    if not valid:
        st.error(error)
    return {
        "time_mode": scope.mode,
        "start_date": scope.start_key,
        "end_date": scope.end_key,
        "time_display": scope.display,
        "time_valid": valid,
    }


def _render_context_bar(package_name: str, mode: str, scope: str) -> None:
    cols = st.columns([2, 1, 1])
    cols[0].metric("当前包名", package_name)
    cols[1].metric("分析模式", mode)
    cols[2].metric("分析范围", scope)


def _render_process_flow(active_index: int) -> None:
    steps = ["01 获取评论", "02 数据清洗", "03 语言过滤", "04 Claude 分类", "05 情感分析", "06 市场洞察", "07 AI 总结", "08 报告导出"]
    html = []
    for index, step in enumerate(steps):
        class_name = "mi-step"
        if active_index >= 0 and index < active_index:
            class_name += " mi-step-done"
        if index == active_index:
            class_name += " mi-step-active"
        html.append(f"<span class='{class_name}'>{step}</span>")
    st.markdown(f"<div class='mi-workflow'>{''.join(html)}</div>", unsafe_allow_html=True)


def _render_single_market_page(config: dict) -> None:
    raw_input = config["raw_input"]
    review_count = config["review_count"]
    lang = config["language"]
    country = config["country"]
    batch_size = config["batch_size"]
    language_filter_mode = config["language_filter_mode"]

    if not raw_input.strip():
        st.warning("请输入游戏平台评论链接或包名。")
        return
    if not _claude_api_key_configured():
        return

    progress = progress_ui.ProgressTracker()
    started_at = time.perf_counter()
    performance = {"started_at": started_at}
    analysis_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        package_name = extract_package_name(raw_input)
        _render_context_bar(package_name, "单市场分析", _format_country(country))

        progress.update(1, "正在连接 Google Play 评论来源。")
        request_lang = _google_play_request_language(lang, country)
        prepared = _cached_fetch_prepare(
            package_name,
            int(review_count),
            request_lang,
            country,
            lang,
            language_filter_mode,
            config["time_mode"],
            config["start_date"],
            config["end_date"],
        )
        performance.update(prepared.get("performance", {}))
        progress.update(2, "数据清洗完成。")
        progress.update(3, "语言过滤完成。")
        if language_filter_mode == LANGUAGE_FILTER_NONE:
            st.info("当前未限制评论语言，分析将包含该商店地区返回的所有语言评论。")

        if not prepared["filtered_reviews"]:
            progress.update(3, "目标语言评论不足，已保留基础统计。", state="error")
            _render_basic_stats(prepared)
            if prepared.get("time_filtered_count", 0) == 0:
                st.warning("当前时间范围内暂无可分析评论，请扩大时间范围。")
            else:
                st.warning("目标语言评论不足，无法继续分类分析。请尝试增加抓取数量、切换地区或调整语言。")
            st.caption(_market_sample_notice())
            st.write(f"本次分析耗时：{time.perf_counter() - started_at:.1f} 秒")
            return

        progress.update(4, "正在调用 Claude 分类、提取原因并生成中文概括。")
        classify_started = time.perf_counter()
        result = _classify_reviews_with_cache(
            package_name,
            country,
            lang,
            tuple(prepared["filtered_reviews"]),
            int(batch_size),
            config["time_mode"],
            config["start_date"],
            config["end_date"],
        )
        performance["classification_total_seconds"] = time.perf_counter() - classify_started
        if not result.classified_reviews:
            progress.update(4, "Claude 批处理未生成有效分类结果。", state="error")
            debug_payload = {
                "type": "single",
                "package_name": package_name,
                "mode": "单市场分析",
                "scope": _format_country(country),
                "language": lang,
                "country": country,
                "review_count": int(review_count),
                "batch_size": int(batch_size),
                "analysis_timestamp": analysis_timestamp,
                "from_session_state": False,
                "prepared": prepared,
                "result": result,
            }
            _render_basic_stats(prepared)
            _render_data_integrity(debug_payload)
            st.error("本次分析未成功完成，未生成有效结果。")
            st.caption(_market_sample_notice())
            st.write(f"本次分析耗时：{time.perf_counter() - started_at:.1f} 秒")
            return
        progress.update(7, "情感分析、市场洞察和 AI 总结已完成。")

        elapsed = time.perf_counter() - started_at
        excluded_evidence_terms = _excluded_evidence_terms(package_name, raw_input)
        report = build_single_market_report(result, len(result.classified_reviews), excluded_evidence_terms=excluded_evidence_terms)
        performance["evaluation_seconds"] = float(report.pop("_evaluation_elapsed_seconds", 0.0) or 0.0)
        result, report, summary_error, summary_perf = _apply_single_ai_summary(result, report)
        performance.update(summary_perf)
        performance["total_seconds"] = time.perf_counter() - started_at
        payload = {
            "type": "single",
            "package_name": package_name,
            "raw_input": raw_input,
            "mode": "单市场分析",
            "scope": _format_country(country),
            "language": lang,
            "request_language": request_lang,
            "language_filter_mode": language_filter_mode,
            "country": country,
            "review_count": int(review_count),
            "batch_size": int(batch_size),
            "analysis_timestamp": analysis_timestamp,
            "time_mode": config["time_mode"],
            "start_date": config["start_date"],
            "end_date": config["end_date"],
            "time_display": config["time_display"],
            "from_session_state": False,
            "prepared": prepared,
            "result": result,
            "category_counts": result.category_counts,
            "sentiment": _sentiment_percentages(result.classified_reviews),
            "ai_summary": result.summary,
            "representative_reviews": result.classified_reviews[:6],
            "chart_data": sort_category_counts(result.category_counts),
            "report": report,
            "excluded_evidence_terms": excluded_evidence_terms,
            "summary_error": summary_error,
            "elapsed": elapsed,
            "fetch_time": analysis_timestamp,
            "performance": performance,
        }
        session_manager.save_analysis(payload, session_manager.AnalysisSignature.from_config(config))
        saved_state = session_manager.get_analysis()
        if saved_state:
            payload = dict(saved_state["payload"])
        progress.update(7, "分析完成，可查看下方市场洞察报告；PPT 尚未生成。", state="complete")
        st.markdown("<a class='mi-report-link' href='#market-insight-report'>查看分析报告</a>", unsafe_allow_html=True)
        _render_saved_analysis(payload, config, show_progress=False, show_context=False)

        st.caption(_market_sample_notice())
        st.write(f"本次分析耗时：{elapsed:.1f} 秒")

    except Exception as exc:
        progress.update(4, f"分析中断：{exc}", state="error")
        st.error(f"分析失败：{exc}")


def _render_market_comparison_page(config: dict) -> None:
    if config.get("market_data_source") == "已保存分析记录":
        _render_saved_records_market_comparison(config)
        return

    raw_input = config["raw_input"]
    analysis_level = config["analysis_level"]
    comment_source = config["comment_source"]
    specified_language = config["specified_language"]
    selected_items = config["selected_items"]
    review_count = config["review_count"]
    batch_size = config["batch_size"]
    theme_mode = config["theme_mode"]
    keep_other_languages = config["keep_other_languages"]

    if not raw_input.strip():
        st.warning("请输入游戏平台评论链接或包名。")
        return
    if not _claude_api_key_configured():
        return
    if analysis_level == "国家/地区对比" and (len(selected_items) < 2 or len(selected_items) > 5):
        st.warning("跨市场对比需要选择 2-5 个国家/地区。")
        return
    if analysis_level == "区域对比" and (len(selected_items) < 2 or len(selected_items) > 4):
        st.warning("区域对比需要选择 2-4 个区域。")
        return

    started_at = time.perf_counter()
    progress_tracker = progress_ui.ProgressTracker()
    try:
        package_name = extract_package_name(raw_input)
        _render_context_bar(package_name, "跨市场分析", analysis_level)
        st.caption(_region_sample_notice() if analysis_level == "区域对比" else _market_sample_notice())

        country_results = []
        progress_tracker.update(1, "准备开始跨市场分析。")
        country_plan = _build_country_plan(analysis_level, selected_items)

        for index, plan_item in enumerate(country_plan, start=1):
            progress_tracker.update(4, f"正在处理 {_format_country(plan_item['country'])} · {index} / {len(country_plan)}")
            country_results.append(
                _run_country_analysis(
                    package_name=package_name,
                    country=plan_item["country"],
                    region=plan_item["region"],
                    comment_source=comment_source,
                    specified_language=specified_language,
                    keep_other_languages=keep_other_languages,
                    review_count=int(review_count),
                    batch_size=int(batch_size),
                    time_mode=config["time_mode"],
                    start_date=config["start_date"],
                    end_date=config["end_date"],
                )
            )

        progress_tracker.update(6, "各市场分类完成，正在汇总指标。")
        if analysis_level == "区域对比":
            display_results = _aggregate_region_results(country_results)
        else:
            display_results = country_results

        rows = [_build_comparison_row(item) for item in display_results]
        valid_pairs = [
            (item, row)
            for item, row in zip(display_results, rows)
            if row.get("评分状态") == "可评分"
        ]
        progress_tracker.update(7, "正在生成中文跨市场总结。")
        if len(valid_pairs) >= 2:
            summary_payload = tuple(_build_summary_payload(item, row) for item, row in valid_pairs)
            comparison_summary = _cached_market_summary(summary_payload)
        else:
            comparison_summary = "可评分市场不足 2 个，暂不生成跨市场高低分结论；请扩大时间范围、调整语言或增加样本。"
        elapsed = time.perf_counter() - started_at

        payload = {
            "type": "market",
            "package_name": package_name,
            "analysis_level": analysis_level,
            "time_mode": config["time_mode"],
            "start_date": config["start_date"],
            "end_date": config["end_date"],
            "time_display": config["time_display"],
            "rows": rows,
            "market_results": display_results,
            "comparison_summary": comparison_summary,
            "country_details": country_results if analysis_level == "区域对比" else None,
            "chart_data": rows,
            "ai_summary": comparison_summary,
            "elapsed": elapsed,
        }
        session_manager.save_analysis(payload, session_manager.AnalysisSignature.from_config(config))
        progress_tracker.update(7, "分析完成，可查看下方市场洞察报告；PPT 尚未生成。", state="complete")
        st.markdown("<a class='mi-report-link' href='#market-insight-report'>查看分析报告</a>", unsafe_allow_html=True)
        _render_saved_analysis(payload, config, show_progress=False, show_context=False)
        st.write(f"本次分析耗时：{elapsed:.1f} 秒")

    except Exception as exc:
        progress_tracker.update(4, f"跨市场分析中断：{exc}", state="error")
        st.error(f"跨市场对比失败：{exc}")


def _render_saved_records_market_comparison(config: dict) -> None:
    records = session_manager.get_single_reports()
    selected_ids = set(config.get("selected_record_ids") or [])
    selected_records = [record for record in records if str(record.get("record_id")) in selected_ids]
    if len(selected_records) < 2:
        st.warning("请先选择至少两条已保存的分析记录。")
        return
    if len(selected_records) > 5:
        st.warning("最多选择 5 条已保存的分析记录。")
        return

    market_results = [_market_result_from_record(record) for record in selected_records]
    rows = [_build_comparison_row(item) for item in market_results]
    comparison_summary = _saved_records_comparison_summary(rows)
    payload = {
        "type": "market",
        "package_name": "已保存分析记录",
        "analysis_level": "已保存记录对比",
        "rows": rows,
        "market_results": market_results,
        "comparison_summary": comparison_summary,
        "country_details": None,
        "chart_data": rows,
        "ai_summary": comparison_summary,
        "elapsed": 0.0,
    }
    if _has_record_parameter_differences(selected_records):
        st.warning("所选报告的游戏、时间范围、语言或样本规模不完全一致，比较结果仅供辅助参考。")
    _render_market_comparison_saved(payload, config)


def _market_result_from_record(record: dict) -> dict:
    meta = record.get("metadata", {})
    return {
        "country": meta.get("country") or record.get("country", ""),
        "country_label": meta.get("market") or record.get("scope") or record.get("package_name", ""),
        "region": "已保存记录",
        "market_label": meta.get("market") or record.get("scope") or record.get("package_name", ""),
        "language": record.get("language", ""),
        "prepared": record.get("prepared", {}),
        "result": record.get("result"),
    }


def _has_record_parameter_differences(records: list[dict]) -> bool:
    packages = {record.get("package_name") for record in records}
    languages = {record.get("language") for record in records}
    time_ranges = {record.get("time_display") or record.get("time_mode") for record in records}
    sample_counts = [int((record.get("prepared") or {}).get("language_filtered_count", 0) or 0) for record in records]
    sample_diff = max(sample_counts or [0]) - min(sample_counts or [0])
    return len(packages) > 1 or len(languages) > 1 or len(time_ranges) > 1 or sample_diff > 50


def _saved_records_comparison_summary(rows: list[dict]) -> str:
    if len(rows) < 2:
        return "请先选择至少两条已保存的分析记录。"
    best = max(rows, key=lambda row: float(row.get("Overall Score", 0) or 0))
    worst_negative = max(rows, key=lambda row: _parse_percent(row.get("负面占比", "0%")))
    return (
        f"{best['市场']} 在所选记录中综合评分最高（{best.get('Overall Score')}），"
        f"{worst_negative['市场']} 的负面占比最高（{worst_negative.get('负面占比')}），"
        "建议结合各记录的时间范围、语言和样本量差异谨慎解读。"
    )


def _parse_percent(value: object) -> float:
    try:
        return float(str(value).replace("%", ""))
    except ValueError:
        return 0.0


def _comment_source_controls() -> tuple[str, str | None, bool]:
    comment_source = st.radio(
        "评论来源",
        ["当地玩家评论（推荐）", "指定语言评论（高级）"],
        help="当地玩家评论会按国家/地区自动选择本地常用语言；指定语言评论会让所有市场抓取同一种语言。",
    )
    if comment_source == "当地玩家评论（推荐）":
        st.caption(
            "自动抓取各国家玩家最常使用语言发布的评论，例如日本→日文、韩国→韩文、美国→英文、法国→法文。"
        )
        st.caption("分析阶段统一输出中文分类、中文概括和中文 AI 总结，适用于海外发行、本地化分析和市场洞察。")
        keep_other_languages = st.checkbox(
            "保留其他语言评论",
            value=False,
            help="开启后仍按各市场默认语言请求 Google Play，但清洗后不再执行二次语言过滤。",
        )
        return comment_source, None, keep_other_languages

    st.caption("只抓取指定语言评论，例如日本+英文、韩国+英文、美国+英文。")
    st.caption("适用于排除语言影响、全球英文社区分析和国际服玩家分析。")
    return comment_source, _language_selectbox(DEFAULT_LANGUAGE), False


def _build_country_plan(analysis_level: str, selected_items: list[str]) -> list[dict]:
    if analysis_level == "国家/地区对比":
        return [
            {"country": country, "region": COUNTRY_OPTIONS[country]["region"]}
            for country in selected_items
        ]

    return [
        {"country": country, "region": region}
        for region in selected_items
        for country in COUNTRY_GROUPS[region]
    ]


def _run_country_analysis(
    package_name: str,
    country: str,
    region: str,
    comment_source: str,
    specified_language: str | None,
    keep_other_languages: bool,
    review_count: int,
    batch_size: int,
    time_mode: str,
    start_date: str,
    end_date: str,
) -> dict:
    lang = specified_language if comment_source == "指定语言评论（高级）" else market_default_language(country, "en")
    language_filter_mode = LANGUAGE_FILTER_NONE if lang == UNRESTRICTED_LANGUAGE or keep_other_languages else LANGUAGE_FILTER_STRICT
    request_lang = _google_play_request_language(lang, country)
    filter_lang = market_default_language(country, "en") if lang == UNRESTRICTED_LANGUAGE else lang
    base_item = {
        "country": country,
        "country_label": market_label(country),
        "region": region,
        "market_label": market_label(country),
        "language": lang,
        "request_language": request_lang,
        "requested_country": country,
        "requested_lang": request_lang,
        "language_filter_mode": language_filter_mode,
    }
    try:
        prepared = _cached_fetch_prepare(
            package_name,
            review_count,
            request_lang,
            country,
            filter_lang,
            language_filter_mode,
            time_mode,
            start_date,
            end_date,
        )
    except Exception as exc:
        failure_status, failure_message = _market_fetch_failure_status(exc)
        return {
            **base_item,
            "prepared": _empty_market_prepared(review_count, request_lang, filter_lang, language_filter_mode, time_mode, start_date, end_date),
            "result": _empty_analysis_result(),
            "scoring_status": failure_status,
            "status_message": failure_message,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }

    final_sample_count = int(prepared.get("language_filtered_count", 0) or 0)
    scoring_status, status_message = _market_scoring_status(prepared)
    if scoring_status == "scorable":
        try:
            result = _classify_reviews_with_cache(
                package_name,
                country,
                lang,
                tuple(prepared["filtered_reviews"]),
                batch_size,
                time_mode,
                start_date,
                end_date,
            )
            if len(result.classified_reviews) < MIN_SCORABLE_REVIEWS:
                scoring_status = "insufficient_sample"
                status_message = f"当前成功分类仅{len(result.classified_reviews)}条，样本不足，不具备稳定评分条件。"
        except Exception as exc:
            result = _empty_analysis_result()
            scoring_status = "request_failed"
            status_message = "该市场评论分类失败，其他市场结果已保留。"
            return {
                **base_item,
                "prepared": prepared,
                "result": result,
                "scoring_status": scoring_status,
                "status_message": status_message,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "final_sample_count": final_sample_count,
            }
    else:
        result = _empty_analysis_result()

    return {
        **base_item,
        "prepared": prepared,
        "result": result,
        "scoring_status": scoring_status,
        "status_message": status_message,
        "final_sample_count": final_sample_count,
    }


def _empty_analysis_result() -> AnalysisResult:
    return AnalysisResult(
        classified_reviews=[],
        category_counts={category: 0 for category in REVIEW_CATEGORIES},
        most_satisfied=[],
        most_unsatisfied=[],
        summary="",
    )


def _empty_market_prepared(
    review_count: int,
    request_lang: str,
    filter_lang: str,
    language_filter_mode: str,
    time_mode: str,
    start_date: str,
    end_date: str,
) -> dict:
    return {
        "raw_count": 0,
        "raw_fetched_count": 0,
        "time_filtered_count": 0,
        "target_sample_count": review_count,
        "analysis_sample_count": 0,
        "cleaned_count": 0,
        "deduplicated_count": 0,
        "language_filtered_count": 0,
        "language_mismatch_count": 0,
        "request_lang": request_lang,
        "filter_lang": filter_lang,
        "language_filter_mode": language_filter_mode,
        "time_mode": time_mode,
        "start_date": start_date,
        "end_date": end_date,
        "filtered_reviews": tuple(),
        "cleaned_reviews": tuple(),
        "raw_reviews": tuple(),
    }


def _market_scoring_status(prepared: dict) -> tuple[str, str]:
    final_count = int(prepared.get("language_filtered_count", 0) or 0)
    raw_count = int(prepared.get("raw_fetched_count", prepared.get("raw_count", 0)) or 0)
    time_count = int(prepared.get("time_filtered_count", 0) or 0)
    cleaned_count = int(prepared.get("cleaned_count", 0) or 0)
    language_mismatch = int(prepared.get("language_mismatch_count", 0) or 0)
    if final_count >= MIN_SCORABLE_REVIEWS:
        return "scorable", "可评分"
    if raw_count == 0:
        return "no_reviews", "该市场当前未返回公开评论。"
    if time_count == 0:
        return "time_range_empty", "该市场在所选时间范围内没有评论，可扩大时间范围。"
    if cleaned_count == 0:
        return "no_reviews", "该市场当前未返回可清洗的公开评论。"
    if language_mismatch > 0 and final_count == 0:
        return "language_filter_empty", "该市场未获取到符合所选语言的评论，可尝试统一英语或其他语言。"
    if final_count == 0:
        return "not_scorable", "该市场未获取到可分析评论，不具备评分条件。"
    return "insufficient_sample", f"当前有效样本仅{final_count}条，样本不足，不具备稳定评分条件。"


def _market_fetch_failure_status(exc: Exception) -> tuple[str, str]:
    message = str(exc).lower()
    if "not found" in message or "404" in message or "not exist" in message:
        return "app_unavailable", "该应用可能未在该 Google Play 市场上架。"
    if "language" in message or "lang" in message or "hl" in message:
        return "unsupported_language", "该市场语言参数可能不受支持，可尝试统一英语或跟随市场本地语言。"
    return "request_failed", "该市场评论抓取失败，请检查网络后重试。"


def _aggregate_region_results(country_results: list[dict]) -> list[dict]:
    region_results = []
    for region in COUNTRY_GROUPS:
        region_countries = [item for item in country_results if item["region"] == region]
        if not region_countries:
            continue

        classified_reviews = [
            review
            for item in region_countries
            for review in item["result"].classified_reviews
        ]
        filtered_reviews = [
            record
            for item in region_countries
            for record in item["prepared"]["filtered_reviews"]
        ]
        category_counts = {
            category: sum(item["result"].category_counts.get(category, 0) for item in region_countries)
            for category in REVIEW_CATEGORIES
        }
        result = AnalysisResult(
            classified_reviews=classified_reviews,
            category_counts=category_counts,
            most_satisfied=_dedupe_items([point for item in region_countries for point in item["result"].most_satisfied])[:5],
            most_unsatisfied=_dedupe_items([point for item in region_countries for point in item["result"].most_unsatisfied])[:5],
            summary="\n".join(item["result"].summary for item in region_countries if item["result"].summary),
        )
        region_prepared = {
            "raw_count": sum(item["prepared"]["raw_count"] for item in region_countries),
            "raw_fetched_count": sum(item["prepared"].get("raw_fetched_count", item["prepared"]["raw_count"]) for item in region_countries),
            "time_filtered_count": sum(item["prepared"].get("time_filtered_count", item["prepared"]["raw_count"]) for item in region_countries),
            "cleaned_count": sum(item["prepared"]["cleaned_count"] for item in region_countries),
            "language_filtered_count": len(filtered_reviews),
            "language_mismatch_count": sum(item["prepared"]["language_mismatch_count"] for item in region_countries),
            "time_mode": region_countries[0]["prepared"].get("time_mode", ""),
            "start_date": region_countries[0]["prepared"].get("start_date", ""),
            "end_date": region_countries[0]["prepared"].get("end_date", ""),
            "time_display": region_countries[0]["prepared"].get("time_display", ""),
            "language_filter_mode": LANGUAGE_FILTER_NONE
            if any(item["prepared"].get("language_filter_mode") == LANGUAGE_FILTER_NONE for item in region_countries)
            else LANGUAGE_FILTER_STRICT,
            "filtered_reviews": tuple(filtered_reviews),
        }
        scoring_status = "scorable" if len(classified_reviews) >= MIN_SCORABLE_REVIEWS else "insufficient_sample"
        region_results.append(
            {
                "country": region,
                "country_label": region,
                "region": region,
                "market_label": region,
                "language": "多语言",
                "prepared": region_prepared,
                "result": result,
                "country_details": region_countries,
                "scoring_status": scoring_status,
                "status_message": "可评分" if scoring_status == "scorable" else "区域内可评分样本不足。",
            }
        )

    return region_results


def _dedupe_items(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        value = item.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _language_selectbox(default_code: str) -> str:
    language_codes = list(LANGUAGE_OPTIONS)
    return st.selectbox(
        "评论语言",
        options=language_codes,
        index=language_codes.index(default_code),
        format_func=lambda code: f"{LANGUAGE_OPTIONS[code]} ({code})",
        help="决定优先抓取哪种语言的评论。",
    )


def _google_play_request_language(selected_language: str, country: str) -> str:
    if selected_language == UNRESTRICTED_LANGUAGE:
        return LOCAL_LANGUAGE_BY_COUNTRY.get(country, DEFAULT_LANGUAGE)
    return selected_language


def _language_display(code: str) -> str:
    return LANGUAGE_OPTIONS.get(code, code)


def _country_selectbox(default_code: str) -> str:
    country_codes = list(COUNTRY_OPTIONS)
    return st.selectbox(
        "国家/地区",
        options=country_codes,
        index=country_codes.index(default_code),
        format_func=_format_country,
        help="决定访问哪个地区的 Google Play 商店，不会读取用户 IP。",
    )


def _format_country(code: str) -> str:
    option = COUNTRY_OPTIONS[code]
    return f"{option['region']} - {option['name']} ({code})"


def _excluded_evidence_terms(package_name: str, raw_input: str = "") -> list[str]:
    terms = ["Google", "Google Play", "Play Store", "app", "game", package_name, raw_input]
    terms.extend(part for part in re.split(r"[._\-/=&?]+", str(package_name or "")) if len(part) > 2)
    return [term for term in terms if str(term).strip()]


@st.cache_data(show_spinner=False)
def _cached_fetch_prepare(
    package_name: str,
    review_count: int,
    request_lang: str,
    country: str,
    filter_lang: str,
    language_filter_mode: str,
    time_mode: str,
    start_date: str,
    end_date: str,
    fetch_cache_version: str = FETCH_CACHE_VERSION,
) -> dict:
    fetch_started = time.perf_counter()
    raw_reviews, fetch_meta = fetch_reviews_with_meta(
        package_name,
        review_count,
        lang=request_lang,
        country=country,
        start_date=time_scope_utils.parse_date_key(start_date),
        end_date=time_scope_utils.parse_date_key(end_date),
    )
    fetch_seconds = time.perf_counter() - fetch_started
    cleaning_started = time.perf_counter()
    cleaned_reviews = clean_reviews(raw_reviews)
    if language_filter_mode == LANGUAGE_FILTER_NONE:
        filtered_reviews = cleaned_reviews
        language_mismatch_count = 0
    else:
        filtered_reviews, language_mismatch_count = filter_reviews_by_language(cleaned_reviews, filter_lang)
    cleaning_seconds = time.perf_counter() - cleaning_started
    return {
        "raw_count": int(fetch_meta.get("raw_fetched_count", len(raw_reviews))),
        "raw_fetched_count": int(fetch_meta.get("raw_fetched_count", len(raw_reviews))),
        "raw_api_count": int(fetch_meta.get("raw_api_count", fetch_meta.get("raw_fetched_count", len(raw_reviews)))),
        "valid_datetime_count": int(fetch_meta.get("valid_datetime_count", 0)),
        "time_filtered_count": int(fetch_meta.get("time_filtered_count", len(raw_reviews))),
        "target_sample_count": int(fetch_meta.get("target_sample_count", review_count)),
        "analysis_sample_count": int(fetch_meta.get("analysis_sample_count", len(raw_reviews))),
        "cleaned_count": len(cleaned_reviews),
        "deduplicated_count": len(cleaned_reviews),
        "language_filtered_count": len(filtered_reviews),
        "language_mismatch_count": language_mismatch_count,
        "time_filter_mode": fetch_meta.get("time_filter_mode", "unlimited" if not start_date and not end_date else "bounded"),
        "resolved_start_datetime": fetch_meta.get("resolved_start_datetime", ""),
        "resolved_end_datetime": fetch_meta.get("resolved_end_datetime", ""),
        "earliest_raw_review_time": fetch_meta.get("earliest_raw_review_time", ""),
        "latest_raw_review_time": fetch_meta.get("latest_raw_review_time", ""),
        "earliest_filtered_review_time": fetch_meta.get("earliest_filtered_review_time", ""),
        "latest_filtered_review_time": fetch_meta.get("latest_filtered_review_time", ""),
        "invalid_datetime_count": int(fetch_meta.get("invalid_datetime_count", 0)),
        "before_start_count": int(fetch_meta.get("before_start_count", 0)),
        "after_end_count": int(fetch_meta.get("after_end_count", 0)),
        "page_count": int(fetch_meta.get("page_count", 0)),
        "stop_reason": fetch_meta.get("stop_reason", ""),
        "page_diagnostics": tuple(tuple(sorted(page.items())) for page in fetch_meta.get("page_diagnostics", [])),
        "fetch_cache_version": fetch_cache_version,
        "time_filter_valid": bool(fetch_meta.get("time_filter_valid", True)),
        "reached_before_start": bool(fetch_meta.get("reached_before_start", False)),
        "max_fetch_reviews": int(fetch_meta.get("max_fetch_reviews", 0)),
        "request_lang": request_lang,
        "filter_lang": filter_lang,
        "language_filter_mode": language_filter_mode,
        "time_mode": time_mode,
        "start_date": start_date,
        "end_date": end_date,
        "time_display": time_scope_utils.TimeScope(
            time_mode,
            time_scope_utils.parse_date_key(start_date),
            time_scope_utils.parse_date_key(end_date),
        ).display,
        "raw_reviews": tuple(_review_to_record(review) for review in raw_reviews),
        "cleaned_reviews": tuple(_review_to_record(review) for review in cleaned_reviews),
        "filtered_reviews": tuple(_review_to_record(review) for review in filtered_reviews),
        "performance": {
            "fetch_seconds": fetch_seconds,
            "cleaning_seconds": cleaning_seconds,
        },
    }


def _classify_reviews_with_cache(
    package_name: str,
    country: str,
    language: str,
    review_records: tuple[tuple, ...],
    batch_size: int,
    time_mode: str,
    start_date: str,
    end_date: str,
):
    cache_key = _classification_cache_key(
        package_name,
        country,
        language,
        review_records,
        batch_size,
        time_mode,
        start_date,
        end_date,
    )
    cache = st.session_state.setdefault("classification_cache_v2", {})
    cached = cache.get(cache_key)
    if _valid_cached_result(cached, len(review_records)):
        return replace(cached, cache_hit=True, classify_calls=0)

    reviews = _records_to_reviews(review_records)
    classify_model = os.getenv("CLAUDE_CLASSIFY_MODEL") or os.getenv("CLAUDE_MODEL")
    claude_client = ClaudeClient(model=classify_model)
    result = classify_reviews(reviews, claude_client, batch_size=batch_size, country=country)
    result = replace(result, cache_hit=False)
    if _valid_cached_result(result, len(review_records)):
        cache[cache_key] = result
    return result


def _classification_cache_key(
    package_name: str,
    country: str,
    language: str,
    review_records: tuple[tuple, ...],
    batch_size: int,
    time_mode: str,
    start_date: str,
    end_date: str,
) -> str:
    review_text = "\n".join(f"{record[0]}|{record[2]}|{record[3]}" for record in review_records)
    review_hash = hashlib.sha256(review_text.encode("utf-8")).hexdigest()
    model = os.getenv("CLAUDE_CLASSIFY_MODEL") or os.getenv("CLAUDE_MODEL") or "default"
    return json.dumps(
        {
            "package_name": package_name,
            "country": country,
            "language": language,
            "review_text_hash": review_hash,
            "model": model,
            "batch_size": batch_size,
            "input_review_count": len(review_records),
            "time_mode": time_mode,
            "start_date": start_date,
            "end_date": end_date,
            "prompt_version": CLASSIFICATION_PROMPT_VERSION,
            "schema_version": CLASSIFICATION_SCHEMA_VERSION,
        },
        sort_keys=True,
        ensure_ascii=False,
    )


def _valid_cached_result(result, expected_count: int) -> bool:
    if not isinstance(result, AnalysisResult):
        return False
    diagnostics = getattr(result, "batch_diagnostics", None)
    if not diagnostics:
        return False
    reviews = getattr(result, "classified_reviews", [])
    if not reviews or len(reviews) != expected_count:
        return False
    review_ids = [getattr(review, "review_id", None) for review in reviews]
    if len(review_ids) != len(set(review_ids)):
        return False
    try:
        normalized_ids = {int(review_id) for review_id in review_ids}
    except (TypeError, ValueError):
        return False
    if normalized_ids != set(range(1, expected_count + 1)):
        return False
    return all(getattr(review, "schema_version", "") == CLASSIFICATION_SCHEMA_VERSION for review in reviews)


@st.cache_data(show_spinner=False)
def _cached_market_summary(summary_payload: tuple[dict, ...]) -> str:
    claude_client = ClaudeClient()
    return summarize_market_comparison(list(summary_payload), claude_client)


def _review_to_record(review: ReviewItem) -> tuple:
    return (review.review_id, review.user_name, review.score, review.content, review.date)


def _records_to_reviews(records: tuple[tuple, ...]) -> list[ReviewItem]:
    return [
        ReviewItem(
            review_id=str(record[0]),
            user_name=str(record[1]),
            score=record[2],
            content=str(record[3]),
            date=str(record[4]),
        )
        for record in records
    ]


def _render_basic_stats(prepared: dict) -> None:
    cols = st.columns(4)
    cols[0].metric("原始抓取数量", prepared["raw_count"])
    cols[1].metric("清洗后数量", prepared["cleaned_count"])
    cols[2].metric("语言过滤后数量", prepared["language_filtered_count"])
    cols[3].metric("语言不匹配过滤数量", prepared["language_mismatch_count"])


def _render_saved_analysis(payload: dict, config: dict, show_progress: bool = True, show_context: bool = True) -> None:
    if payload["type"] == "single":
        render_started = time.perf_counter()
        if show_context:
            _render_context_bar(payload["package_name"], payload["mode"], payload["scope"])
        if show_progress:
            progress_ui.render_saved_complete()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            result = payload["result"]
            sorted_counts = sort_category_counts(result.category_counts)
            theme_mode = config.get("theme_mode", "light")
            bar_chart_path = create_bar_chart(sorted_counts, temp_path / "category_bar.png", theme_mode=theme_mode)
            pie_chart_path = create_pie_chart(sorted_counts, temp_path / "category_pie.png", theme_mode=theme_mode)
            _render_result(payload, bar_chart_path, pie_chart_path)
        payload.setdefault("performance", {})["render_seconds"] = time.perf_counter() - render_started
        _render_performance_summary(payload)
        return

    if show_progress:
        progress_ui.render_saved_complete()
    if show_context:
        _render_context_bar(payload["package_name"], "跨市场分析", payload["analysis_level"])
    _render_market_comparison_saved(payload, config)


def _render_result(payload: dict, bar_chart_path: Path, pie_chart_path: Path) -> None:
    result = payload["result"]
    prepared = payload["prepared"]
    sorted_counts = sort_category_counts(result.category_counts)
    report = payload.get("report") or build_single_market_report(
        result,
        len(result.classified_reviews),
        excluded_evidence_terms=payload.get("excluded_evidence_terms"),
    )
    if "overall_score" not in report:
        report = build_single_market_report(
            result,
            len(result.classified_reviews),
            excluded_evidence_terms=payload.get("excluded_evidence_terms"),
        )
    else:
        fresh_report = build_single_market_report(
            result,
            len(result.classified_reviews),
            excluded_evidence_terms=payload.get("excluded_evidence_terms"),
        )
        report = _merge_fresh_evaluation(report, fresh_report)
    consistency_errors = _report_consistency_errors(payload, result, prepared, report)

    st.markdown("<div id='market-insight-report'></div>", unsafe_allow_html=True)
    st.subheader("市场洞察报告")
    _render_report_trace(payload, prepared, result, report)
    if consistency_errors:
        st.error("检测到报告数据状态不一致，请重新选择历史记录或重新分析。")
        for error in consistency_errors:
            st.caption(error)
        return
    _render_basic_stats(prepared)
    _render_data_integrity(payload)
    if int(prepared.get("language_filtered_count", 0)) < int(payload.get("review_count", 0)):
        st.warning(f"当前时间范围仅获取{int(prepared.get('language_filtered_count', 0))}条有效评论，报告基于实际样本生成。")
    if prepared.get("language_filter_mode") == LANGUAGE_FILTER_NONE:
        st.info("当前未限制评论语言，分析将包含该商店地区返回的所有语言评论。")
    if prepared["language_filtered_count"] < 20:
        st.warning("当前有效样本量较小，结论仅反映本次抓取样本，不代表完整市场表现。")

    report_tab, reviews_tab = st.tabs(["分析报告", "代表性评论"])
    with report_tab:
        _render_analysis_report(payload, bar_chart_path, pie_chart_path, report, sorted_counts)
    with reviews_tab:
        _render_representative_reviews_tabs(result)

    _render_export_center(payload, "game_review_report.pptx")


def _merge_fresh_evaluation(stored_report: dict, fresh_report: dict) -> dict:
    merged = dict(stored_report)
    deterministic_keys = [
        "evaluation_available",
        "player_satisfaction",
        "satisfaction_score",
        "product_health",
        "health_score",
        "strength_bonus",
        "strength_sources",
        "base_score",
        "confidence_factor",
        "confidence_level",
        "confidence_reason",
        "confidence_breakdown",
        "overall_score",
        "overall_score_int",
        "grade",
        "grade_label",
        "severity_distribution",
        "raw_risk",
        "risk_ratio",
        "risk_penalty",
        "blocking_penalty",
        "s4_blocking_ratio",
        "s4_ratio",
        "s4_penalty",
        "blocking_count",
        "strength_breakdown",
        "score_breakdown",
        "category_sentiment_table",
        "top_negative_categories",
        "sentiment_conclusion",
        "analyzed_count",
        "failed_count",
    ]
    for key in deterministic_keys:
        if key in fresh_report:
            merged[key] = fresh_report[key]
    return merged


def _report_consistency_errors(payload: dict, result: AnalysisResult, prepared: dict, report: dict) -> list[str]:
    errors: list[str] = []
    classified_count = len(result.classified_reviews)
    category_total = sum(int(value) for value in result.category_counts.values())
    if category_total != classified_count:
        errors.append(f"类别统计合计 {category_total} 与分类结果数量 {classified_count} 不一致。")
    severity_total = sum(
        1
        for review in result.classified_reviews
        if getattr(review, "severity", None) in {"S1", "S2", "S3", "S4"}
    )
    if severity_total > classified_count:
        errors.append(f"严重度统计数量 {severity_total} 大于分类结果数量 {classified_count}。")
    report_count = int(report.get("analyzed_count", classified_count) or 0)
    if report_count != classified_count:
        errors.append(f"Evaluation 使用样本数 {report_count} 与分类结果数量 {classified_count} 不一致。")
    final_count = int(prepared.get("language_filtered_count", classified_count) or 0)
    failed_count = len(getattr(result, "failed_review_ids", []) or [])
    if classified_count + failed_count > final_count:
        errors.append(f"分类成功数 {classified_count} + 失败数 {failed_count} 大于最终分析样本 {final_count}。")
    target_count = int(prepared.get("target_sample_count", final_count) or 0)
    time_filtered_count = int(prepared.get("time_filtered_count", 0) or 0)
    raw_fetched_count = int(prepared.get("raw_fetched_count", prepared.get("raw_count", 0)) or 0)
    if final_count > target_count:
        errors.append(f"最终分析样本 {final_count} 大于目标分析样本 {target_count}。")
    if prepared.get("time_filter_mode") == "unlimited":
        if time_filtered_count != raw_fetched_count:
            errors.append(f"不限时间模式下时间范围内评论 {time_filtered_count} 与原始抓取评论 {raw_fetched_count} 不一致。")
    elif final_count > time_filtered_count:
        errors.append(f"最终分析样本 {final_count} 大于时间范围内评论 {time_filtered_count}。")
    if not prepared.get("time_filter_valid", True):
        errors.append("评论时间筛选结果异常，请重新分析。")
    if payload.get("record_id") and payload.get("metadata", {}).get("record_id") and payload["record_id"] != payload["metadata"]["record_id"]:
        errors.append("payload record_id 与 metadata record_id 不一致。")
    return errors


def _render_report_trace(payload: dict, prepared: dict, result: AnalysisResult, report: dict) -> None:
    severity_counts = Counter(getattr(review, "severity", None) for review in result.classified_reviews)
    rows = [
        ("record_id", str(payload.get("record_id", "未记录"))),
        ("analysis_created_at", str(payload.get("created_at") or payload.get("analysis_timestamp") or payload.get("fetch_time") or "")),
        ("package id", str(payload.get("package_name", ""))),
        ("country", str(payload.get("country", ""))),
        ("language", str(payload.get("language", ""))),
        ("time range", str(payload.get("time_display") or prepared.get("time_display") or "")),
        ("time_filter_mode", str(prepared.get("time_filter_mode", ""))),
        ("resolved_start_datetime", str(prepared.get("resolved_start_datetime", ""))),
        ("resolved_end_datetime", str(prepared.get("resolved_end_datetime", ""))),
        ("earliest_raw_review_time", str(prepared.get("earliest_raw_review_time", ""))),
        ("latest_raw_review_time", str(prepared.get("latest_raw_review_time", ""))),
        ("earliest_filtered_review_time", str(prepared.get("earliest_filtered_review_time", ""))),
        ("latest_filtered_review_time", str(prepared.get("latest_filtered_review_time", ""))),
        ("valid_datetime_count", str(prepared.get("valid_datetime_count", 0))),
        ("invalid_datetime_count", str(prepared.get("invalid_datetime_count", 0))),
        ("before_start_count", str(prepared.get("before_start_count", 0))),
        ("after_end_count", str(prepared.get("after_end_count", 0))),
        ("page_count", str(prepared.get("page_count", 0))),
        ("stop_reason", str(prepared.get("stop_reason", ""))),
        ("fetch_cache_version", str(prepared.get("fetch_cache_version", ""))),
        ("raw_fetch_count", str(prepared.get("raw_fetched_count", prepared.get("raw_count", 0)))),
        ("time_filtered_count", str(prepared.get("time_filtered_count", 0))),
        ("cleaned_count", str(prepared.get("cleaned_count", 0))),
        ("deduplicated_count", str(prepared.get("deduplicated_count", prepared.get("cleaned_count", 0)))),
        ("language_filtered_count", str(prepared.get("language_filtered_count", 0))),
        ("final_sample_count", str(prepared.get("language_filtered_count", 0))),
        ("classified_count", str(len(result.classified_reviews))),
        ("category_count_total", str(sum(int(value) for value in result.category_counts.values()))),
        ("severity_counts", ", ".join(f"{key}:{severity_counts.get(key, 0)}" for key in ["S1", "S2", "S3", "S4"])),
        ("overall_score", f"{float(report.get('overall_score', 0)):.1f}"),
    ]
    with st.expander("报告数据追踪", expanded=False):
        _render_kv_table(rows)


def _render_analysis_report(payload: dict, bar_chart_path: Path, pie_chart_path: Path, report: dict, sorted_counts: dict) -> None:
    result = payload["result"]
    prepared = payload["prepared"]

    _render_data_scope_card(payload)

    st.subheader("综合评分")
    _render_score_panel(report)

    st.subheader("整体概括")
    _render_text_panel(report["overall_summary"])
    if payload.get("summary_error"):
        st.warning(f"AI 总结生成失败，可稍后重试。原因：{payload['summary_error']}")

    st.subheader("类别统计")
    st.caption("按评论数量降序排列，零值类别置后，‘其他’固定最后。")
    total = max(sum(sorted_counts.values()), 1)
    table_rows = [
        {"Rank": index, "Category": category, "Count": count, "Percent": _format_percentage(count / total)}
        for index, (category, count) in enumerate(sorted_counts.items(), start=1)
    ]
    _render_category_table(table_rows)

    pie_col, bar_col = st.columns(2)
    with pie_col:
        st.image(str(pie_chart_path), use_container_width=True)
    with bar_col:
        st.image(str(bar_chart_path), use_container_width=True)
    st.subheader("类别分析")
    _render_structured_points(report["category_insights"])

    st.subheader("情感分布")
    _render_sentiment_cards(result.classified_reviews)
    _render_text_panel(report["sentiment_conclusion"])
    st.markdown("#### 类别 × 情感交叉统计")
    _render_category_sentiment_table(report.get("category_sentiment_table", []))

    _render_strength_pain_grid(report["strengths"], report["pain_points"])

    st.subheader("优化建议")
    _render_recommendations(report["recommendations"])
    payload["report"] = report


def _render_data_scope_card(payload: dict) -> None:
    prepared = payload.get("prepared", {})
    requested_count = int(payload.get("review_count") or prepared.get("raw_count") or 0)
    valid_count = int(prepared.get("language_filtered_count") or len(getattr(payload.get("result"), "classified_reviews", []) or []))
    timestamp = str(payload.get("analysis_timestamp") or payload.get("fetch_time") or time.strftime("%Y-%m-%d %H:%M:%S"))
    time_display = str(payload.get("time_display") or prepared.get("time_display") or "最新评论（不限制时间）").replace("～", "至")
    rows = [
        ("数据来源", "Google Play 公开评论", ""),
        ("评论排序", "最新评论（按发布时间倒序）", ""),
        ("评论时间", time_display, ""),
        ("目标分析样本", f"{requested_count} 条", ""),
        (
            "原始抓取评论",
            f"{int(prepared.get('raw_fetched_count', prepared.get('raw_count', 0)))} 条",
            "为获取时间范围内足够样本而抓取的原始评论数量",
        ),
        ("时间范围内评论", f"{int(prepared.get('time_filtered_count', prepared.get('raw_count', 0)))} 条", ""),
        (
            "最终分析样本",
            f"{valid_count} 条",
            "已排除无效评论及当前分析语言不支持的评论",
        ),
        ("抓取时间", timestamp, ""),
    ]
    items = "".join(
        (
            "<div class='mi-data-scope-row'>"
            f"<strong>{html.escape(label)}</strong>"
            f"<span>{html.escape(value)}</span>"
            + (f"<small>{html.escape(note)}</small>" if note else "")
            + "</div>"
        )
        for label, value, note in rows
    )
    st.markdown(
        f"""
        <div class='mi-data-scope-card'>
          <div class='mi-eval-title'>数据范围</div>
          <div class='mi-data-scope-grid'>{items}</div>
          <div class='mi-data-scope-note'>本报告基于指定时间范围内最新评论生成，用于反映对应版本周期玩家反馈。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _apply_single_ai_summary(result: AnalysisResult, report: dict) -> tuple[AnalysisResult, dict, str, dict]:
    summary_perf: dict = {}
    try:
        summary_model = os.getenv("CLAUDE_SUMMARY_MODEL") or os.getenv("CLAUDE_MODEL")
        payload = _build_single_summary_payload(result, report)
        payload_text = json.dumps(payload, ensure_ascii=False)
        summary_perf["summary_prompt_chars"] = len(payload_text)
        summary_perf["summary_prompt_tokens_estimate"] = _estimate_tokens(payload_text)
        summary_started = time.perf_counter()
        summary = summarize_single_market_report(payload, ClaudeClient(model=summary_model))
        summary_perf["summary_seconds"] = time.perf_counter() - summary_started
        summary_output = json.dumps(summary, ensure_ascii=False)
        summary_perf["summary_response_chars"] = len(summary_output)
        summary_perf["summary_response_tokens_estimate"] = _estimate_tokens(summary_output)
        overview = str(summary.get("overview", "")).strip()
        evidence = report.get("game_evidence", {})
        strengths = [_ground_ai_text(str(item).strip(), evidence) for item in summary.get("strengths", []) if str(item).strip()][:5]
        pain_points = [_ground_ai_text(str(item).strip(), evidence) for item in summary.get("pain_points", []) if str(item).strip()][:5]
        if overview:
            report["overall_summary"] = f"Overall Score：{float(report.get('overall_score', 0)):.1f} / 100。{_ground_ai_text(overview, evidence)}"
        if strengths:
            report["strengths"] = [{"title": _insight_title(item, "strength"), "detail": item} for item in strengths]
        if pain_points:
            report["pain_points"] = [{"title": _insight_title(item, "pain"), "detail": item} for item in pain_points]
        result = replace(
            result,
            summary_calls=1,
            most_satisfied=strengths or result.most_satisfied,
            most_unsatisfied=pain_points or result.most_unsatisfied,
        )
        return result, report, "", summary_perf
    except Exception as exc:
        summary_perf.setdefault("summary_seconds", 0.0)
        return replace(result, summary_calls=1), report, str(exc), summary_perf


def _build_single_summary_payload(result: AnalysisResult, report: dict) -> dict:
    selected = select_representative_reviews(result.classified_reviews, 5, 5)
    sentiment_counts = Counter(review.sentiment for review in result.classified_reviews)
    strength_counts = Counter(tag for review in result.classified_reviews for tag in (review.strength_tags or ()))
    evidence = report.get("game_evidence", {})
    return {
        "success_count": len(result.classified_reviews),
        "category_counts": result.category_counts,
        "sentiment_counts": dict(sentiment_counts),
        "severity_distribution": report.get("severity_distribution", {}),
        "s4_blocking_ratio": report.get("s4_blocking_ratio", 0),
        "strength_tags": dict(strength_counts.most_common(10)),
        "game_evidence": evidence,
        "category_sentiment_table": report.get("category_sentiment_table", []),
        "top_negative_categories": report.get("top_negative_categories", []),
        "representative_positive": _summary_review_payload(selected["positive"], evidence, 5),
        "representative_negative": _summary_review_payload(selected["negative"], evidence, 5),
        "evaluation": {
            "overall_score": report.get("overall_score"),
            "grade": report.get("grade"),
            "player_satisfaction": report.get("player_satisfaction"),
            "product_health": report.get("product_health"),
            "strength_bonus": report.get("strength_bonus"),
            "base_score": report.get("base_score"),
            "confidence_factor": report.get("confidence_factor"),
        },
    }


def _review_summary(review) -> dict:
    return {
        "content": review.content[:250],
        "score": getattr(review, "score", None),
        "category": review.category,
        "sentiment": review.sentiment,
        "severity": getattr(review, "severity", None),
        "is_blocking": getattr(review, "is_blocking", False),
        "strength_tags": list(getattr(review, "strength_tags", ()) or ()),
    }


def _summary_review_payload(reviews: list, evidence: dict, limit: int) -> list[dict]:
    terms = [str(item.get("term", "")).strip() for item in evidence.get("top_terms", []) if str(item.get("term", "")).strip()]

    def score(review) -> tuple[int, int]:
        content = str(getattr(review, "content", ""))
        return (1 if any(term and term in content for term in terms) else 0, min(len(content), 250))

    output = []
    seen: set[str] = set()
    for review in sorted(reviews, key=score, reverse=True):
        content = " ".join(str(getattr(review, "content", "")).split())[:250]
        key = content[:120].lower()
        if not content or key in seen:
            continue
        seen.add(key)
        output.append(_review_summary(review))
        if len(output) >= limit:
            break
    return output


def _normalize_ai_recommendations(recommendations: dict) -> dict:
    output = {}
    for level in ["P0", "P1", "P2"]:
        rows = []
        for item in recommendations.get(level, [])[:3]:
            text = str(item).strip()
            if not text:
                continue
            rows.append({"title": _short_text(text, 18), "basis": "基于本次分类统计与代表性评论。", "action": text, "impact": "提升体验稳定性与市场口碑。"})
        output[level] = rows
    return output


def _short_text(text: str, limit: int) -> str:
    return text[:limit] or "建议"


def _ground_ai_text(text: str, evidence: dict) -> str:
    terms = [str(item.get("term", "")).strip() for item in evidence.get("top_terms", [])[:3] if str(item.get("term", "")).strip()]
    if not text or not terms:
        return text
    if any(term in text for term in terms):
        return text
    if any(phrase in text for phrase in ["玩法丰富", "角色优秀", "体验良好", "优化空间较大", "整体不错"]):
        return f"{text}（需结合评论中提到的{'、'.join(terms)}核对。）"
    return f"{text}（涉及：{'、'.join(terms)}。）"


def _insight_title(text: str, kind: str) -> str:
    value = str(text)
    mappings = [
        ("角色", "角色设计"),
        ("玩法", "核心玩法"),
        ("战斗", "核心玩法"),
        ("美术", "美术表现"),
        ("画面", "美术表现"),
        ("口碑", "整体口碑"),
        ("稳定", "产品稳定性"),
        ("BUG", "产品稳定性"),
        ("崩溃", "登录闪退"),
        ("闪退", "登录闪退"),
        ("登录", "登录闪退"),
        ("抽卡", "抽卡机制"),
        ("付费", "抽卡机制"),
        ("氪金", "抽卡机制"),
        ("资源", "资源循环"),
        ("活动", "运营内容"),
        ("运营", "运营内容"),
        ("UI", "UI体验"),
        ("界面", "UI体验"),
        ("卡顿", "性能优化"),
        ("性能", "性能优化"),
    ]
    for keyword, title in mappings:
        if keyword in value:
            return title
    return "产品优势" if kind == "strength" else "痛点反馈"


def _render_data_integrity(payload: dict) -> None:
    result = payload["result"]
    prepared = payload["prepared"]
    expected = int(prepared.get("language_filtered_count", 0))
    analyzed = len(result.classified_reviews)
    failed = max(expected - analyzed, 0)
    category_total = sum(result.category_counts.values())
    sentiment_counts = {
        sentiment: sum(1 for review in result.classified_reviews if review.sentiment == sentiment)
        for sentiment in ["正面", "中性", "负面"]
    }
    sentiment_total = sum(sentiment_counts.values())
    diagnostics = getattr(result, "batch_diagnostics", None) or []
    batch_count = len(diagnostics) or ((expected + max(int(payload.get("batch_size", 0) or 1), 1) - 1) // max(int(payload.get("batch_size", 1)), 1))

    if analyzed == expected:
        st.success(f"成功分析 {analyzed} / {expected} 条评论")
    else:
        st.warning(f"成功分析 {analyzed} / {expected} 条评论，{failed} 条处理失败")

    if category_total != analyzed or sentiment_total != analyzed:
        st.error(f"数据完整性异常：类别统计合计 {category_total}，情感统计合计 {sentiment_total}，成功分析 {analyzed}。")

    st.caption(
        f"批次完成：{sum(1 for item in diagnostics if item.get('success'))}/{len(diagnostics) or batch_count} · "
        f"分类调用：{getattr(result, 'classify_calls', 0)} 次 · "
        f"总结调用：{getattr(result, 'summary_calls', 0)} 次 · "
        f"缓存：{'命中' if getattr(result, 'cache_hit', False) else '未命中'}"
    )

    if not DEBUG_MODE:
        if failed:
            st.caption(f"失败 review_id：{', '.join(str(item) for item in (getattr(result, 'failed_review_ids', []) or [])[:30])}")
        return

    with st.expander("Claude 批处理 Debug 日志", expanded=False):
        st.write("最终统计：")
        st.write(f"输入评论：{expected}")
        st.write(f"批次数：{batch_count}")
        st.write(f"Claude 总返回：{sum(int(item.get('returned_count', 0) or 0) for item in diagnostics)}")
        st.write(f"JSON 成功解析：{sum(1 for item in diagnostics if item.get('json_success'))} / {len(diagnostics)} 批")
        st.write(f"最终成功：{analyzed}")
        st.write(f"最终失败：{failed}")
        for item in diagnostics:
            st.write("==============================")
            st.write(f"Batch {item.get('batch')}")
            st.write("==============================")
            st.write("输入评论数：")
            st.write(int(item.get("input_count", 0) or 0))
            st.write("发送给 Claude 的 Prompt 长度：")
            st.write(f"{int(item.get('prompt_length', 0) or 0)} characters")
            st.write("Claude 是否正常返回：")
            st.write(bool(item.get("raw_returned")))
            st.write("Claude 返回原始文本（前1000字符）：")
            st.code(str(item.get("raw_preview") or "<无返回>")[:1000], language="text")
            st.write("JSON 是否解析成功：")
            st.write(bool(item.get("json_success")))
            st.write("解析失败原因：")
            st.write(str(item.get("error") or "无"))
            st.write("重试次数：")
            st.write(int(item.get("retry_count", 0) or 0))
            st.write("本批耗时：")
            st.write(f"{float(item.get('elapsed_seconds', 0) or 0):.2f} 秒")
            st.write("Claude 返回对象类型：")
            st.write(str(item.get("classified_reviews_type") or item.get("response_type") or "未知"))
            st.write("Claude 返回评论数量：")
            st.write(int(item.get("returned_count", 0) or 0))
            st.write("本批成功写入：")
            st.write(int(item.get("parsed_count", 0) or 0))
            st.write("累计成功：")
            cumulative = sum(int(previous.get("parsed_count", 0) or 0) for previous in diagnostics if int(previous.get("batch", 0) or 0) <= int(item.get("batch", 0) or 0))
            st.write(cumulative)
        st.write(f"所有批次合并后数量: {analyzed}")
        st.write(f"类别统计数量合计: {category_total}")
        st.write(f"情感统计数量合计: {sentiment_total}")
        st.write(f"Eval 使用评论数: {analyzed}")


def _render_performance_summary(payload: dict) -> None:
    performance = payload.get("performance", {}) or {}
    result = payload.get("result")
    diagnostics = list(getattr(result, "batch_diagnostics", None) or []) if result else []
    lines = ["===== Performance =====", ""]
    lines.append(f"Fetch: {_format_seconds(performance.get('fetch_seconds'))}")
    lines.append(f"Cleaning: {_format_seconds(performance.get('cleaning_seconds'))}")
    for index, item in enumerate(diagnostics[:4], start=1):
        lines.append(
            f"Batch{index}: {_format_seconds(item.get('total_seconds') or item.get('elapsed_seconds'))} "
            f"| prompt {int(item.get('prompt_length', 0) or 0)} chars / ~{int(item.get('prompt_tokens_estimate', 0) or 0)} tokens "
            f"| output ~{int(item.get('response_tokens_estimate', 0) or 0)} tokens "
            f"| queue {_format_seconds(item.get('queue_wait_seconds'))} "
            f"| API {item.get('api_started_at') or '--'} → {item.get('api_ended_at') or '--'} ({_format_seconds(item.get('api_elapsed_seconds'))}) "
            f"| JSON {_format_seconds(item.get('json_parse_seconds'))} "
            f"| retry sleep {_format_seconds(item.get('retry_sleep_seconds'))} "
            f"| retries {int(item.get('retry_count', 0) or 0)} "
            f"| error {item.get('error_type') or '-'}"
        )
    lines.append(
        f"Summary: {_format_seconds(performance.get('summary_seconds'))} "
        f"| prompt ~{int(performance.get('summary_prompt_tokens_estimate', 0) or 0)} tokens "
        f"| output ~{int(performance.get('summary_response_tokens_estimate', 0) or 0)} tokens"
    )
    lines.append(f"Evaluation: {_format_seconds(performance.get('evaluation_seconds'))}")
    lines.append(f"Render: {_format_seconds(performance.get('render_seconds'))}")
    lines.append("")
    analysis_total = float(performance.get("total_seconds") or payload.get("elapsed") or 0)
    render_total = float(performance.get("render_seconds") or 0)
    lines.append(f"Total: {_format_seconds(analysis_total + render_total if analysis_total else payload.get('elapsed'))}")

    prompt_tokens = sum(int(item.get("prompt_tokens_estimate", 0) or 0) for item in diagnostics)
    output_tokens = sum(int(item.get("response_tokens_estimate", 0) or 0) for item in diagnostics)
    summary_prompt_tokens = int(performance.get("summary_prompt_tokens_estimate", 0) or 0)
    summary_output_tokens = int(performance.get("summary_response_tokens_estimate", 0) or 0)
    lines.append("")
    lines.append(f"Classification prompt total: ~{prompt_tokens} tokens")
    lines.append(f"Classification output total: ~{output_tokens} tokens")
    lines.append(f"Summary prompt: ~{summary_prompt_tokens} tokens")
    lines.append(f"Summary output: ~{summary_output_tokens} tokens")
    lines.append(f"Prompt 是否比之前增加很多: {'是，Summary payload 增加了 game_evidence/category_sentiment/representative_reviews。' if summary_prompt_tokens > 1200 else '未见明显增加。'}")
    lines.append(f"Output 是否比之前增加很多: {'分类输出仍为 compact schema；Summary 输出按短 JSON 控制。' if output_tokens else '暂无输出 token 数据。'}")

    with st.expander("Performance", expanded=False):
        st.code("\n".join(lines), language="text")


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(str(text)) / 4))


def _format_seconds(value) -> str:
    try:
        return f"{float(value):.3f}s"
    except (TypeError, ValueError):
        return "--"


def _build_comparison_row(item: dict) -> dict:
    result = item["result"]
    reviews = _records_to_reviews(tuple(item["prepared"]["filtered_reviews"]))
    final_sample_count = int(item["prepared"].get("language_filtered_count", len(result.classified_reviews)) or 0)
    classified_count = len(result.classified_reviews)
    average_score = _average_score(reviews)
    sentiment_percentages = _sentiment_percentages(result.classified_reviews)
    scoring_status = item.get("scoring_status") or ("scorable" if classified_count >= MIN_SCORABLE_REVIEWS else "insufficient_sample")
    status_label = _scoring_status_label(scoring_status)
    if scoring_status == "scorable" and classified_count >= MIN_SCORABLE_REVIEWS:
        report = build_single_market_report(result, classified_count)
        score_fields = {
            "Overall Score": f"{report.get('overall_score', 0):.1f}",
            "Grade": f"{report.get('grade', '')} · {report.get('grade_label', '')}",
            "玩家满意度": f"{report.get('player_satisfaction', 0):.1f}",
            "产品健康度": f"{report.get('product_health', 0):.1f}",
            "优势加成": f"+{report.get('strength_bonus', 0):.1f}",
            "可信度": f"{report.get('confidence_level', '')} · {report.get('confidence_factor', 0):.2f}",
            "S4阻塞占比": _format_percentage(float(report.get("s4_blocking_ratio", 0))),
        }
    else:
        score_fields = {
            "Overall Score": "—",
            "Grade": "N/A",
            "玩家满意度": "--",
            "产品健康度": "--",
            "优势加成": "--",
            "可信度": "--",
            "S4阻塞占比": "--",
        }

    return {
        "市场": item["market_label"],
        "语言": item["language"],
        "有效评论数量": final_sample_count,
        "评分状态": status_label,
        "平均星级": f"{average_score:.2f}" if average_score is not None else "暂无",
        **score_fields,
        "正面占比": _format_percentage(sentiment_percentages["正面"]),
        "中性占比": _format_percentage(sentiment_percentages["中性"]),
        "负面占比": _format_percentage(sentiment_percentages["负面"]),
        "游戏玩法占比": _format_percentage(_category_percentage(result.category_counts, "游戏玩法", classified_count)),
        "BUG占比": _format_percentage(_category_percentage(result.category_counts, "BUG", classified_count)),
        "氪金占比": _format_percentage(_category_percentage(result.category_counts, "氪金", classified_count)),
        "性能问题占比": _format_percentage(_category_percentage(result.category_counts, "性能优化", classified_count)),
        "美术占比": _format_percentage(_category_percentage(result.category_counts, "美术", classified_count)),
        "整体评价占比": _format_percentage(_category_percentage(result.category_counts, "整体评价", classified_count)),
        "其他占比": _format_percentage(_category_percentage(result.category_counts, "其他", classified_count)),
    }


def _scoring_status_label(status: str) -> str:
    return {
        "scorable": "可评分",
        "no_reviews": "无公开评论",
        "request_failed": "请求失败",
        "app_unavailable": "应用未上架",
        "unsupported_language": "语言不支持",
        "time_range_empty": "时间范围无评论",
        "language_filter_empty": "语言筛选为空",
        "not_scorable": "不具备评分条件",
        "insufficient_sample": "样本不足",
    }.get(status, status or "未知")


def _valid_comparison_rows(rows: list[dict]) -> list[dict]:
    return [row for row in rows if str(row.get("Overall Score", "")).replace(".", "", 1).isdigit()]


def _build_summary_payload(item: dict, row: dict) -> dict:
    result = item["result"]
    return {
        "market": row["市场"],
        "language": row["语言"],
        "metrics": row,
        "top_categories": sort_category_counts(result.category_counts),
        "most_satisfied": result.most_satisfied,
        "most_unsatisfied": result.most_unsatisfied,
        "summary": result.summary,
        "representative_reviews": [
            {"content": review.content, "category": review.category, "sentiment": review.sentiment, "reason": review.reason}
            for review in result.classified_reviews[:3]
        ],
    }


def _render_market_comparison(
    rows: list[dict],
    market_results: list[dict],
    comparison_summary: str,
    package_name: str,
    analysis_level: str,
    country_details: list[dict] | None = None,
) -> None:
    payload = {
        "type": "market",
        "package_name": package_name,
        "analysis_level": analysis_level,
        "rows": rows,
        "market_results": market_results,
        "comparison_summary": comparison_summary,
        "country_details": country_details,
    }
    _render_market_comparison_saved(payload, {"theme_mode": theme.resolve_theme_mode(st.session_state.get("theme_choice", "跟随系统"))})


def _render_market_comparison_saved(payload: dict, config: dict) -> None:
    rows = payload["rows"]
    market_results = payload["market_results"]
    comparison_summary = payload["comparison_summary"]
    analysis_level = payload["analysis_level"]
    country_details = payload.get("country_details")
    entity_name = "区域" if analysis_level == "区域对比" else "市场"
    st.markdown("<div id='market-insight-report'></div>", unsafe_allow_html=True)
    st.subheader("Overall Insight")
    if any(item["prepared"].get("language_filter_mode") == LANGUAGE_FILTER_NONE for item in market_results):
        st.info("当前部分或全部市场未限制评论语言，分析将包含对应商店地区返回的所有语言评论。")
    invalid_rows = [row for row in rows if row.get("评分状态") != "可评分"]
    if invalid_rows:
        st.warning("部分市场无数据或样本不足，已从评分排序、平均分、图表和高低分结论中排除。")
        for row in invalid_rows:
            st.caption(f"{row.get('市场')}：{row.get('评分状态')}，有效样本 {row.get('有效评论数量')} 条。")
    valid_rows = _valid_comparison_rows(rows)
    _render_overall_insight(valid_rows, comparison_summary)

    st.subheader(f"{entity_name}核心指标")
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        current_theme_mode = config.get("theme_mode", "light")
        chart_payload = {**payload, "rows": valid_rows}
        negative_chart, category_chart, monetization_chart, average_score_chart = _create_market_charts_for_payload(
            chart_payload,
            temp_path,
            theme_mode=current_theme_mode,
        )

        st.subheader(f"{entity_name}对比图")
        if valid_rows:
            st.image(str(negative_chart), use_container_width=True)
            _render_ai_insight("负面率洞察", _market_metric_insights(valid_rows, "负面占比", "负面反馈"))
            st.image(str(category_chart), use_container_width=True)
            _render_ai_insight("主要问题类别洞察", _market_category_insights(valid_rows))
            st.image(str(monetization_chart), use_container_width=True)
            _render_ai_insight("商业化风险洞察", _market_metric_insights(valid_rows, "氪金占比", "氪金争议"))
            if analysis_level == "区域对比":
                st.image(str(average_score_chart), use_container_width=True)
                _render_ai_insight("评分差异洞察", _score_insights(valid_rows))
        else:
            st.info("暂无满足最低样本阈值的市场，暂不生成对比图。")

        st.subheader("Claude 中文跨市场总结")
        _render_text_panel(comparison_summary or "暂无总结")

        st.subheader("代表性评论")
        for item in market_results:
            st.markdown(f"**{item['country_label']} ({item['language']})**")
            representatives = item["result"].classified_reviews[:3]
            if not representatives:
                _render_report_list([], "暂无有效评论")
                continue
            _render_review_cards(representatives)

        if country_details:
            st.subheader("国家级明细")
            for region in COUNTRY_GROUPS:
                details = [item for item in country_details if item["region"] == region]
                if not details:
                    continue
                with st.expander(f"{region} 国家级明细"):
                    detail_rows = [_build_comparison_row(item) for item in details]
                    st.dataframe(pd.DataFrame(detail_rows), use_container_width=True)

        _render_export_center(payload, "market_comparison_report.pptx")


def _create_market_charts_for_payload(payload: dict, temp_path: Path, theme_mode: str) -> list[Path]:
    rows = payload["rows"]
    entity_name = "Region" if payload["analysis_level"] == "区域对比" else "Market"
    negative_chart = create_market_bar_chart(rows, "负面占比", f"Negative Reviews by {entity_name}", temp_path / "negative.png", theme_mode=theme_mode)
    category_chart = create_market_category_distribution_chart(rows, temp_path / "category_distribution.png", theme_mode=theme_mode)
    monetization_chart = create_market_bar_chart(rows, "氪金占比", f"Monetization Issues by {entity_name}", temp_path / "monetization.png", theme_mode=theme_mode)
    average_score_chart = create_market_bar_chart(
        rows,
        "平均星级",
        f"Average Rating by {entity_name}",
        temp_path / "average_score.png",
        y_label="Average Rating",
        value_suffix="",
        theme_mode=theme_mode,
    )
    return [negative_chart, category_chart, monetization_chart, average_score_chart]


def _render_ai_insight(title: str, insights: list[str]) -> None:
    items = "".join(f"<li>{html.escape(str(item))}</li>" for item in insights[:3])
    st.markdown(
        f"""
        <div class="mi-insight">
          <strong>{title}</strong>
          <ul style="margin: 6px 0 0 18px; padding: 0;">{items}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_text_panel(text: str) -> None:
    st.markdown(
        f"<div class='mi-report-item'><strong>AI Summary</strong><small>{html.escape(str(text))}</small></div>",
        unsafe_allow_html=True,
    )


def _render_score_panel(report: dict) -> None:
    available = bool(report.get("evaluation_available", True))
    score = float(report.get("overall_score", 0))
    grade = str(report.get("grade", "暂无"))
    grade_label = str(report.get("grade_label", ""))
    summary = str(report.get("evaluation_summary") or report.get("score_reason") or "暂无评分总结")
    metric_cards = [
        ("玩家满意度", f"{float(report.get('player_satisfaction', 0)):.0f}", ""),
        ("产品健康度", f"{float(report.get('product_health', 0)):.0f}", ""),
        ("产品优势加成", f"+{float(report.get('strength_bonus', 0)):.1f}", ""),
        ("基础分", f"{float(report.get('base_score', 0)):.1f}", ""),
        ("结果可信度", f"{float(report.get('confidence_factor', 0)):.2f}", html.escape(str(report.get("confidence_level", "")))),
    ]
    metric_html = "".join(
        f"<div class='mi-eval-metric'><strong>{html.escape(label)}</strong><b>{html.escape(value)}</b><small>{note}</small></div>"
        for label, value, note in metric_cards
    )
    severity = report.get("severity_distribution", {}) or {}
    severity_html = "".join(
        f"<div class='mi-eval-metric'><strong>{key} {label}</strong><b>{int(severity.get(key, 0))}</b></div>"
        for key, label in [("S1", "轻微"), ("S2", "中等"), ("S3", "严重"), ("S4", "阻塞")]
    )
    score_html = f"{score:.1f} <small>/ 100</small>" if available else "需重新分析"
    grade_html = f"{html.escape(grade)} · {html.escape(grade_label)}" if available else "旧版标注不可用"
    st.markdown(
        f"""
        <div class='mi-eval-panel'>
          <div class='mi-eval-head'>
            <div>
              <div class='mi-eval-title'>GamePulse AI 综合评分</div>
              <div class='mi-muted' style='font-size:12px; margin:4px 0 8px;'>Evaluation Framework {FRAMEWORK_VERSION}</div>
              <div class='mi-eval-score'>{score_html}</div>
            </div>
            <div><div class='mi-eval-title'>Grade</div><div class='mi-eval-grade'>{grade_html}</div></div>
          </div>
          <div class='mi-eval-grid'>{metric_html}</div>
          <div class='mi-muted' style='margin:12px 0 6px;'>严重度分布</div>
          <div class='mi-eval-grid'>{severity_html}</div>
          <div class='mi-eval-summary'>{html.escape(summary)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not available:
        st.warning("该分析使用旧版标注，需重新运行分析后才能生成 v2.0 评分。")
    pdf_bytes = b""
    pdf_error = ""
    try:
        pdf_bytes = _get_evaluation_framework_pdf_bytes()
        if not pdf_bytes:
            pdf_error = "PDF 生成结果为空。"
    except Exception as exc:
        pdf_error = str(exc)

    st.caption("Evaluation Framework v2.0 PDF ready" if pdf_bytes and not pdf_error else "Evaluation PDF unavailable")
    cols = st.columns(2)
    with cols[0]:
        if st.button("查看评分体系", key="evaluation_framework_button", use_container_width=False):
            _render_evaluation_framework_dialog(report)
    with cols[1]:
        if pdf_bytes and not pdf_error:
            st.download_button(
                "下载 Evaluation Framework v2.0",
                data=pdf_bytes,
                file_name=PDF_FILENAME,
                mime="application/pdf",
                use_container_width=False,
            )
        else:
            st.button("下载 Evaluation Framework v2.0", disabled=True, use_container_width=False)
    if pdf_error:
        st.error(f"评分体系 PDF 生成失败：{pdf_error}")


@st.dialog("GamePulse AI Evaluation Framework", width="large")
def _render_evaluation_framework_dialog(report: dict) -> None:
    st.caption(f"{FRAMEWORK_NAME} {FRAMEWORK_VERSION} · Designed & Developed by Yihan Yao")
    try:
        st.download_button(
            "下载完整 Evaluation Framework v2.0",
            data=_get_evaluation_framework_pdf_bytes(),
            file_name=PDF_FILENAME,
            mime="application/pdf",
            use_container_width=True,
        )
    except Exception as exc:
        st.error(f"评分体系 PDF 读取失败：{exc}")
    st.subheader("评分组成")
    _render_report_list(
        [
            "AI 只负责评论分类、情感判断、S1–S4 严重度标注、阻塞标记和优势信号识别。",
            "最终 Overall Score 由 Python 固定公式计算，Claude 不直接生成总分。",
            "Base Score = 55% × 玩家满意度 + 45% × 产品健康度 + 产品优势加成（最高 +5）。",
            "Overall Score = Base Score × 结果可信度系数，可信度系数范围为 0.70–1.00。",
        ],
        "暂无评分说明",
    )
    _render_evaluation_breakdown(report)
    st.subheader("核心指标")
    _render_kv_table([
        ("玩家满意度", "根据正面、中性、负面比例确定性计算；中性评论计为部分正向。"),
        ("产品健康度", "基于风险评论逐条 S1–S4 严重度、阻塞标记和样本占比计算，健康度越高代表体验越稳定。"),
        ("产品优势加成", "只来自具体正面优势信号，最高 +5 分，不能抵消严重阻塞风险。"),
        ("结果可信度", "作为最终折扣系数，而不是普通加权维度；当前依据样本量、分类成功率和泛化评论占比。"),
    ])
    st.subheader("产品健康度")
    _render_report_list(
        [
            f"风险类别包括 BUG、性能优化、UI体验、氪金、新手引导等；严重度权重为 {SEVERITY_WEIGHTS}。",
            f"风险扣分 = Σ(严重度评论数 × 权重) / 有效评论数 × {HEALTH_RISK_NORMALIZATION_FACTOR:.1f}。",
            "S4 采用连续扣分：min(15, S4占比 × 200)；存在阻塞标记时阻塞扣分最低为 3 分。",
            "健康度标准化系数目前为初始经验参数，尚未经过历史数据校准。",
        ],
        "暂无说明",
    )
    st.subheader("严重度标准")
    _render_method_table(
        [
            {"等级": "S1", "说明": "轻微，影响体验但不影响核心功能", "权重": "1"},
            {"等级": "S2", "说明": "中等，造成明显不便但存在绕过方法", "权重": "3"},
            {"等级": "S3", "说明": "严重，影响核心玩法体验且难以绕过", "权重": "7"},
            {"等级": "S4", "说明": "阻塞，导致闪退、无法登录、数据丢失或核心功能失效", "权重": "15"},
        ],
        ["等级", "说明", "权重"],
    )
    st.subheader("评分等级")
    _render_method_table(
        [
            {"分数": "90~100", "等级": "S", "说明": "优秀"},
            {"分数": "80~89", "等级": "A", "说明": "良好"},
            {"分数": "70~79", "等级": "B", "说明": "中上"},
            {"分数": "60~69", "等级": "C", "说明": "一般"},
            {"分数": "<60", "等级": "D", "说明": "需重点优化"},
        ],
        ["分数", "等级", "说明"],
    )


def _render_evaluation_breakdown(report: dict) -> None:
    if not report.get("evaluation_available", True):
        st.warning("该分析缺少 v2.0 标注字段，需重新运行分析后才能展示本次评分拆解。")
        return
    breakdown = report.get("score_breakdown", {})
    rows = [
        f"<div class='mi-eval-row'><strong>玩家满意度</strong><span>{float(report.get('player_satisfaction', 0)):.1f}</span><span>× {SATISFACTION_WEIGHT * 100:.0f}%</span><b>= {float(breakdown.get('player_satisfaction', 0)):.1f}</b></div>",
        f"<div class='mi-eval-row'><strong>产品健康度</strong><span>{float(report.get('product_health', 0)):.1f}</span><span>× {HEALTH_WEIGHT * 100:.0f}%</span><b>= {float(breakdown.get('product_health', 0)):.1f}</b></div>",
        f"<div class='mi-eval-row'><strong>产品优势加成</strong><span></span><span>最高 +{STRENGTH_BONUS_MAX:.0f}</span><b>+ {float(report.get('strength_bonus', 0)):.1f}</b></div>",
        f"<div class='mi-eval-row'><strong>Base Score</strong><span></span><span></span><b>{float(report.get('base_score', 0)):.1f}</b></div>",
        f"<div class='mi-eval-row'><strong>结果可信度系数</strong><span></span><span>× {float(report.get('confidence_factor', 0)):.2f}</span><b>{html.escape(str(report.get('confidence_level', '')))}</b></div>",
        f"<div class='mi-eval-row'><strong>Overall Score</strong><span></span><span></span><b>{float(report.get('overall_score', 0)):.1f}</b></div>",
    ]
    st.markdown(f"<div class='mi-eval-breakdown'>{''.join(rows)}</div>", unsafe_allow_html=True)
    strength_breakdown = report.get("strength_breakdown", {})
    confidence_breakdown = report.get("confidence_breakdown", {})
    _render_kv_table([
        ("优势覆盖度", f"{float(strength_breakdown.get('coverage', 0)):.2f} / 2.00"),
        ("优势多样性", f"{float(strength_breakdown.get('diversity', 0)):.2f} / 1.50"),
        ("优势证据集中度", f"{float(strength_breakdown.get('evidence', 0)):.2f} / 1.50"),
        ("样本量得分", f"{float(confidence_breakdown.get('sample_factor', 0)):.2f}"),
        ("分类成功率", f"{float(confidence_breakdown.get('success_factor', 0)):.1%}"),
        ("泛化评论占比", f"{float(confidence_breakdown.get('generic_review_ratio', 0)):.1%}"),
    ])


def _render_category_table(rows: list[dict]) -> None:
    body = "".join(
        "<tr>"
        f"<td>{row['Rank']}</td>"
        f"<td>{html.escape(str(row['Category']))}</td>"
        f"<td>{row['Count']}</td>"
        f"<td>{html.escape(str(row['Percent']))}</td>"
        "</tr>"
        for row in rows
    )
    st.markdown(
        f"""
        <div class="mi-table-wrap">
          <table class="mi-data-table">
            <thead><tr><th>Rank</th><th>Category</th><th>Count</th><th>Percent</th></tr></thead>
            <tbody>{body}</tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_category_sentiment_table(rows: list[dict]) -> None:
    if not rows:
        _render_report_list([], "暂无类别情感交叉数据")
        return
    safe_rows = []
    for row in rows:
        safe_rows.append({
            "类别": row.get("类别", ""),
            "正面": row.get("正面", 0),
            "中性": row.get("中性", 0),
            "负面": row.get("负面", 0),
            "合计": row.get("合计", 0),
            "负面率": row.get("负面率", "0.0%"),
        })
    _render_method_table(safe_rows, ["类别", "正面", "中性", "负面", "合计", "负面率"])


def _render_structured_points(points: list[dict]) -> None:
    if not points:
        _render_report_list([], "暂无足够信息")
        return
    cards = "".join(
        "<div class='mi-report-item'>"
        f"<strong>{html.escape(str(item.get('title', '要点')))}</strong>"
        f"<small>{html.escape(str(item.get('detail', '暂无说明')))}</small>"
        "</div>"
        for item in points[:6]
    )
    st.markdown(f"<div class='mi-report-list'>{cards}</div>", unsafe_allow_html=True)


def _render_strength_pain_grid(strengths: list[dict], pain_points: list[dict]) -> None:
    def column(title: str, points: list[dict]) -> str:
        items = points or [{"title": "暂无足够信息", "detail": "暂无足够信息"}]
        cards = "".join(
            "<div class='mi-report-item'>"
            f"<strong>{html.escape(str(item.get('title', '要点')))}</strong>"
            f"<small>{html.escape(str(item.get('detail', '暂无说明')))}</small>"
            "</div>"
            for item in items[:6]
        )
        return (
            "<section class='insight-column'>"
            f"<h3>{html.escape(title)}</h3>"
            f"<div class='mi-report-list'>{cards}</div>"
            "</section>"
        )

    st.markdown(
        "<div class='insight-grid'>"
        + column("玩家认可的优点", strengths)
        + column("主要痛点", pain_points)
        + "</div>",
        unsafe_allow_html=True,
    )


def _render_recommendations(recommendations: dict) -> None:
    labels = {"P0": "P0 立即处理", "P1": "P1 近期优化", "P2": "P2 长期建设"}
    sections = []
    for level in ["P0", "P1", "P2"]:
        cards = []
        for item in recommendations.get(level, [])[:3]:
            cards.append(
                "<article class='recommendation-card'>"
                f"<h4>{html.escape(str(item.get('title', '建议')))}</h4>"
                f"<p><strong>依据：</strong>{html.escape(str(item.get('basis', '暂无')))}</p>"
                f"<p><strong>动作：</strong>{html.escape(str(item.get('action', '暂无')))}</p>"
                f"<p><strong>预期收益：</strong>{html.escape(str(item.get('impact', '暂无')))}</p>"
                "</article>"
            )
        if not cards:
            cards.append("<article class='recommendation-card'><p>暂无建议</p></article>")
        sections.append(
            "<section class='recommendation-section'>"
            f"<h3 class='priority-section-title'>{html.escape(labels[level])}</h3>"
            f"<div class='recommendation-grid'>{''.join(cards)}</div>"
            "</section>"
        )
    st.markdown("".join(sections), unsafe_allow_html=True)


def _render_report_list(items: list[str], empty_text: str) -> None:
    if not items:
        items = [empty_text]
    cards = "".join(
        f"<div class='mi-report-item'><strong>{index:02d}</strong><small>{html.escape(str(item))}</small></div>"
        for index, item in enumerate(items[:5], start=1)
    )
    st.markdown(f"<div class='mi-report-list'>{cards}</div>", unsafe_allow_html=True)


def _render_sentiment_cards(classified_reviews) -> None:
    percentages = _sentiment_percentages(classified_reviews)
    total = len(classified_reviews)
    cards = []
    for sentiment in ["正面", "中性", "负面"]:
        count = sum(1 for review in classified_reviews if _normalize_sentiment_display(review.sentiment) == sentiment)
        cards.append(
            f"<div class='mi-sentiment-card'><b>{sentiment}</b><span>{_format_percentage(percentages[sentiment])}</span><small>{count} / {total} 条</small></div>"
        )
    st.markdown(f"<div class='mi-sentiment-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)


def _render_pain_points(result) -> None:
    if result.most_unsatisfied:
        _render_report_list(result.most_unsatisfied[:5], "当前样本未识别出集中痛点")
        return
    sorted_counts = sort_category_counts(result.category_counts)
    pain_rows = [
        f"{category}：{count} 条相关评论，建议结合代表性评论进一步确认具体问题。"
        for category, count in sorted_counts.items()
        if count > 0 and category not in {"整体评价", "其他"}
    ]
    _render_report_list(pain_rows[:5], "当前样本未识别出集中痛点")


def _render_review_cards(reviews, show_negative_fields: bool = False) -> None:
    if not reviews:
        _render_report_list([], "暂无代表性评论")
        return
    cards = []
    for index, review in enumerate(reviews, start=1):
        meta = [
            f"星级：{getattr(review, 'score', '暂无') or '暂无'}",
            f"类别：{review.category}",
            f"情感：{review.sentiment}",
            f"国家：{getattr(review, 'country', '') or '暂无'}",
            f"版本：{getattr(review, 'version', '') or '暂无'}",
            f"日期：{getattr(review, 'date', '') or '暂无'}",
        ]
        if show_negative_fields:
            meta.append(f"严重度：{getattr(review, 'severity', None) or '无'}")
            if getattr(review, "is_blocking", False):
                meta.append("阻塞问题：是")
        else:
            tags = "、".join(getattr(review, "strength_tags", ()) or ()) or "无"
            meta.append(f"优势标签：{tags}")
        cards.append(
            "<div class='mi-report-item'>"
            f"<strong>{index:02d} · {html.escape(review.category)} · {html.escape(review.sentiment)}</strong>"
            f"<small>{html.escape(' | '.join(meta))}</small>"
            f"<small>原文：{html.escape(review.content)}</small>"
            f"<small>中文概括：{html.escape(_review_chinese_summary(review))}</small>"
            "</div>"
        )
    st.markdown(f"<div class='mi-report-list'>{''.join(cards)}</div>", unsafe_allow_html=True)


def _review_chinese_summary(review) -> str:
    sentiment = _normalize_sentiment_display(getattr(review, "sentiment", "中性"))
    category = getattr(review, "category", "其他") or "其他"
    severity = getattr(review, "severity", None)
    is_blocking = bool(getattr(review, "is_blocking", False))
    tags = [str(tag) for tag in (getattr(review, "strength_tags", ()) or ()) if str(tag)]
    if sentiment == "正面":
        if tags:
            return f"该评论整体为正面，主要认可{category}，具体优势信号包括：{'、'.join(tags)}。"
        return f"该评论整体为正面，主要认可{category}相关体验。"
    if sentiment == "负面":
        severity_text = f"，严重度为{severity}" if severity else ""
        blocking_text = "，且属于阻塞核心流程的问题" if is_blocking else ""
        return f"该评论整体为负面，主要反馈{category}问题{severity_text}{blocking_text}。"
    return f"该评论情感偏中性，主要围绕{category}提供反馈，未表现出强烈正面或负面态度。"


def _render_representative_reviews_tabs(result) -> None:
    selected = select_representative_reviews(result.classified_reviews)
    st.subheader("Representative Reviews")
    pos_tab, neg_tab = st.tabs(["👍 Positive Reviews", "👎 Negative Reviews"])
    with pos_tab:
        _render_review_cards(selected["positive"], show_negative_fields=False)
    with neg_tab:
        _render_review_cards(selected["negative"], show_negative_fields=True)
    with st.expander("Show All Reviews", expanded=False):
        _render_review_cards(result.classified_reviews[:100], show_negative_fields=True)


def _render_methodology_entry() -> None:
    left, right = st.columns([1, 0.22])
    is_running = bool(st.session_state.get(ANALYSIS_RUNNING_KEY, False))
    with right:
        button_key = "methodology_dialog_button_running" if is_running else "methodology_dialog_button"
        if st.button("📖 分析方法说明", key=button_key, use_container_width=True, disabled=is_running):
            _render_methodology_dialog()
        if is_running:
            st.caption("分析运行中，完成后可查看。")


@st.dialog("分析方法（Analysis Methodology）", width="large")
def _render_methodology_dialog() -> None:
    _render_methodology_page()


def _render_methodology_page() -> None:
    st.markdown("### 分析方法（Analysis Methodology）")
    st.caption("说明 GamePulse AI 的数据处理流程、AI 标注方法和 v2.0 确定性评分规则。")
    try:
        pdf_bytes = _get_evaluation_framework_pdf_bytes()
        st.download_button(
            "下载完整评分体系 PDF",
            data=pdf_bytes,
            file_name=PDF_FILENAME,
            mime="application/pdf",
            use_container_width=True,
        )
    except Exception as exc:
        st.error(f"评分体系 PDF 生成失败：{exc}")

    st.subheader("分析流程")
    steps = [
        ("01", "评论抓取", "按应用包名、Google Play 商店地区和评论语言请求公开评论。"),
        ("02", "数据清洗", "删除空内容、过短文本和重复正文，保留可用评分、日期和版本字段。"),
        ("03", "评论分类", "为每条评论选择一个最主要类别，并输出中文概括和判断原因。"),
        ("04", "情感分析", "根据评论正文语义判断正面、中性或负面。"),
        ("05", "AI 严重度标注", "风险类别输出 S1–S4 严重度，并标记是否阻塞核心流程。"),
        ("06", "确定性评分引擎", "Python 按 v2.0 固定公式计算 Base Score 和 Overall Score。"),
    ]
    _render_step_cards(steps)

    left, right = st.columns([1, 1])
    with left:
        st.subheader("评论分类说明")
        _render_kv_table(category_standards())

    with right:
        st.subheader("GamePulse AI 综合评分")
        _render_report_list(score_formula_text(), "暂无评分说明")
        _render_kv_table([
            ("玩家满意度", "55% 权重；根据正面、中性、负面评论比例计算，中性计为部分正向。"),
            ("产品健康度", "45% 权重；根据风险类别的 S1–S4 严重度、问题频率和连续 S4/阻塞扣分计算。"),
            ("产品优势加成", "最高 +5 分；由优势覆盖度、多样性和证据集中度确定，只来自具体正向优势信号。"),
            ("结果可信度", "0.70–1.00 折扣系数；由样本量、分类成功率和泛化评论占比计算。"),
            ("综合评分公式", "Base Score = 0.55 × 玩家满意度 + 0.45 × 产品健康度 + 优势加成；Overall Score = Base Score × 可信度系数。"),
            ("评分范围", "0–100 分。"),
            ("等级", "90–100：S 优秀；80–89：A 良好；70–79：B 中上；60–69：C 一般；低于 60：D 需重点优化。"),
        ])
        st.subheader("严重度标准")
        _render_kv_table(severity_standards())

    st.subheader("情感分析标准")
    _render_kv_table(sentiment_standards())
    st.caption("情感由 Claude 根据评论正文语义判断；当前星级评分不参与情感分类。")

    st.warning("数据局限性：" + "；".join(evaluation_limitations()))


def _render_step_cards(steps: list[tuple[str, str, str]]) -> None:
    cards = "".join(
        "<div class='mi-report-item'>"
        f"<strong>{html.escape(number)} · {html.escape(title)}</strong>"
        f"<small>{html.escape(detail)}</small>"
        "</div>"
        for number, title, detail in steps
    )
    st.markdown(f"<div class='mi-method-steps'>{cards}</div>", unsafe_allow_html=True)


def _render_report_cards(steps: list[tuple[str, str, str]]) -> None:
    cards = "".join(
        "<div class='mi-report-item'>"
        f"<strong>{html.escape(step)} · {html.escape(title)}</strong>"
        f"<small>{html.escape(detail)}</small>"
        "</div>"
        for step, title, detail in steps
    )
    st.markdown(f"<div class='mi-report-list'>{cards}</div>", unsafe_allow_html=True)


def _render_methodology(payload: dict, report: dict) -> None:
    prepared = payload["prepared"]
    st.subheader("数据来源")
    source_rows = [
        ("应用包名", payload["package_name"]),
        ("Google Play 商店地区", payload.get("scope", payload.get("country", "未知"))),
        ("评论语言", _language_display(payload.get("language", ""))),
        ("请求评论数量", str(payload.get("review_count", ""))),
        ("实际抓取数量", str(prepared.get("raw_count", 0))),
        ("抓取时间", payload.get("fetch_time", "未知")),
    ]
    _render_kv_table(source_rows)
    st.caption("评论通过 google-play-scraper，根据应用包名、Google Play 商店地区和评论语言参数请求评论。商店地区不代表评论者真实国籍或 IP；分析结果仅代表本次抓取样本。")

    st.subheader("数据清洗流程")
    _render_method_table(cleaning_steps(prepared), ["处理步骤", "规则", "删除数量", "保留数量"])

    st.subheader("类别分类标准")
    _render_kv_table(category_standards())
    st.caption("当前实现为单标签分类：系统为每条评论选择最主要的问题类别；“其他”仅用于无法明确判断的评论。")

    st.subheader("情感判断标准")
    _render_kv_table(sentiment_standards())
    st.caption("情感由 Claude 根据评论正文语义判断；当前星级评分不参与情感分类。每条评论保存 reason 作为中文判定说明。")

    st.subheader("综合评分说明")
    _render_report_list(score_formula_text(), "暂无评分说明")
    _render_kv_table([
        ("Overall Score", f"{report.get('overall_score', 0):.1f} / 100"),
        ("玩家满意度", f"{report.get('player_satisfaction', 0):.1f}"),
        ("产品健康度", f"{report.get('product_health', 0):.1f}"),
        ("产品优势加成", f"+{report.get('strength_bonus', 0):.1f}"),
        ("Base Score", f"{report.get('base_score', 0):.1f}"),
        ("结果可信度系数", f"{report.get('confidence_factor', 0):.2f} · {report.get('confidence_level', '')}"),
    ])
    st.subheader("严重度标准")
    _render_kv_table(severity_standards())
    st.caption("Overall Score 基于 GamePulse AI Evaluation Framework v2.0 生成，不等同于 Google Play 官方星级或商业表现。")
    st.warning("数据局限性：" + "；".join(evaluation_limitations()))


def _render_kv_table(rows: list[tuple[str, str]]) -> None:
    table_rows = [{"项目": key, "说明": value} for key, value in rows]
    _render_method_table(table_rows, ["项目", "说明"])


def _render_method_table(rows: list[dict], columns: list[str]) -> None:
    head = "".join(f"<th>{html.escape(column)}</th>" for column in columns)
    body = ""
    for row in rows:
        body += "<tr>" + "".join(f"<td>{html.escape(str(row.get(column, '')))}</td>" for column in columns) + "</tr>"
    st.markdown(
        f"<div class='mi-table-wrap'><table class='mi-data-table'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _render_overall_insight(rows: list[dict], summary: str) -> None:
    summary_points = _summary_points(summary, 4)
    cols = st.columns(3)
    with cols[0]:
        _render_ai_insight("共同优点", summary_points[:2] or ["正向反馈集中在核心体验与内容吸引力。"])
    with cols[1]:
        _render_ai_insight("共同问题", _market_category_insights(rows)[:2])
    with cols[2]:
        _render_ai_insight("机会与风险", _market_metric_insights(rows, "氪金占比", "商业化风险")[:2])


def _render_export_center(payload: dict, ppt_filename: str) -> None:
    st.markdown("<div class='mi-export'><strong>Export Center</strong><div class='mi-muted'>当前支持专业 PPT，已预留多格式报告导出能力。</div></div>", unsafe_allow_html=True)
    record_id = str(payload.get("record_id") or payload.get("metadata", {}).get("record_id") or "current")
    cols = st.columns(5)
    with cols[0]:
        if st.button("生成报告", type="primary", use_container_width=True, key=f"generate_report_{record_id}"):
            try:
                current_state = session_manager.get_analysis()
                source_payload = current_state["payload"] if current_state and current_state.get("payload") else payload
                export_payload = copy.deepcopy(source_payload)
                before_record_id = str(source_payload.get("record_id") or source_payload.get("metadata", {}).get("record_id") or record_id)
                before_score = _payload_overall_score(source_payload)
                before_final_count = _payload_final_sample_count(source_payload)
                with st.spinner("正在生成 PPT 报告..."):
                    ppt_bytes = _generate_ppt_bytes(export_payload, ppt_filename)
                session_manager.save_ppt(ppt_filename, ppt_bytes)
                session_manager.save_export(before_record_id, "pptx", ppt_filename, ppt_bytes)
                after_state = session_manager.get_analysis()
                after_payload = after_state["payload"] if after_state and after_state.get("payload") else {}
                if (
                    str(after_payload.get("record_id") or after_payload.get("metadata", {}).get("record_id") or before_record_id) != before_record_id
                    or _payload_overall_score(after_payload) != before_score
                    or _payload_final_sample_count(after_payload) != before_final_count
                ):
                    st.error("报告生成后检测到当前分析状态变化，请重新选择历史记录或重新分析。")
                    return
                st.success("PPT 报告生成完成，分析结果已保留。")
            except Exception as exc:
                st.error(f"报告生成失败，当前分析结果已保留，请重试。原因：{exc}")
    for label, col in zip(["PDF", "Excel", "CSV", "JSON"], cols[1:]):
        with col:
            st.button(label, disabled=True, use_container_width=True, help="预留导出格式，后续可扩展。", key=f"export_placeholder_{label}_{record_id}")
    ppt_state = session_manager.get_export(record_id, "pptx") or session_manager.get_ppt()
    if ppt_state:
        st.download_button(
            "下载 PPT",
            data=ppt_state["data"],
            file_name=ppt_state["filename"],
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            use_container_width=True,
            key=f"download_ppt_{record_id}",
        )


def _payload_overall_score(payload: dict) -> float | None:
    try:
        return float((payload.get("report") or {}).get("overall_score"))
    except (TypeError, ValueError):
        return None


def _payload_final_sample_count(payload: dict) -> int:
    try:
        return int((payload.get("prepared") or {}).get("language_filtered_count", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _generate_ppt_bytes(payload: dict, filename: str) -> bytes:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        output_path = temp_path / filename
        if payload["type"] == "single":
            result = payload["result"]
            sorted_counts = sort_category_counts(result.category_counts)
            bar_chart_path = create_bar_chart(sorted_counts, temp_path / "category_bar.png", theme_mode="light")
            pie_chart_path = create_pie_chart(sorted_counts, temp_path / "category_pie.png", theme_mode="light")
            ppt_path = export_ppt(
                result,
                payload["package_name"],
                bar_chart_path,
                pie_chart_path,
                output_path,
                report=payload.get("report"),
                context=_ppt_single_context(payload),
            )
        else:
            chart_paths = _create_market_charts_for_payload(payload, temp_path, theme_mode="light")
            ppt_path = export_market_comparison_ppt(
                payload["package_name"],
                payload["rows"],
                payload["comparison_summary"],
                chart_paths,
                output_path,
                market_results=payload["market_results"],
            )
        return ppt_path.read_bytes()


def _ppt_single_context(payload: dict) -> dict:
    return {
        "game_title": payload.get("game_name") or payload.get("metadata", {}).get("game_name") or payload.get("package_name", ""),
        "package_name": payload.get("package_name", ""),
        "market": payload.get("scope") or payload.get("country", "当前市场"),
        "language": _language_display(str(payload.get("language", ""))),
        "time_range": payload.get("time_display") or payload.get("time_mode") or "未记录",
        "analysis_time": payload.get("analysis_timestamp") or payload.get("fetch_time") or "",
    }


def _single_market_insights(result) -> list[str]:
    sorted_counts = sort_category_counts(result.category_counts)
    top_category, top_count = next(iter(sorted_counts.items()), ("暂无", 0))
    total = max(sum(sorted_counts.values()), 1)
    return [
        f"玩家反馈最集中在「{top_category}」，占比约 {_format_percentage(top_count / total)}。",
        "该类别可作为产品、运营和发行复盘的优先观察方向。",
        "建议结合代表性评论判断是短期版本问题还是长期体验问题。",
    ]


def _category_chart_insights(result) -> list[str]:
    sorted_counts = sort_category_counts(result.category_counts)
    non_zero = [(category, count) for category, count in sorted_counts.items() if count > 0]
    if not non_zero:
        return ["暂无足够样本形成类别洞察。"]
    top = non_zero[0][0]
    bug_count = result.category_counts.get("BUG", 0)
    return [
        f"Top Category 为「{top}」，说明该维度最影响当前样本反馈。",
        f"BUG 相关评论共 {bug_count} 条，可作为稳定性风险监控指标。",
        "若具体问题类别持续升高，建议进入版本复盘和专项验证。",
    ]


def _share_chart_insights(result) -> list[str]:
    total = max(sum(result.category_counts.values()), 1)
    monetization = result.category_counts.get("氪金", 0) / total
    gameplay = result.category_counts.get("游戏玩法", 0) / total
    return [
        f"玩法反馈占比约 {_format_percentage(gameplay)}，可用于判断核心玩法认可度。",
        f"氪金反馈占比约 {_format_percentage(monetization)}，需要结合情感判断商业化接受度。",
        "整体占比结构可帮助区分产品体验问题与运营节奏问题。",
    ]


def _market_metric_insights(rows: list[dict], key: str, label: str) -> list[str]:
    if not rows:
        return ["暂无市场样本。"]
    highest = max(rows, key=lambda row: _parse_percentage(row.get(key, "0%")))
    lowest = min(rows, key=lambda row: _parse_percentage(row.get(key, "0%")))
    average = sum(_parse_percentage(row.get(key, "0%")) for row in rows) / len(rows)
    return [
        f"{highest['市场']}的{label}最高，达到 {highest.get(key, '0%')}。",
        f"{lowest['市场']}的{label}最低，为 {lowest.get(key, '0%')}。",
        f"样本平均{label}约 {average:.1f}%，可作为后续监控基线。",
    ]


def _market_category_insights(rows: list[dict]) -> list[str]:
    if not rows:
        return ["暂无市场样本。"]
    keys = ["BUG占比", "氪金占比", "性能问题占比", "游戏玩法占比", "美术占比", "整体评价占比"]
    totals = {key: sum(_parse_percentage(row.get(key, "0%")) for row in rows) for key in keys}
    top_key = max(totals, key=totals.get)
    top_market = max(rows, key=lambda row: _parse_percentage(row.get(top_key, "0%")))
    return [
        f"跨市场最突出的反馈维度是「{top_key.replace('占比', '')}」。",
        f"{top_market['市场']}在该维度占比最高，为 {top_market.get(top_key, '0%')}。",
        "建议优先比较该维度在不同市场中的评论原文，判断是否存在本地化差异。",
    ]


def _score_insights(rows: list[dict]) -> list[str]:
    score_rows = [row for row in rows if _parse_float(row.get("平均星级")) is not None]
    if not score_rows:
        return ["暂无有效平均星级数据。"]
    best = max(score_rows, key=lambda row: _parse_float(row.get("平均星级")) or 0)
    weakest = min(score_rows, key=lambda row: _parse_float(row.get("平均星级")) or 0)
    return [
        f"{best['市场']}平均星级最高，为 {best.get('平均星级')}。",
        f"{weakest['市场']}平均星级最低，为 {weakest.get('平均星级')}。",
        "评分差异可用于定位优先运营市场和风险市场。",
    ]


def _summary_points(text: str, limit: int) -> list[str]:
    cleaned = str(text or "").replace("#", "").replace("*", "").replace("|", " ")
    parts = [part.strip() for part in cleaned.replace("\n", "。").split("。") if part.strip()]
    return parts[:limit]


def _parse_percentage(value) -> float:
    try:
        return float(str(value).replace("%", "").strip())
    except ValueError:
        return 0.0


def _parse_float(value) -> float | None:
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def _average_score(reviews: list[ReviewItem]) -> float | None:
    scores = [review.score for review in reviews if review.score is not None]
    if not scores:
        return None
    return sum(scores) / len(scores)


def _sentiment_percentages(classified_reviews) -> dict[str, float]:
    total = len(classified_reviews)
    if not total:
        return {"正面": 0.0, "中性": 0.0, "负面": 0.0}
    return {
        sentiment: sum(1 for review in classified_reviews if _normalize_sentiment_display(review.sentiment) == sentiment) / total
        for sentiment in ["正面", "中性", "负面"]
    }


def _normalize_sentiment_display(value: str) -> str:
    mapping = {"positive": "正面", "neutral": "中性", "negative": "负面", "正面": "正面", "中性": "中性", "负面": "负面"}
    return mapping.get(str(value).strip().lower(), "中性")


def _category_percentage(category_counts: dict[str, int], category: str, total: int) -> float:
    if not total:
        return 0.0
    return category_counts.get(category, 0) / total


def _format_percentage(value: float) -> str:
    return f"{value * 100:.1f}%"


def _market_sample_notice() -> str:
    return "结果反映所抓取地区评论样本，不代表完整市场表现。"


def _region_sample_notice() -> str:
    return "区域结果基于区域内所选国家的等量评论样本，不代表完整市场表现。"


if __name__ == "__main__":
    main()
