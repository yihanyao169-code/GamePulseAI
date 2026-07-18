from __future__ import annotations

import streamlit as st


STEPS = [
    "获取评论",
    "数据清洗",
    "语言过滤",
    "Claude 分类",
    "情感分析",
    "市场洞察",
    "AI 总结",
    "报告生成",
]


class ProgressTracker:
    def __init__(self):
        self.placeholder = st.empty()

    def update(self, step_index: int, detail: str = "", state: str = "running") -> None:
        step_index = max(1, min(step_index, len(STEPS)))
        percent = step_index / len(STEPS)
        current = STEPS[step_index - 1]
        state_label = {"running": "正在执行", "complete": "已完成", "error": "执行失败"}.get(state, "正在执行")
        bar = _bar_segments(step_index, state)
        meter = f"<div class='mi-progress-meter'><span style='width:{percent * 100:.1f}%'></span></div>"
        detail_html = f"<div class='mi-progress-detail'>{detail}</div>" if detail else ""
        self.placeholder.markdown(
            f"""
            <div class="mi-progress-panel">
              <div class="mi-progress-head">
                <strong>{state_label}</strong>
                <span>{percent:.1%}</span>
              </div>
              <div class="mi-progress-track">{bar}</div>
              {meter}
              <div class="mi-progress-current">{step_index:02d} / 08 · {current}</div>
              {detail_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_complete(detail: str = "分析完成，可查看下方市场洞察报告。") -> None:
    tracker = ProgressTracker()
    tracker.update(7, detail, state="complete")
    st.markdown("<a class='mi-report-link' href='#market-insight-report'>查看分析报告</a>", unsafe_allow_html=True)


def render_saved_complete() -> None:
    st.markdown(
        f"""
        <div class="mi-progress-panel">
          <div class="mi-progress-head"><strong>分析结果已保留</strong><span>87.5%</span></div>
          <div class="mi-progress-track">{_bar_segments(7, "complete")}</div>
          <div class="mi-progress-meter"><span style="width:87.5%"></span></div>
          <div class="mi-progress-current">07 / 08 · AI 总结</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _bar_segments(step_index: int, state: str) -> str:
    parts = []
    for index, label in enumerate(STEPS, start=1):
        class_name = "mi-progress-segment"
        if index < step_index:
            class_name += " is-done"
        elif index == step_index:
            class_name += " is-error" if state == "error" else " is-active"
        parts.append(f"<span class='{class_name}' title='{index:02d} {label}'></span>")
    return "".join(parts)
