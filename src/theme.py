from __future__ import annotations


PRIMARY = "#F5E400"
CHART_PALETTE = ["#F5C400", "#2F6BFF", "#27C4C2", "#42B866", "#8A5CF6", "#E84A8A", "#F28C38", "#A5A7AC"]
LIGHT_PRIMARY = "#F5E400"
LIGHT_ACCENT_TEXT = "#B89F00"
PRIMARY_ALT = "#F5E400"
ELECTRIC_BLUE = "#333333"
CYAN = "#666666"
DANGER = "#111111"
ORANGE = "#B8A800"
FONT_FAMILY = "Microsoft YaHei"
BREAKPOINTS = {"desktop": "1440px", "tablet": "1100px", "mobile": "768px"}

THEMES = {
    "dark": {
        "background": "#0E0E0E",
        "sidebar": "#0D0D0D",
        "surface": "#181818",
        "surface_alt": "#202020",
        "input": "#151515",
        "text": "#F3F3F3",
        "muted": "#B3B3B3",
        "border": "#303030",
        "grid": "#202020",
        "grid_1": "rgba(255,255,255,.035)",
        "grid_2": "rgba(255,255,255,.018)",
        "contour": "rgba(150,150,150,.05)",
        "table_bg": "#111111",
        "table_head": "#1B1B1B",
        "table_cell": "#141414",
        "table_alt": "#181818",
        "table_hover": "#242424",
        "tag": "#1A1A1A",
        "primary": PRIMARY,
        "accent_text": PRIMARY,
        "primary_hover": "#D6C700",
        "focus": "rgba(245, 228, 0, .28)",
        "shadow": "0 10px 28px rgba(0, 0, 0, .18)",
        "card_hover_shadow": "0 0 0 1px rgba(244, 255, 0, .45), 0 14px 34px rgba(0, 0, 0, .28)",
        "chart_primary": PRIMARY,
    },
    "light": {
        "background": "#F2F2EF",
        "sidebar": "#ECECE8",
        "surface": "#FFFFFF",
        "surface_alt": "#F7F7F4",
        "input": "#F7F7F4",
        "text": "#111111",
        "muted": "#666666",
        "weak": "#858585",
        "border": "#D7D7D2",
        "grid": "#DADAD4",
        "grid_1": "rgba(17,17,17,.035)",
        "grid_2": "rgba(17,17,17,.018)",
        "contour": "rgba(120,120,120,.055)",
        "table_bg": "#FFFFFF",
        "table_head": "#F1F2F4",
        "table_cell": "#FFFFFF",
        "table_alt": "#F7F7F4",
        "table_hover": "#F1F2F4",
        "tag": "#ECECEC",
        "primary": LIGHT_PRIMARY,
        "accent_text": LIGHT_ACCENT_TEXT,
        "primary_hover": "#D6C700",
        "focus": "rgba(214, 184, 0, .24)",
        "shadow": "0 12px 28px rgba(17, 17, 17, .06)",
        "card_hover_shadow": "0 12px 28px rgba(17, 17, 17, .08)",
        "chart_primary": "#7A7000",
    },
}


def resolve_theme_mode(theme_choice: str) -> str:
    if theme_choice == "浅色":
        return "light"
    if theme_choice == "深色":
        return "dark"
    return "system"


def chart_tokens(theme_mode: str) -> dict[str, str | list[str]]:
    mode = "dark" if theme_mode == "dark" else "light"
    tokens = THEMES[mode]
    colors = CHART_PALETTE
    if mode == "light":
        tokens = {**tokens, "background": "#FFFFFF", "surface": "#FFFFFF", "grid": "#E6E6E0", "text": "#111111", "muted": "#555555"}
    return {**tokens, "colors": colors}


BACKGROUND = THEMES["dark"]["background"]
SURFACE = THEMES["dark"]["surface"]
SURFACE_ALT = THEMES["dark"]["surface_alt"]
TEXT = THEMES["dark"]["text"]
MUTED = THEMES["dark"]["muted"]
BORDER = THEMES["dark"]["border"]
GRID = THEMES["dark"]["grid"]
CHART_COLORS = [PRIMARY, "#111111", "#333333", "#666666", "#8A8A8A", ORANGE, "#737373"]
