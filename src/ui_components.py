from __future__ import annotations

import streamlit as st

from src import theme


def inject_theme_css(theme_choice: str) -> None:
    mode = theme.resolve_theme_mode(theme_choice)
    light = theme.THEMES["light"]
    dark = theme.THEMES["dark"]

    if mode == "light":
        variable_css = _css_variables(light)
        color_scheme = "light"
    elif mode == "dark":
        variable_css = _css_variables(dark)
        color_scheme = "dark"
    else:
        variable_css = f"""
        :root {{{_variables_block(light)}}}
        @media (prefers-color-scheme: dark) {{
          :root {{{_variables_block(dark)}}}
        }}
        """
        color_scheme = "light dark"

    st.markdown(
        f"""
        <style>
        {variable_css}
        :root {{color-scheme: {color_scheme};}}
        [data-testid="stAppViewContainer"] {{color-scheme: {color_scheme};}}
        * {{accent-color: var(--gp-primary); box-sizing: border-box;}}
        html {{scroll-behavior: smooth;}}
        html, body, [data-testid="stAppViewContainer"], .stApp,
        [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
        [data-testid="stStatusWidget"] {{
            background:
              linear-gradient(var(--gp-grid-1) 1px, transparent 1px),
              linear-gradient(90deg, var(--gp-grid-1) 1px, transparent 1px),
              var(--gp-bg) !important;
            background-size: 44px 44px, 44px 44px, auto !important;
            color: var(--gp-text) !important;
        }}
        [data-testid="stSidebar"], [data-testid="stSidebarContent"], section[data-testid="stSidebar"] {{
            background: var(--gp-sidebar) !important;
            color: var(--gp-text) !important;
        }}
        [data-testid="stHeader"] {{box-shadow: none !important; border-bottom: 1px solid var(--gp-border);}}
        .main .block-container {{padding: 2rem clamp(1rem, 4vw, 4rem) 4rem; max-width: 1440px;}}
        [data-testid="stSidebar"] {{border-right: 1px solid var(--gp-border);}}
        h1, h2, h3, h4, h5, h6, p, li, span, label {{
            color: var(--gp-text);
            font-family: Inter, "Noto Sans SC", "Microsoft YaHei", sans-serif;
        }}
        small, [data-testid="stCaptionContainer"], .mi-muted {{color: var(--gp-muted) !important;}}
        pre, code, [data-testid="stJson"], [data-testid="stCodeBlock"], [data-testid="stMarkdownContainer"] pre {{
            background: var(--gp-surface-alt) !important;
            color: var(--gp-text) !important;
            border: 1px solid var(--gp-border) !important;
            text-shadow: none !important;
        }}
        [data-testid="stExpander"], details, details > summary {{
            background: var(--gp-surface) !important;
            color: var(--gp-text) !important;
            border-color: var(--gp-border) !important;
        }}
        [data-testid="stStatus"], [data-testid="stAlert"], [data-testid="stException"], .stAlert {{
            background: var(--gp-surface-alt) !important;
            color: var(--gp-text) !important;
            border-color: var(--gp-border) !important;
        }}
        [data-testid="stMarkdownContainer"] ul, [data-testid="stMarkdownContainer"] ol {{
            color: var(--gp-text) !important;
        }}

        .mi-group-title {{
            display:flex; align-items:baseline; gap:8px;
            margin: 14px 0 2px; padding-left: 0;
            color: var(--gp-text); font-size: 14px; font-weight: 900;
        }}
        .mi-group-title:before {{content:""; width:3px; height:16px; background:var(--gp-primary); display:inline-block;}}
        .mi-group-title small {{color: var(--gp-muted) !important; font-size: 10px; letter-spacing: .08em; font-weight: 800; text-transform: uppercase;}}
        .mi-group-subtitle {{display:none;}}
        .mi-sidebar-brand {{margin: 4px 0 18px;}}
        .mi-sidebar-brand-name {{
            color: var(--gp-text);
            font-size: 21px;
            font-weight: 700;
            line-height: 1.15;
            margin-bottom: 12px;
        }}
        .mi-author-label {{
            color: var(--gp-muted);
            font-size: 12px;
            font-weight: 700;
            letter-spacing: .02em;
            line-height: 1.25;
        }}
        .mi-author-name {{
            color: var(--gp-muted);
            font-size: 15px;
            font-weight: 700;
            line-height: 1.25;
            margin-top: 3px;
        }}

        [data-testid="stSidebar"] hr {{margin: 0.55rem 0 !important;}}
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{margin-bottom: 0.15rem !important;}}
        [data-testid="stSidebar"] .stRadio, [data-testid="stSidebar"] .stSelectbox,
        [data-testid="stSidebar"] .stTextInput, [data-testid="stSidebar"] .stNumberInput,
        [data-testid="stSidebar"] .stSlider {{margin-bottom: 0.35rem !important;}}
        div[data-baseweb="input"] input, textarea, div[data-baseweb="select"] > div,
        [data-testid="stNumberInput"] input {{
            background: var(--gp-input) !important;
            color: var(--gp-text) !important;
            border: 1px solid var(--gp-border) !important;
            border-radius: 8px !important;
            min-height: 42px !important;
            caret-color: var(--gp-primary) !important;
        }}
        div[data-baseweb="input"]:hover input, div[data-baseweb="select"]:hover > div,
        [data-testid="stNumberInput"]:hover input {{
            border-color: var(--gp-primary) !important;
        }}
        input::placeholder, textarea::placeholder {{color: var(--gp-muted) !important; opacity: 1 !important;}}
        div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within,
        [data-testid="stNumberInput"]:focus-within {{
            outline: 1px solid var(--gp-primary) !important;
            box-shadow: 0 0 0 2px var(--gp-focus) !important;
            border-radius: 8px !important;
        }}
        [data-testid="stNumberInput"] button {{
            background: var(--gp-input) !important;
            color: var(--gp-text) !important;
            border-color: var(--gp-border) !important;
            height: 42px !important;
            min-width: 38px !important;
        }}
        [data-testid="stNumberInput"] button:hover {{color: var(--gp-primary) !important; border-color: var(--gp-primary) !important;}}

        [data-testid="stRadio"] [role="radio"] {{
            border-color: var(--gp-border) !important;
            background: transparent !important;
            box-shadow: none !important;
        }}
        [data-testid="stRadio"] [role="radio"][aria-checked="true"] {{
            border-color: var(--gp-primary) !important;
            background: var(--gp-primary) !important;
            box-shadow: inset 0 0 0 4px var(--gp-bg) !important;
        }}
        [data-testid="stRadio"] [role="radio"] * {{
            background-color: var(--gp-primary) !important;
            border-color: var(--gp-primary) !important;
        }}
        [data-testid="stRadio"] label:hover [role="radio"] {{border-color: var(--gp-primary) !important;}}

        .stSlider [data-baseweb="slider"] div {{border-color: var(--gp-border) !important;}}
        .stSlider [data-baseweb="slider"] [role="slider"] {{
            background: var(--gp-primary) !important;
            border-color: var(--gp-primary) !important;
            box-shadow: none !important;
        }}
        .stSlider [data-baseweb="slider"] div[style*="background"] {{
            background-color: var(--gp-primary) !important;
        }}
        .stSlider [data-baseweb="slider"] span, .stSlider [data-baseweb="slider"] div {{
            color: var(--gp-text) !important;
        }}
        .stSlider [data-baseweb="slider"] div[style*="rgb(255"],
        .stSlider [data-baseweb="slider"] div[style*="red"],
        [data-baseweb="radio"] div[style*="rgb(255"],
        [data-baseweb="checkbox"] div[style*="rgb(255"],
        [data-baseweb="tag"][style*="rgb(255"],
        [data-baseweb="tag"] div[style*="rgb(255"] {{
            background-color: var(--gp-primary) !important;
            color: var(--gp-text) !important;
            border-color: var(--gp-primary) !important;
        }}

        [data-baseweb="tag"] {{
            background: var(--gp-tag) !important;
            color: var(--gp-text) !important;
            border: 1px solid var(--gp-primary) !important;
            border-radius: 4px !important;
        }}
        [data-baseweb="tag"] span {{
            color: var(--gp-text) !important;
        }}
        [data-baseweb="tag"] svg {{color: var(--gp-muted) !important; fill: var(--gp-muted) !important;}}
        [data-baseweb="tag"]:hover, [data-baseweb="tag"]:hover svg {{
            border-color: var(--gp-primary) !important;
            color: var(--gp-primary) !important;
            fill: var(--gp-primary) !important;
        }}
        [data-baseweb="select"] svg, [data-baseweb="input"] svg {{
            color: var(--gp-muted) !important;
            fill: var(--gp-muted) !important;
        }}
        [data-baseweb="select"]:hover svg, [data-baseweb="input"]:hover svg {{
            color: var(--gp-primary) !important;
            fill: var(--gp-primary) !important;
        }}
        [data-baseweb="popover"], [data-baseweb="menu"] {{
            background: var(--gp-surface-alt) !important;
            color: var(--gp-text) !important;
            border: 1px solid var(--gp-border) !important;
        }}
        [role="listbox"], [role="option"] {{
            background: var(--gp-surface-alt) !important;
            color: var(--gp-text) !important;
        }}
        [role="option"]:hover, [role="option"][aria-selected="true"] {{
            background: var(--gp-tag) !important;
            color: var(--gp-text) !important;
            box-shadow: inset 3px 0 0 var(--gp-primary) !important;
        }}

        div.stButton > button, div.stDownloadButton > button {{
            min-height: 44px; border-radius: 8px; border: 1px solid var(--gp-primary);
            font-weight: 900; background: var(--gp-surface); color: var(--gp-primary);
        }}
        div.stButton > button:hover, div.stDownloadButton > button:hover {{
            border-color: var(--gp-primary-hover); background: var(--gp-primary-hover); color: #111111;
        }}
        div.stButton > button[kind="primary"] {{
            background: var(--gp-primary) !important; color: #111111 !important; border-color: var(--gp-primary) !important;
        }}
        div.stButton > button[kind="primary"]:hover {{
            background: var(--gp-primary-hover) !important; color: #111111 !important; border-color: var(--gp-primary-hover) !important;
        }}
        div.stButton > button:disabled, div.stDownloadButton > button:disabled {{
            background: var(--gp-surface-alt) !important; color: var(--gp-muted) !important; border-color: var(--gp-border) !important;
        }}
        button:focus, input:focus, textarea:focus {{outline-color: var(--gp-primary) !important; box-shadow: 0 0 0 1px var(--gp-primary) !important;}}

        [data-testid="stMetric"], .mi-card, .mi-insight, .mi-export {{
            background: var(--gp-surface) !important; border: 1px solid var(--gp-border) !important;
            border-radius: 0; color: var(--gp-text);
            box-shadow: var(--gp-shadow);
        }}
        [data-testid="stMetric"] {{padding: 12px 14px;}}
        [data-testid="stMetricLabel"] {{color: var(--gp-muted) !important;}}
        [data-testid="stMetricValue"] {{color: var(--gp-primary) !important;}}
        div[data-testid="stDataFrame"], [data-testid="stTable"] {{
            border: 1px solid var(--gp-border) !important;
            background: var(--gp-surface) !important;
            color: var(--gp-text) !important;
        }}
        [data-testid="stTable"] table, [data-testid="stTable"] thead, [data-testid="stTable"] tbody,
        [data-testid="stTable"] tr, [data-testid="stTable"] td, [data-testid="stTable"] th {{
            background: var(--gp-surface) !important;
            color: var(--gp-text) !important;
            border-color: var(--gp-border) !important;
        }}
        .mi-table-wrap {{
            width:100%; overflow-x:auto; border:1px solid var(--gp-border); background:var(--gp-table-bg);
            margin:8px 0 18px;
        }}
        .mi-data-table {{width:100%; border-collapse:collapse; color:var(--gp-text); font-size:14px;}}
        .mi-data-table thead th {{
            background:var(--gp-table-head); color:var(--gp-text); text-align:left; padding:10px 12px;
            border-bottom:1px solid var(--gp-border); font-weight:900;
        }}
        .mi-data-table tbody td {{
            background:var(--gp-table-cell); color:var(--gp-text); text-align:left; padding:9px 12px;
            border-bottom:1px solid var(--gp-border);
        }}
        .mi-data-table tbody tr:nth-child(even) td {{background:var(--gp-table-alt);}}
        .mi-data-table tbody tr:hover td {{background:var(--gp-table-hover);}}

        [data-testid="stProgress"] div div div {{background-color: var(--gp-primary) !important;}}
        [data-testid="stProgress"] div div {{background-color: var(--gp-border) !important;}}

        .mi-hero {{
            display: grid;
            grid-template-columns: minmax(0, 1.38fr) minmax(320px, .92fr);
            gap: clamp(26px, 5vw, 64px);
            align-items: center;
            position: relative; overflow: hidden; box-sizing: border-box;
            min-height: 390px; padding: clamp(28px, 5vw, 68px);
            border: 1px solid var(--gp-border); background:
              radial-gradient(ellipse at 74% 16%, color-mix(in srgb, var(--gp-primary) 10%, transparent), transparent 28%),
              repeating-radial-gradient(ellipse at 78% 48%, transparent 0 18px, rgba(17,17,17,.035) 19px 20px),
              linear-gradient(rgba(17,17,17,.045) 1px, transparent 1px),
              linear-gradient(90deg, rgba(17,17,17,.045) 1px, transparent 1px),
              var(--gp-bg);
            background-size: auto, auto, 42px 42px, 42px 42px, auto;
            margin-bottom: 56px;
            box-shadow: var(--gp-shadow);
        }}
        .mi-hero:after {{
            content:""; position:absolute; right:-54px; bottom:-44px;
            width:220px; height:120px; background:var(--gp-primary);
            clip-path: polygon(18% 0, 100% 0, 82% 100%, 0 100%);
            opacity:.9; z-index:0;
        }}
        .mi-hero-copy, .mi-hero-art {{min-width: 0; box-sizing: border-box;}}
        .mi-hero-copy, .mi-hero-art {{position:relative; z-index:1;}}
        .mi-kicker {{
            display:inline-block; margin-bottom:18px; padding-left:12px;
            border-left:4px solid var(--gp-primary);
            color:var(--gp-muted); font-size:12px; font-weight:900;
            line-height:1.2; letter-spacing:.16em;
        }}
        .mi-hero h1.mi-title {{
            font-size: clamp(2.65rem, 5.2vw, 6.2rem);
            line-height: .98; margin: 0 0 20px; color: var(--gp-text);
            letter-spacing: -.035em; font-weight: 900;
            overflow-wrap: normal; word-break: keep-all;
            max-width: 820px;
        }}
        .mi-title-line {{display:block; white-space:nowrap;}}
        .mi-title-mark {{
            display:inline-block; position:relative; padding:0 .08em;
            color:#111111; background:var(--gp-primary);
        }}
        .mi-product-subtitle {{
            font-size: clamp(18px, 2vw, 20px) !important;
            color: var(--gp-muted) !important;
            font-weight: 800;
            letter-spacing: .02em;
            margin-bottom: 12px !important;
        }}
        .mi-english-tagline {{
            font-size: 13px !important;
            letter-spacing: .02em;
        }}
        .mi-hero .accent {{color: var(--gp-text); font-weight:800; letter-spacing:.04em;}}
        .mi-hero p {{font-size: 16px; margin: 0 0 8px; color: var(--gp-muted); max-width: 620px;}}
        .mi-hero-visual {{
            position:relative; width:100%; max-width:100%; min-width:0;
            aspect-ratio: 1.08 / 1; min-height: 280px;
            border:1px solid var(--gp-border); background:
              linear-gradient(rgba(17,17,17,.05) 1px, transparent 1px),
              linear-gradient(90deg, rgba(17,17,17,.05) 1px, transparent 1px),
              repeating-linear-gradient(135deg, transparent 0 10px, color-mix(in srgb, var(--gp-primary) 10%, transparent) 10px 11px),
              var(--gp-surface);
            background-size: 30px 30px, 30px 30px, auto, auto;
            opacity:.98;
            overflow:hidden;
        }}
        .mi-flow-label {{
            position:absolute; left:18px; top:14px; color:var(--gp-muted);
            font-size:10px; font-weight:900; letter-spacing:.14em;
        }}
        .mi-flow {{position:absolute; inset:48px 22px 24px; display:grid; grid-template-columns:1fr; gap:8px;}}
        .mi-flow-step {{
            display:grid; grid-template-columns:44px 1fr auto; align-items:center; min-width:0;
            padding:10px 12px; border:1px solid var(--gp-border);
            background: color-mix(in srgb, var(--gp-surface) 88%, transparent);
        }}
        .mi-flow-step:after {{content:""; width:8px; height:8px; background:var(--gp-primary);}}
        .mi-flow-step span:first-child {{font-size:11px; color:var(--gp-accent-text); font-weight:900; letter-spacing:.08em;}}
        .mi-flow-step span:last-child {{font-size:13px; color:var(--gp-text); font-weight:900; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}}
        .mi-flow-arrow {{text-align:center; color:var(--gp-muted); font-size:11px; line-height:1; margin:-5px 0;}}
        .mi-tags {{display:flex; flex-wrap:wrap; gap:8px; margin-top:22px; max-width:620px;}}
        .mi-tag {{
            display:inline-flex; align-items:center; gap:6px; white-space:nowrap; max-width:100%;
            padding:7px 10px; border:1px solid var(--gp-border); border-left:3px solid var(--gp-primary);
            color:var(--gp-text); background:var(--gp-surface); font-size:11px;
            letter-spacing:.06em; font-weight:900; cursor:default;
        }}
        .mi-tag:before {{content:""; width:5px; height:5px; background:var(--gp-primary); display:inline-block;}}
        .mi-feature-grid {{display:grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap:0; margin:18px 0 58px; border:1px solid var(--gp-border); background:var(--gp-surface);}}
        .mi-card {{
            display:block; position:relative; padding:18px 16px 22px; min-height:154px; margin:0;
            text-decoration:none !important; transition: border-color 200ms ease;
            border-width:0 1px 0 0 !important; box-shadow:none !important; cursor:default;
        }}
        .mi-card:nth-child(6n) {{border-right:0 !important;}}
        .mi-card:before {{content: attr(data-index); color:var(--gp-accent-text); font-size:12px; font-weight:900;}}
        .mi-card:after {{content:""; position:absolute; right:0; bottom:0; width:42px; height:5px; background:var(--gp-primary);}}
        .mi-card h3 {{font-size:16px; margin:12px 0 10px; color:var(--gp-text); font-weight:900; line-height:1.22;}}
        .mi-card .mi-muted {{font-size:12px; line-height:1.55;}}
        .mi-section-title {{font-size:18px; font-weight:900; color:var(--gp-text); margin:54px 0 16px; letter-spacing:.06em; border-bottom:3px solid var(--gp-primary); display:inline-block; padding-bottom:5px;}}
        .mi-workflow {{display:flex; flex-wrap:nowrap; gap:12px; margin:10px 0 42px; align-items:stretch;}}
        .mi-step {{
            position:relative; display:flex; align-items:center; justify-content:center; min-height:54px;
            flex:1 1 0; min-width:0; margin:0; padding:10px 12px; border-radius:0;
            border:1px solid var(--gp-border); background:var(--gp-surface); color:var(--gp-muted);
            font-size:12px; font-weight:900; letter-spacing:.04em; text-align:center;
        }}
        .mi-step:not(:last-child):after {{
            content:""; position:absolute; right:-10px; top:50%; width:14px; height:1px;
            background:var(--gp-text); z-index:2;
        }}
        .mi-step-active {{background:var(--gp-primary); border-color:var(--gp-primary); color:#111111;}}
        .mi-step-done {{background:var(--gp-surface-alt); border-color:var(--gp-primary); color:var(--gp-accent-text);}}
        .mi-insight {{border-left:3px solid var(--gp-primary) !important; padding:14px 16px; margin:12px 0 24px;}}
        .mi-insight strong {{color:var(--gp-text); border-bottom:2px solid var(--gp-primary);}}
        .mi-export {{padding:16px 18px; margin-top:18px;}}
        .mi-result-grid {{display:grid; grid-template-columns: minmax(280px, 1fr) minmax(280px, .9fr) minmax(320px, 1.1fr); gap:16px; align-items:start; margin: 10px 0 24px;}}
        .mi-report-list {{display:grid; gap:10px; margin: 8px 0 22px;}}
        .mi-report-item {{
            background:var(--gp-surface); border:1px solid var(--gp-border);
            padding:12px 14px; color:var(--gp-text); border-left:4px solid var(--gp-primary);
            min-width:0; word-break:normal; overflow-wrap:break-word; line-height:1.65;
        }}
        .mi-report-item strong {{color:var(--gp-text); word-break:keep-all; overflow-wrap:break-word;}}
        .mi-report-item small {{display:block; margin-top:4px; color:var(--gp-muted) !important; word-break:normal; overflow-wrap:break-word; line-height:1.65;}}
        .insight-grid {{display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:24px; align-items:start; margin:8px 0 24px;}}
        .insight-column {{min-width:0;}}
        .insight-column h3 {{white-space:nowrap; word-break:keep-all; overflow-wrap:normal; margin:0 0 14px; color:var(--gp-text); font-size:1.17em;}}
        .insight-column .mi-report-list {{margin-bottom:0;}}
        .recommendation-section {{margin:24px 0 12px;}}
        .priority-section-title {{white-space:nowrap; word-break:keep-all; overflow-wrap:normal; margin:24px 0 12px; color:var(--gp-text); font-size:1.08rem; font-weight:900;}}
        .recommendation-grid {{display:grid; grid-template-columns:repeat(2, minmax(320px, 1fr)); gap:18px;}}
        .recommendation-card {{min-width:0; padding:18px 20px; background:var(--gp-surface); border:1px solid var(--gp-border); border-left:4px solid var(--gp-primary); color:var(--gp-text);}}
        .recommendation-card h4 {{white-space:normal; word-break:keep-all; overflow-wrap:break-word; margin:0 0 10px; color:var(--gp-text);}}
        .recommendation-card p {{word-break:normal; overflow-wrap:break-word; line-height:1.65; margin:8px 0 0; color:var(--gp-muted);}}
        div[data-testid="stButton"] button, div[data-testid="stDownloadButton"] button {{
            min-width:180px; white-space:nowrap !important; word-break:keep-all !important; overflow-wrap:normal !important;
        }}
        .mi-score-panel {{display:grid; grid-template-columns: 240px 1fr; gap:18px; align-items:center; background:var(--gp-surface); border:1px solid var(--gp-border); padding:18px; margin:8px 0 8px;}}
        .mi-score-panel b {{display:block; font-size:42px; line-height:1; color:var(--gp-text);}}
        .mi-score-panel span {{display:inline-block; margin-top:8px; padding:4px 10px; background:var(--gp-primary); color:#111111; font-weight:900;}}
        .mi-score-panel strong {{display:block; color:var(--gp-text); margin-bottom:6px;}}
        .mi-eval-panel {{background:var(--gp-surface); border:1px solid var(--gp-border); padding:18px; margin:8px 0 16px;}}
        .mi-eval-head {{display:flex; justify-content:space-between; align-items:flex-start; gap:18px; border-bottom:1px solid var(--gp-border); padding-bottom:14px; margin-bottom:14px;}}
        .mi-eval-title {{font-size:15px; color:var(--gp-muted); font-weight:900; letter-spacing:.08em;}}
        .mi-eval-score {{font-size:54px; line-height:.95; color:var(--gp-text); font-weight:900;}}
        .mi-eval-score small {{font-size:18px; color:var(--gp-muted) !important;}}
        .mi-eval-grade {{display:inline-block; background:var(--gp-primary); color:#111111; font-size:16px; font-weight:900; padding:5px 12px; margin-top:8px;}}
        .mi-eval-grid {{display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:10px; margin: 12px 0;}}
        .mi-eval-metric {{border:1px solid var(--gp-border); background:var(--gp-surface-alt); padding:13px; min-height:98px;}}
        .mi-eval-metric strong {{display:block; color:var(--gp-muted); font-size:13px; margin-bottom:9px;}}
        .mi-eval-metric b {{display:block; color:var(--gp-text); font-size:30px; line-height:1;}}
        .mi-eval-summary {{border-left:4px solid var(--gp-primary); padding:10px 12px; background:var(--gp-surface-alt); color:var(--gp-text); margin-top:12px;}}
        .mi-data-scope-card {{background:var(--gp-surface); border:1px solid var(--gp-border); padding:16px 18px; margin:4px 0 18px;}}
        .mi-data-scope-grid {{display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:10px 16px; margin-top:12px;}}
        .mi-data-scope-row {{border-left:3px solid var(--gp-primary); background:var(--gp-surface-alt); padding:10px 12px; min-width:0;}}
        .mi-data-scope-row strong {{display:block; color:var(--gp-muted); font-size:12px; margin-bottom:4px; white-space:nowrap;}}
        .mi-data-scope-row span {{display:block; color:var(--gp-text); font-size:14px; font-weight:700; line-height:1.5; word-break:normal; overflow-wrap:break-word;}}
        .mi-data-scope-row small {{display:block; color:var(--gp-muted); font-size:12px; line-height:1.45; margin-top:4px;}}
        .mi-data-scope-note {{margin-top:12px; color:var(--gp-muted); font-size:13px; line-height:1.55;}}
        .mi-eval-breakdown {{display:grid; gap:8px; margin:10px 0;}}
        .mi-eval-row {{display:grid; grid-template-columns:1.2fr .55fr .45fr .55fr; gap:8px; align-items:center; border:1px solid var(--gp-border); background:var(--gp-surface); padding:8px 10px; color:var(--gp-text);}}
        .mi-sentiment-grid {{display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:12px; margin:8px 0 24px;}}
        .mi-sentiment-card {{background:var(--gp-surface); border:1px solid var(--gp-border); padding:14px;}}
        .mi-sentiment-card b {{display:block; font-size:13px; color:var(--gp-muted);}}
        .mi-sentiment-card span {{display:block; margin-top:8px; font-size:26px; font-weight:900; color:var(--gp-text);}}
        .mi-sentiment-card:before {{content:""; display:block; width:26px; height:4px; background:var(--gp-primary); margin-bottom:10px;}}
        .mi-progress-panel {{
            max-height: 140px; margin: 14px 0 20px; padding: 14px 16px;
            border: 1px solid var(--gp-border); background: var(--gp-surface);
            box-shadow: var(--gp-shadow);
        }}
        .mi-progress-head {{display:flex; justify-content:space-between; align-items:center; gap:16px; margin-bottom:10px;}}
        .mi-progress-head strong {{font-size:13px; letter-spacing:.08em; color:var(--gp-text);}}
        .mi-progress-head span {{font-size:13px; font-weight:900; color:var(--gp-accent-text);}}
        .mi-progress-track {{display:grid; grid-template-columns:repeat(8, 1fr); gap:5px; margin-bottom:10px;}}
        .mi-progress-segment {{height:9px; background:var(--gp-border); display:block;}}
        .mi-progress-segment.is-done {{background:color-mix(in srgb, var(--gp-primary) 52%, var(--gp-text));}}
        .mi-progress-segment.is-active {{background:var(--gp-primary);}}
        .mi-progress-segment.is-error {{background:var(--gp-text); outline:2px solid var(--gp-primary);}}
        .mi-progress-meter {{height:8px; background:var(--gp-border); margin:0 0 9px; overflow:hidden;}}
        .mi-progress-meter span {{display:block; height:100%; background:var(--gp-primary);}}
        .mi-progress-current {{font-size:13px; font-weight:900; color:var(--gp-text);}}
        .mi-progress-detail {{margin-top:5px; color:var(--gp-muted); font-size:12px;}}
        .mi-method-steps {{
            display:grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap:10px;
            margin: 8px 0 18px;
        }}
        .mi-report-link {{
            display:inline-flex; margin: 0 0 18px; padding:7px 10px; border:1px solid var(--gp-primary);
            color:#111111 !important; background:var(--gp-primary); text-decoration:none !important; font-weight:900; font-size:12px;
        }}
        .mi-chart-wrap {{
            width:100%; margin:0; border:1px solid var(--gp-border); background:var(--gp-surface);
            padding:12px; overflow:hidden;
        }}
        .mi-chart-wrap img, .mi-chart-wrap canvas, .mi-chart-wrap svg {{width:100%; height:auto; object-fit:contain; object-position:center; display:block; margin:0;}}
        @media (min-width: 1400px) {{
          .mi-hero {{grid-template-columns: minmax(0, 1.42fr) minmax(380px, .88fr);}}
          .mi-hero-visual {{min-height: 330px;}}
        }}
        @media (max-width: 1100px) {{
          [data-testid="stHorizontalBlock"] {{flex-wrap:wrap !important;}}
          [data-testid="stHorizontalBlock"] > [data-testid="column"] {{min-width:100% !important; flex:1 1 100% !important;}}
          .mi-hero {{grid-template-columns: 1fr;}}
          .mi-hero h1.mi-title {{font-size: clamp(2.5rem, 8vw, 5rem);}}
          .mi-hero-visual {{min-height: 260px; aspect-ratio: 16 / 8;}}
          .mi-feature-grid {{grid-template-columns: repeat(3, minmax(0, 1fr));}}
          .mi-card:nth-child(3n) {{border-right:0 !important;}}
          .mi-card:nth-child(n+4) {{border-top:1px solid var(--gp-border) !important;}}
          .mi-workflow {{flex-wrap:wrap;}}
          .mi-step {{flex:1 1 calc(25% - 12px);}}
          .mi-result-grid {{grid-template-columns:1fr;}}
        }}
        @media (max-width: 900px) {{
          .insight-grid {{grid-template-columns:1fr;}}
          .recommendation-grid {{grid-template-columns:1fr;}}
        }}
        @media (max-width: 768px) {{
          .main .block-container {{padding-left: 1rem; padding-right: 1rem;}}
          .mi-hero {{grid-template-columns: 1fr; padding: clamp(18px, 6vw, 28px); gap:22px; min-height:0;}}
          .mi-hero h1.mi-title {{font-size: clamp(2rem, 13vw, 3.4rem); line-height:1.02;}}
          .mi-tags {{gap:6px;}}
          .mi-tag {{font-size:10px; padding:6px 8px;}}
          .mi-hero-visual {{min-height: 230px; aspect-ratio: 4 / 3;}}
          .mi-flow {{inset:42px 14px 18px;}}
          .mi-flow-step {{grid-template-columns:36px 1fr auto; padding:8px 9px;}}
          .mi-feature-grid {{grid-template-columns: repeat(2, minmax(0, 1fr));}}
          .mi-card, .mi-card:nth-child(3n), .mi-card:nth-child(6n) {{border-right:1px solid var(--gp-border) !important;}}
          .mi-card:nth-child(2n) {{border-right:0 !important;}}
          .mi-card:nth-child(n+3) {{border-top:1px solid var(--gp-border) !important;}}
          .mi-card {{min-height:142px; padding:16px 14px 20px;}}
          .mi-workflow {{display:grid; grid-template-columns:1fr; gap:8px;}}
          .mi-method-steps {{grid-template-columns:1fr;}}
          .mi-step {{min-height:46px;}}
          .mi-step:not(:last-child):after {{right:50%; top:auto; bottom:-7px; width:1px; height:8px;}}
          .mi-sentiment-grid {{grid-template-columns:1fr;}}
          .mi-score-panel {{grid-template-columns:1fr;}}
          .mi-eval-head {{display:block;}}
          .mi-eval-grid {{grid-template-columns:1fr;}}
          .mi-eval-row {{grid-template-columns:1fr;}}
          .mi-data-scope-grid {{grid-template-columns:1fr;}}
          .insight-grid {{grid-template-columns:1fr;}}
          .recommendation-grid {{grid-template-columns:1fr;}}
        }}
        @media (max-width: 520px) {{
          .mi-feature-grid {{grid-template-columns: 1fr;}}
          .mi-card, .mi-card:nth-child(2n), .mi-card:nth-child(3n), .mi-card:nth-child(6n) {{border-right:0 !important;}}
          .mi-card:nth-child(n+2) {{border-top:1px solid var(--gp-border) !important;}}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def section_title(label: str, subtitle: str) -> None:
    st.markdown(f"<div class='mi-group-title'>{subtitle}<small>{label}</small></div>", unsafe_allow_html=True)


def sidebar_branding() -> None:
    st.markdown(
        """
        <div class="mi-sidebar-brand">
          <div class="mi-sidebar-brand-name">GamePulse AI</div>
          <div class="mi-author-label">Designed &amp; Developed by</div>
          <div class="mi-author-name">Yihan Yao</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def product_header() -> None:
    st.markdown(
        """
        <div class="mi-hero">
          <div class="mi-hero-copy">
            <div class="mi-kicker">MOBILE GAME<br>MARKET INTELLIGENCE</div>
            <h1 class="mi-title">
              <span class="mi-title-line">移动游戏</span>
              <span class="mi-title-line"><span class="mi-title-mark">市场洞察</span>平台</span>
            </h1>
            <p><span class="accent">Mobile Game Market Intelligence</span></p>
            <p>Designed &amp; Developed by Yihan Yao</p>
            <div class="mi-tags">
              <span class="mi-tag">GOOGLE PLAY</span>
              <span class="mi-tag">MULTI MARKET</span>
              <span class="mi-tag">AI ANALYSIS</span>
              <span class="mi-tag">REPORT READY</span>
            </div>
          </div>
          <div class="mi-hero-art">
            <div class="mi-hero-visual">
              <div class="mi-flow-label">A01 / DATA FLOW</div>
              <div class="mi-flow">
                <div class="mi-flow-step"><span>01</span><span>Google Play</span></div>
                <div class="mi-flow-arrow">↓</div>
                <div class="mi-flow-step"><span>02</span><span>Review Stream</span></div>
                <div class="mi-flow-arrow">↓</div>
                <div class="mi-flow-step"><span>03</span><span>Claude AI</span></div>
                <div class="mi-flow-arrow">↓</div>
                <div class="mi-flow-step"><span>04</span><span>Insight</span></div>
                <div class="mi-flow-arrow">↓</div>
                <div class="mi-flow-step"><span>05</span><span>Dashboard / Report</span></div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def feature_card(index: int, title: str, body: str) -> None:
    st.markdown(
        f"<div class='mi-card' data-index='{index:02d}'><h3>{title}</h3><div class='mi-muted'>{body}</div></div>",
        unsafe_allow_html=True,
    )


def feature_grid(features: list[tuple[str, str]]) -> None:
    cards = "".join(
        f"<div class='mi-card' data-index='{index:02d}'><h3>{title}</h3><div class='mi-muted'>{body}</div></div>"
        for index, (title, body) in enumerate(features, start=1)
    )
    st.markdown(f"<div class='mi-feature-grid'>{cards}</div>", unsafe_allow_html=True)


def section_label(text: str) -> None:
    st.markdown(f"<div class='mi-section-title'>{text}</div>", unsafe_allow_html=True)


def _css_variables(tokens: dict[str, str]) -> str:
    return f":root {{{_variables_block(tokens)}}}"


def _variables_block(tokens: dict[str, str]) -> str:
    return f"""
      --gp-bg: {tokens['background']};
      --gp-sidebar: {tokens['sidebar']};
      --gp-surface: {tokens['surface']};
      --gp-surface-alt: {tokens['surface_alt']};
      --gp-input: {tokens['input']};
      --gp-text: {tokens['text']};
      --gp-muted: {tokens['muted']};
      --gp-border: {tokens['border']};
      --gp-tag: {tokens['tag']};
      --gp-primary: {tokens['primary']};
      --gp-accent-text: {tokens['accent_text']};
      --gp-primary-hover: {tokens.get('primary_hover', '#D6B800')};
      --gp-focus: {tokens.get('focus', 'rgba(244, 228, 9, .30)')};
      --gp-shadow: {tokens.get('shadow', 'none')};
      --gp-card-hover-shadow: {tokens.get('card_hover_shadow', 'none')};
      --gp-cyan: {theme.CYAN};
      --gp-blue: {theme.ELECTRIC_BLUE};
      --gp-danger: {theme.DANGER};
      --gp-grid-1: {tokens.get('grid_1', 'rgba(17,17,17,.035)')};
      --gp-grid-2: {tokens.get('grid_2', 'rgba(17,17,17,.018)')};
      --gp-contour: {tokens.get('contour', 'rgba(150,150,150,.05)')};
      --gp-table-bg: {tokens.get('table_bg', tokens['surface'])};
      --gp-table-head: {tokens.get('table_head', tokens['surface_alt'])};
      --gp-table-cell: {tokens.get('table_cell', tokens['surface'])};
      --gp-table-alt: {tokens.get('table_alt', tokens['surface_alt'])};
      --gp-table-hover: {tokens.get('table_hover', tokens['tag'])};
    """
