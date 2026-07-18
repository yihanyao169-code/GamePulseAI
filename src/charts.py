from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from src.reporting import sort_category_counts
from src.chart_data import prepare_chart_category_data
from src import theme


def configure_chinese_font(theme_mode: str = "dark") -> dict:
    plt.style.use("default")
    plt.rcdefaults()
    tokens = theme.chart_tokens(theme_mode)
    plt.rcParams["font.sans-serif"] = [
        "Noto Sans CJK SC",
        "Noto Sans CJK JP",
        "Arial Unicode MS",
        "PingFang SC",
        "SimHei",
        "Microsoft YaHei",
        "DejaVu Sans",
    ]
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.facecolor"] = tokens["background"]
    plt.rcParams["axes.facecolor"] = tokens["background"]
    plt.rcParams["savefig.facecolor"] = tokens["background"]
    plt.rcParams["text.color"] = tokens["text"]
    plt.rcParams["axes.labelcolor"] = tokens["muted"]
    plt.rcParams["xtick.color"] = tokens["muted"]
    plt.rcParams["ytick.color"] = tokens["muted"]
    return tokens


def apply_light_chart_theme() -> dict:
    return configure_chinese_font("light")


def apply_dark_chart_theme() -> dict:
    return configure_chinese_font("dark")


def _style_axis(ax, tokens: dict) -> None:
    ax.set_facecolor(tokens["background"])
    ax.grid(True, axis="x", color=tokens["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_color(tokens["border"])


def create_bar_chart(category_counts: dict[str, int], output_path: Path, theme_mode: str = "dark") -> Path:
    tokens = configure_chinese_font(theme_mode)
    chart_data = prepare_chart_category_data(category_counts)
    categories = [item["category"] for item in chart_data]
    counts = [item["count"] for item in chart_data]

    fig_height = max(5.5, len(categories) * 0.55)
    fig, ax = plt.subplots(figsize=(9, fig_height))
    colors = [item["color"] for item in chart_data]
    bars = ax.barh(categories, counts, color=colors, edgecolor=tokens["background"], linewidth=1.0)
    ax.set_title("评论类别数量统计", color=tokens["text"])
    ax.set_xlabel("评论数量")
    ax.set_ylabel("类别")
    ax.invert_yaxis()
    ax.tick_params(axis="both", labelsize=13)
    ax.title.set_fontsize(16)
    ax.xaxis.label.set_size(14)
    ax.yaxis.label.set_size(14)
    _style_axis(ax, tokens)
    max_count = max(counts) if counts else 0
    total = sum(counts) or 1
    ax.set_xlim(0, max_count * 1.15 if max_count else 1)
    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_width() + max(max_count * 0.01, 0.2),
            bar.get_y() + bar.get_height() / 2,
            f"{count} ({count / total * 100:.1f}%)",
            va="center",
            fontsize=12,
            color=tokens["text"],
        )
    fig.tight_layout(pad=0.8)
    fig.savefig(output_path, dpi=180, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    return output_path


def create_pie_chart(category_counts: dict[str, int], output_path: Path, theme_mode: str = "dark") -> Path:
    tokens = configure_chinese_font(theme_mode)
    chart_data = prepare_chart_category_data(category_counts)

    fig, ax = plt.subplots(figsize=(7, 5))
    if chart_data:
        labels = [item["category"] for item in chart_data]
        values = [item["count"] for item in chart_data]
        colors = [item["color"] for item in chart_data]
        wedges, _, autotexts = ax.pie(
            values,
            labels=None,
            autopct=lambda pct: f"{pct:.1f}%" if pct >= 4 else "",
            startangle=90,
            pctdistance=0.68,
            colors=colors,
            textprops={"fontsize": 12, "fontweight": "bold"},
            wedgeprops={"edgecolor": "#FFFFFF", "linewidth": 1.2},
            radius=0.82,
        )
        for text, color in zip(autotexts, colors):
            text.set_color(_contrast_text_color(color))
        legend = ax.legend(
            wedges,
            labels,
            loc="center left",
            bbox_to_anchor=(1.0, 0.5),
            frameon=False,
            fontsize=10,
        )
        for text in legend.get_texts():
            text.set_color(tokens["text"])
    else:
        ax.text(0.5, 0.5, "暂无数据", ha="center", va="center", fontsize=16, color=tokens["muted"])
    ax.set_title("评论类别占比", color=tokens["text"])
    ax.axis("equal")
    fig.tight_layout(pad=0.7)
    fig.savefig(output_path, dpi=180, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    return output_path


def _contrast_text_color(hex_color: str) -> str:
    value = hex_color.lstrip("#")
    r, g, b = (int(value[index:index + 2], 16) for index in (0, 2, 4))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#111111" if luminance > 0.58 else "#FFFFFF"


def create_market_bar_chart(
    rows: list[dict],
    value_key: str,
    title: str,
    output_path: Path,
    y_label: str = "占比 (%)",
    value_suffix: str = "%",
    theme_mode: str = "dark",
) -> Path:
    tokens = configure_chinese_font(theme_mode)
    markets = [row["市场"] for row in rows]
    values = [_to_float(row[value_key]) for row in rows]

    fig, ax = plt.subplots(figsize=(11, 6))
    colors = tokens["colors"]
    bars = ax.bar(markets, values, color=[colors[index % len(colors)] for index in range(len(markets))])
    ax.set_title(title, fontsize=18, color=tokens["text"])
    ax.set_ylabel(y_label, fontsize=14)
    ax.tick_params(axis="both", labelsize=12)
    _style_axis(ax, tokens)
    max_value = max(values) if values else 0
    ax.set_ylim(0, max_value * 1.2 if max_value else 1)
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(max_value * 0.02, 0.5),
            f"{value:.1f}{value_suffix}",
            ha="center",
            fontsize=12,
            color=tokens["text"],
        )
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def create_market_category_distribution_chart(rows: list[dict], output_path: Path, theme_mode: str = "dark") -> Path:
    tokens = configure_chinese_font(theme_mode)
    markets = [row["市场"] for row in rows]
    keys = ["游戏玩法占比", "BUG占比", "氪金占比", "性能问题占比", "整体评价占比"]
    colors = tokens["colors"][: len(keys)]

    fig, ax = plt.subplots(figsize=(12, 6))
    bottoms = [0.0 for _ in markets]
    for key, color in zip(keys, colors):
        values = [_to_float(row[key]) for row in rows]
        ax.bar(markets, values, bottom=bottoms, label=key.replace("占比", ""), color=color)
        bottoms = [bottom + value for bottom, value in zip(bottoms, values)]

    ax.set_title("各市场主要问题类别分布", fontsize=18, color=tokens["text"])
    ax.set_ylabel("占比 (%)", fontsize=14)
    ax.tick_params(axis="both", labelsize=12)
    _style_axis(ax, tokens)
    legend = ax.legend(loc="upper right", facecolor=tokens["surface"], edgecolor=tokens["border"])
    for text in legend.get_texts():
        text.set_color(tokens["text"])
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def _to_float(value) -> float:
    try:
        return float(str(value).rstrip("%"))
    except ValueError:
        return 0.0
