from __future__ import annotations


GP_BG = "#F5F5F1"
GP_SURFACE = "#FFFFFF"
GP_TEXT = "#111111"
GP_TEXT_SECONDARY = "#666666"
GP_BORDER = "#D8D8D2"
GP_BLUE = "#55D6E8"
GP_YELLOW = "#F1E600"
GP_MAGENTA = "#E83E8C"
GP_GREEN = "#4CAF50"
GP_PURPLE = "#9B6BD6"
GP_ORANGE = "#F2994A"

CHART_PALETTE = [GP_BLUE, GP_MAGENTA, GP_YELLOW, GP_GREEN, GP_PURPLE, GP_ORANGE, GP_TEXT_SECONDARY]

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
        "text_secondary": "#B3B3B3",
        "border": "#303030",
        "grid": "#242424",
        "grid_1": "rgba(255,255,255,.035)",
        "grid_2": "rgba(255,255,255,.018)",
        "contour": "rgba(150,150,150,.05)",
        "table_bg": "#111111",
        "table_head": "#1B1B1B",
        "table_cell": "#141414",
        "table_alt": "#181818",
        "table_hover": "#242424",
        "tag": "#1A1A1A",
        "primary": GP_YELLOW,
        "accent_text": GP_YELLOW,
        "primary_hover": "#D6C700",
        "focus": "rgba(245, 228, 0, .28)",
        "shadow": "0 10px 28px rgba(0, 0, 0, .18)",
        "card_hover_shadow": "0 0 0 1px rgba(241, 230, 0, .45), 0 14px 34px rgba(0, 0, 0, .28)",
    },
    "light": {
        "background": GP_BG,
        "sidebar": "#ECECE8",
        "surface": GP_SURFACE,
        "surface_alt": "#F7F7F4",
        "input": "#F7F7F4",
        "text": GP_TEXT,
        "text_secondary": GP_TEXT_SECONDARY,
        "border": GP_BORDER,
        "grid": GP_BORDER,
        "grid_1": "rgba(17,17,17,.035)",
        "grid_2": "rgba(17,17,17,.018)",
        "contour": "rgba(120,120,120,.055)",
        "table_bg": GP_SURFACE,
        "table_head": "#F1F2F4",
        "table_cell": GP_SURFACE,
        "table_alt": "#F7F7F4",
        "table_hover": "#F1F2F4",
        "tag": "#ECECEC",
        "primary": GP_YELLOW,
        "accent_text": "#B89F00",
        "primary_hover": "#D6C700",
        "focus": "rgba(214, 184, 0, .24)",
        "shadow": "0 12px 28px rgba(17, 17, 17, .06)",
        "card_hover_shadow": "0 12px 28px rgba(17, 17, 17, .08)",
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
    background = tokens["surface"] if mode == "light" else tokens["background"]
    return {
        "background": background,
        "surface": tokens["surface"],
        "text": tokens["text"],
        "muted": tokens["text_secondary"],
        "border": tokens["border"],
        "grid": tokens["grid"],
        "colors": CHART_PALETTE,
    }
