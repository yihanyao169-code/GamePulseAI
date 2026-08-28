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
            background:
              repeating-radial-gradient(circle at 12% 8%, transparent 0 28px, var(--gp-contour) 28px 29px),
              repeating-radial-gradient(circle at 108% 82%, transparent 0 36px, var(--gp-contour) 36px 37px),
              var(--gp-sidebar) !important;
            background-size: auto, auto, auto !important;
            color: var(--gp-text) !important;
        }}
        [data-testid="stHeader"] {{box-shadow: none !important; border-bottom: 1px solid var(--gp-border);}}
        .main .block-container {{padding: 2rem clamp(1rem, 4vw, 4rem) 4rem; max-width: 1440px;}}
        [data-testid="stSidebar"] {{border-right: 1px solid var(--gp-border); display:flex; flex-direction:column;}}
        [data-testid="stSidebarContent"] {{display:flex; flex-direction:column; min-height:100%;}}
        h1, h2, h3, h4, h5, h6, p, li, span, label {{
            color: var(--gp-text);
            font-family: Inter, "Noto Sans SC", "Microsoft YaHei", sans-serif;
        }}
        small, [data-testid="stCaptionContainer"], .mi-muted {{color: var(--gp-text-secondary) !important;}}
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
        .mi-group-title small {{color: var(--gp-text-secondary) !important; font-size: 10px; letter-spacing: .08em; font-weight: 800; text-transform: uppercase;}}
        .mi-group-subtitle {{display:none;}}
        .mi-sidebar-brand {{margin: 4px 0 18px;}}
        .mi-sidebar-brand.mi-corner-frame {{padding: 10px 14px; margin: 4px 0 20px;}}
        .mi-sidebar-brand-name {{
            color: var(--gp-text);
            font-size: 21px;
            font-weight: 700;
            line-height: 1.15;
            margin-bottom: 8px;
        }}
        .mi-sidebar-brand-subtitle {{
            color: var(--gp-text-secondary);
            font-size: 12px;
            font-weight: 700;
            letter-spacing: .02em;
            margin: -4px 0 0;
        }}
        .mi-sidebar-footer {{
            margin-top: auto;
            padding: 14px 14px 6px;
            border-top: 1px solid var(--gp-border);
        }}
        .mi-author-label {{
            color: var(--gp-text-secondary);
            font-size: 10px;
            font-weight: 700;
            letter-spacing: .02em;
            line-height: 1.25;
        }}
        .mi-author-name {{
            color: var(--gp-text-secondary);
            font-size: 12px;
            font-weight: 700;
            line-height: 1.25;
            margin-top: 2px;
        }}

        [data-testid="stSidebar"] hr {{margin: 0.55rem 0 !important;}}
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{margin-bottom: 0.15rem !important;}}
        [data-testid="stSidebar"] .stRadio, [data-testid="stSidebar"] .stSelectbox,
        [data-testid="stSidebar"] .stTextInput, [data-testid="stSidebar"] .stNumberInput,
        [data-testid="stSidebar"] .stSlider {{margin-bottom: 0.35rem !important;}}
        div[data-baseweb="select"] {{
            background: var(--gp-input) !important;
        }}
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
        input::placeholder, textarea::placeholder {{color: var(--gp-text-secondary) !important; opacity: 1 !important;}}
        div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within,
        [data-testid="stNumberInput"]:focus-within {{
            outline: 1px solid var(--gp-primary) !important;
            box-shadow: 0 0 0 2px color-mix(in srgb, var(--gp-primary) 30%, transparent) !important;
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

        [class*="st-key-navitem_"] div[data-testid="stButton"] button {{
            justify-content:flex-start !important; text-align:left !important;
            background: transparent !important; border:1px solid transparent !important;
            color: var(--gp-text-secondary) !important; font-weight:700 !important;
            min-height:40px !important; padding-left:12px !important;
        }}
        [class*="st-key-navitem_"] div[data-testid="stButton"] button:hover {{
            border-color: var(--gp-border) !important; color: var(--gp-text) !important;
            background: var(--gp-surface-alt) !important;
        }}
        [class*="st-key-navitem_"][class*="_active"] div[data-testid="stButton"] button {{
            background: var(--gp-surface-alt) !important;
            border-left:3px solid var(--gp-blue) !important;
            color: var(--gp-text) !important;
            font-weight:900 !important;
        }}

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
        [data-baseweb="tag"] svg {{color: var(--gp-text-secondary) !important; fill: var(--gp-text-secondary) !important;}}
        [data-baseweb="tag"]:hover, [data-baseweb="tag"]:hover svg {{
            border-color: var(--gp-primary) !important;
            color: var(--gp-primary) !important;
            fill: var(--gp-primary) !important;
        }}
        [data-baseweb="select"] svg, [data-baseweb="input"] svg {{
            color: var(--gp-text-secondary) !important;
            fill: var(--gp-text-secondary) !important;
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
            border-color: var(--gp-primary); background: var(--gp-surface-alt); color: var(--gp-primary);
        }}
        div.stButton > button[kind="primary"], div.stDownloadButton > button[kind="primary"] {{
            background: var(--gp-yellow) !important; color: var(--gp-on-accent) !important; border-color: var(--gp-yellow) !important;
        }}
        div.stButton > button[kind="primary"] *, div.stDownloadButton > button[kind="primary"] * {{
            color: var(--gp-on-accent) !important;
        }}
        div.stButton > button[kind="primary"]:hover {{
            filter: brightness(.94);
        }}
        div.stButton > button:disabled, div.stDownloadButton > button:disabled {{
            background: var(--gp-surface-alt) !important; color: var(--gp-text-secondary) !important; border-color: var(--gp-border) !important;
        }}
        button:focus, input:focus, textarea:focus {{outline-color: var(--gp-primary) !important; box-shadow: 0 0 0 1px var(--gp-primary) !important;}}

        [data-testid="stMetric"], .mi-card, .mi-insight, .mi-export {{
            background: var(--gp-surface) !important; border: 1px solid var(--gp-border) !important;
            border-radius: 0; color: var(--gp-text);
            box-shadow: var(--gp-shadow);
        }}
        [data-testid="stMetric"] {{padding: 12px 14px;}}
        [data-testid="stMetricLabel"] {{color: var(--gp-text-secondary) !important;}}
        [data-testid="stMetricValue"] {{color: var(--gp-text) !important;}}
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

        [data-testid="stTabs"] [data-baseweb="tab-list"] {{
            gap: 6px; border-bottom: 2px solid var(--gp-border) !important;
        }}
        [data-testid="stTabs"] [data-baseweb="tab"] {{
            height: auto; padding: 10px 20px; border-radius: 8px 8px 0 0;
            background: var(--gp-surface-alt) !important;
            color: var(--gp-text-secondary) !important;
        }}
        [data-testid="stTabs"] [data-baseweb="tab"] p {{
            font-size: 17px !important; font-weight: 800 !important;
        }}
        [data-testid="stTabs"] [data-baseweb="tab"]:hover {{
            color: var(--gp-text) !important; background: var(--gp-surface-alt) !important;
        }}
        [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {{
            background: var(--gp-surface) !important;
            color: var(--gp-primary) !important;
        }}
        [data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
            background: var(--gp-primary) !important; height: 3px !important;
        }}
        [data-testid="stTabs"] [data-baseweb="tab-border"] {{display: none !important;}}
        [data-testid="stTabs"] [data-testid="stTabsContent"] {{
            border: 1px solid var(--gp-border); border-top: none;
            padding: 16px; background: var(--gp-surface);
        }}

        .brand-hero {{
            position: relative; box-sizing: border-box; overflow: hidden;
            border: 1px solid var(--gp-border); background: var(--gp-bg);
            padding: clamp(28px, 3.4vw, 40px) clamp(24px, 4vw, 48px);
            margin-bottom: 40px;
            box-shadow: var(--gp-shadow);
        }}
        .brand-hero__inner {{
            position: relative; z-index: 1;
            display: grid;
            grid-template-columns: minmax(0, 1.25fr) minmax(280px, 0.75fr);
            align-items: center;
            gap: clamp(32px, 5vw, 80px);
            min-height: 150px;
        }}
        .brand-hero__copy, .brand-hero__visual {{min-width: 0; box-sizing: border-box;}}
        .brand-hero__kicker {{
            display:inline-block; margin-bottom:14px; padding-left:12px;
            border-left:4px solid var(--gp-primary);
            color:var(--gp-text-secondary); font-size:12px; font-weight:700;
            line-height:1.2; letter-spacing:.1em;
        }}
        .brand-hero__page {{display:flex; align-items:baseline; gap:12px; margin:0 0 12px;}}
        .brand-hero__page-code {{
            font-size: clamp(28px, 3.4vw, 44px); line-height:1.1; font-weight:900;
            color: var(--gp-text-secondary);
        }}
        .brand-hero__page-name {{
            font-size: clamp(28px, 3.4vw, 44px); line-height:1.1; font-weight:900;
            color: var(--gp-text); letter-spacing:-.01em;
        }}
        .brand-hero__description {{
            font-size:15px; line-height:1.6; margin:0; max-width:520px;
            color: var(--gp-text-secondary);
        }}
        .brand-hero__visual {{position:relative; width:100%; min-height:130px;}}
        .brand-hero__visual-frame {{
            position:relative; height:100%; min-height:130px; box-sizing:border-box;
            border:1px solid var(--gp-border); padding:16px 18px; overflow:hidden;
            background:
              linear-gradient(rgba(17,17,17,.05) 1px, transparent 1px),
              linear-gradient(90deg, rgba(17,17,17,.05) 1px, transparent 1px),
              var(--gp-surface);
            background-size: 22px 22px, 22px 22px, auto;
        }}
        .brand-hero__visual-frame:after {{
            content:""; position:absolute; right:-28px; bottom:-28px;
            width:110px; height:64px; background:var(--gp-primary);
            clip-path: polygon(18% 0, 100% 0, 82% 100%, 0 100%);
            opacity:.9;
        }}
        .brand-hero__visual-code {{
            position:relative; z-index:1; display:block;
            font-size:11px; font-weight:900; letter-spacing:.14em;
            color:var(--gp-text-secondary);
        }}
        .brand-hero__visual-tag {{
            position:relative; z-index:1; display:block; margin-top:12px;
            font-size:19px; font-weight:900; letter-spacing:.04em;
            color:var(--gp-text); white-space:nowrap;
        }}
        .brand-hero__visual-nodes {{position:relative; z-index:1; display:flex; gap:8px; margin-top:16px;}}
        .brand-hero__node {{width:8px; height:8px; display:inline-block;}}
        .brand-hero__node--blue {{background:var(--gp-blue);}}
        .brand-hero__node--magenta {{background:var(--gp-magenta);}}
        @media (max-width: 900px) {{
          .brand-hero__inner {{grid-template-columns: 1fr;}}
          .brand-hero__visual {{min-height: 120px;}}
        }}
        @media (max-width: 520px) {{
          .brand-hero__page-name {{white-space:normal;}}
        }}
        @media (prefers-reduced-motion: reduce) {{
          .landing-page *, .brand-hero * {{
            animation: none !important;
            transition: none !important;
          }}
        }}

        .home-page {{position: relative;}}
        .st-key-home_hero_grid {{
            position: relative; overflow: hidden; box-sizing: border-box;
            container-type: inline-size;
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
        .st-key-home_hero_grid:after {{
            content:""; position:absolute; right:-54px; bottom:-44px;
            width:220px; height:120px; background:var(--gp-primary);
            clip-path: polygon(18% 0, 100% 0, 82% 100%, 0 100%);
            opacity:.9; z-index:0; pointer-events:none;
        }}
        .st-key-home_hero_grid div[data-testid="stHorizontalBlock"] {{
            position: relative; z-index: 1;
            align-items: center;
            gap: clamp(26px, 5vw, 64px) !important;
            flex-wrap: nowrap !important;
        }}
        .st-key-home_hero_grid div[data-testid="column"], .st-key-home_hero_grid div[data-testid="stColumn"] {{min-width: 0;}}
        .mi-hero-copy, .mi-hero-art {{min-width: 0; box-sizing: border-box;}}
        .mi-kicker {{
            display:inline-block; margin-bottom:18px; padding-left:12px;
            border-left:4px solid var(--gp-primary);
            color:var(--gp-text-secondary); font-size:12px; font-weight:900;
            line-height:1.2; letter-spacing:.16em;
        }}
        .mi-hero-copy h1.mi-title {{
            font-size: clamp(2.65rem, 5.2vw, 6.2rem);
            line-height: .98; margin: 0 0 20px; color: var(--gp-text);
            letter-spacing: -.035em; font-weight: 900;
            overflow-wrap: normal; word-break: keep-all;
            max-width: 820px;
        }}
        .mi-title-line {{display:block; white-space:nowrap;}}
        .mi-title-mark {{
            display:inline-block; position:relative; padding:0 .08em;
            color:var(--gp-on-accent); background:var(--gp-primary);
        }}
        .mi-hero-copy .accent {{color: var(--gp-text); font-weight:800; letter-spacing:.04em;}}
        .mi-hero-copy p {{font-size: 16px; margin: 0 0 8px; color: var(--gp-text-secondary); max-width: 620px;}}
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
            position:absolute; left:18px; top:14px; color:var(--gp-text-secondary);
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
        .mi-flow-step span:last-child {{
            font-size:13px; color:var(--gp-text); font-weight:900;
            white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
        }}
        .mi-flow-arrow {{text-align:center; color:var(--gp-text-secondary); font-size:11px; line-height:1; margin:-5px 0;}}
        .mi-scroll-hint {{
            position:relative; z-index:2; margin: 20px auto 0; width:fit-content; max-width:100%;
            display:flex; flex-direction:column; align-items:center; gap:6px;
            text-decoration:none !important; cursor:pointer; padding:2px 10px;
        }}
        .mi-scroll-hint__text {{
            font-size:11px; font-weight:800; letter-spacing:.06em;
            color:var(--gp-text-secondary); white-space:nowrap;
        }}
        .mi-scroll-hint__arrow {{
            color:var(--gp-primary); font-size:17px; line-height:1; font-weight:900;
            animation: mi-scroll-bounce 1.8s ease-in-out infinite;
        }}
        @keyframes mi-scroll-bounce {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(4px); }}
        }}
        @media (prefers-reduced-motion: reduce) {{
          .mi-scroll-hint__arrow {{ animation: none !important; }}
        }}
        .st-key-home_actions {{margin-top: 28px;}}
        .st-key-home_actions div[data-testid="stHorizontalBlock"] {{gap: 24px !important;}}
        .st-key-home_actions div[data-testid="stButton"] button {{
            background: #ffffff !important; color: #111111 !important;
            border: 1px solid #111111 !important; font-weight: 800 !important;
        }}
        .st-key-home_actions div[data-testid="stButton"] button:hover {{
            filter: brightness(.96);
        }}
        .st-key-home_workspace_action div[data-testid="stButton"] button {{
            background: var(--gp-yellow) !important; color: var(--gp-on-accent) !important;
            border: 1px solid var(--gp-on-accent) !important; font-weight: 800 !important;
        }}
        .st-key-home_workspace_action div[data-testid="stButton"] button:hover {{
            filter: brightness(.94);
        }}
        @container (max-width: 700px) {{
          .st-key-home_hero_grid div[data-testid="stHorizontalBlock"] {{flex-wrap: wrap !important;}}
          .st-key-home_hero_grid div[data-testid="column"], .st-key-home_hero_grid div[data-testid="stColumn"] {{min-width: 100% !important; flex: 1 1 100% !important;}}
          .mi-hero-copy h1.mi-title {{font-size: clamp(2.5rem, 8vw, 5rem);}}
          .mi-hero-visual {{min-height: 260px; aspect-ratio: 16 / 8;}}
        }}
        @media (max-width: 768px) {{
          .st-key-home_hero_grid {{padding: clamp(18px, 6vw, 28px); gap:22px; min-height:0;}}
          .mi-hero-copy h1.mi-title {{font-size: clamp(2rem, 13vw, 3.4rem); line-height:1.02;}}
          .mi-hero-visual {{min-height: 230px; aspect-ratio: 4 / 3;}}
          .mi-flow {{inset:42px 14px 18px;}}
          .mi-flow-step {{grid-template-columns:36px 1fr auto; padding:8px 9px;}}
        }}
        @media (max-width: 640px) {{
          .mi-hero-copy h1.mi-title {{white-space: normal;}}
        }}
        .mi-feature-grid {{display:grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap:0; margin:18px 0 58px; border:1px solid var(--gp-border); background:var(--gp-surface);}}
        .mi-card {{
            display:block; position:relative; padding:18px 16px 22px; min-height:154px; margin:0;
            text-decoration:none !important; transition: border-color 200ms ease;
            border-width:0 1px 0 0 !important; box-shadow:none !important; cursor:default;
        }}
        .mi-card:nth-child(6n) {{border-right:0 !important;}}
        .mi-card:before {{content: attr(data-index); color:var(--gp-text-secondary); font-size:12px; font-weight:900;}}
        .mi-card:after {{content:""; position:absolute; right:0; bottom:0; width:42px; height:5px; background:var(--gp-primary);}}
        .mi-card h3 {{font-size:16px; margin:12px 0 10px; color:var(--gp-text); font-weight:900; line-height:1.22;}}
        .mi-card .mi-muted {{font-size:12px; line-height:1.55;}}
        .mi-section-title {{font-size:18px; font-weight:900; color:var(--gp-text); margin:54px 0 16px; letter-spacing:.06em; border-bottom:3px solid var(--gp-primary); display:inline-block; padding-bottom:5px;}}
        .mi-workflow {{display:flex; flex-wrap:nowrap; gap:12px; margin:10px 0 42px; align-items:stretch;}}
        .mi-step {{
            position:relative; display:flex; align-items:center; justify-content:center; min-height:54px;
            flex:1 1 0; min-width:0; margin:0; padding:10px 12px; border-radius:0;
            border:1px solid var(--gp-border); background:var(--gp-surface); color:var(--gp-text-secondary);
            font-size:12px; font-weight:900; letter-spacing:.04em; text-align:center;
        }}
        .mi-step:not(:last-child):after {{
            content:""; position:absolute; right:-10px; top:50%; width:14px; height:1px;
            background:var(--gp-text); z-index:2;
        }}
        .mi-step-active {{background:var(--gp-primary); border-color:var(--gp-primary); color:var(--gp-on-accent);}}
        .mi-step-done {{background:var(--gp-surface-alt); border-color:var(--gp-primary); color:var(--gp-text-secondary);}}
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
        .mi-report-item small {{display:block; margin-top:4px; color:var(--gp-text-secondary) !important; word-break:normal; overflow-wrap:break-word; line-height:1.65;}}
        .insight-grid {{display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:24px; align-items:start; margin:8px 0 24px;}}
        .insight-column {{min-width:0;}}
        .insight-column h3 {{white-space:nowrap; word-break:keep-all; overflow-wrap:normal; margin:0 0 14px; color:var(--gp-text); font-size:1.17em;}}
        .insight-column .mi-report-list {{margin-bottom:0;}}
        .recommendation-section {{margin:24px 0 12px;}}
        .priority-section-title {{white-space:nowrap; word-break:keep-all; overflow-wrap:normal; margin:24px 0 12px; color:var(--gp-text); font-size:1.08rem; font-weight:900;}}
        .recommendation-grid {{display:grid; grid-template-columns:repeat(2, minmax(320px, 1fr)); gap:18px;}}
        .recommendation-card {{min-width:0; padding:18px 20px; background:var(--gp-surface); border:1px solid var(--gp-border); border-left:4px solid var(--gp-magenta); color:var(--gp-text);}}
        .recommendation-card h4 {{white-space:normal; word-break:keep-all; overflow-wrap:break-word; margin:0 0 10px; color:var(--gp-text);}}
        .recommendation-card p {{word-break:normal; overflow-wrap:break-word; line-height:1.65; margin:8px 0 0; color:var(--gp-text-secondary);}}
        div[data-testid="stButton"] button, div[data-testid="stDownloadButton"] button {{
            min-width:180px; white-space:nowrap !important; word-break:keep-all !important; overflow-wrap:normal !important;
        }}
        .mi-score-panel {{display:grid; grid-template-columns: 240px 1fr; gap:18px; align-items:center; background:var(--gp-surface); border:1px solid var(--gp-border); padding:18px; margin:8px 0 8px;}}
        .mi-score-panel b {{display:block; font-size:42px; line-height:1; color:var(--gp-text);}}
        .mi-score-panel span {{display:inline-block; margin-top:8px; padding:4px 10px; background:var(--gp-yellow); color:var(--gp-on-accent); font-weight:900;}}
        .mi-score-panel strong {{display:block; color:var(--gp-text); margin-bottom:6px;}}
        .mi-eval-panel {{background:var(--gp-surface); border:1px solid var(--gp-border); padding:18px; margin:8px 0 16px;}}
        .mi-eval-head {{display:flex; justify-content:space-between; align-items:flex-start; gap:18px; border-bottom:1px solid var(--gp-border); padding-bottom:14px; margin-bottom:14px;}}
        .mi-eval-title {{font-size:15px; color:var(--gp-text-secondary); font-weight:900; letter-spacing:.08em;}}
        .mi-eval-score {{font-size:54px; line-height:.95; color:var(--gp-text); font-weight:900;}}
        .mi-eval-score small {{font-size:18px; color:var(--gp-text-secondary) !important;}}
        .mi-eval-grade {{display:inline-block; background:var(--gp-yellow); color:var(--gp-on-accent); font-size:16px; font-weight:900; padding:5px 12px; margin-top:8px;}}
        .mi-eval-grid {{display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:10px; margin: 12px 0;}}
        .mi-eval-metric {{border:1px solid var(--gp-border); background:var(--gp-surface-alt); padding:13px; min-height:98px;}}
        .mi-eval-metric strong {{display:block; color:var(--gp-text-secondary); font-size:13px; margin-bottom:9px;}}
        .mi-eval-metric b {{display:block; color:var(--gp-text); font-size:30px; line-height:1;}}
        .mi-eval-summary {{border-left:4px solid var(--gp-primary); padding:10px 12px; background:var(--gp-surface-alt); color:var(--gp-text); margin-top:12px;}}
        .mi-data-scope-card {{background:var(--gp-surface); border:1px solid var(--gp-border); padding:16px 18px; margin:4px 0 18px;}}
        .mi-data-scope-grid {{display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:10px 16px; margin-top:12px;}}
        .mi-data-scope-row {{border-left:3px solid var(--gp-primary); background:var(--gp-surface-alt); padding:10px 12px; min-width:0;}}
        .mi-data-scope-row strong {{display:block; color:var(--gp-text-secondary); font-size:12px; margin-bottom:4px; white-space:nowrap;}}
        .mi-data-scope-row span {{display:block; color:var(--gp-text); font-size:14px; font-weight:700; line-height:1.5; word-break:normal; overflow-wrap:break-word;}}
        .mi-data-scope-row small {{display:block; color:var(--gp-text-secondary); font-size:12px; line-height:1.45; margin-top:4px;}}
        .mi-data-scope-note {{margin-top:12px; color:var(--gp-text-secondary); font-size:13px; line-height:1.55;}}
        .mi-eval-breakdown {{display:grid; gap:8px; margin:10px 0;}}
        .mi-eval-row {{display:grid; grid-template-columns:1.2fr .55fr .45fr .55fr; gap:8px; align-items:center; border:1px solid var(--gp-border); background:var(--gp-surface); padding:8px 10px; color:var(--gp-text);}}
        .mi-sentiment-grid {{display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:12px; margin:8px 0 24px;}}
        .mi-sentiment-card {{background:var(--gp-surface); border:1px solid var(--gp-border); padding:14px;}}
        .mi-sentiment-card b {{display:block; font-size:13px; color:var(--gp-text-secondary);}}
        .mi-sentiment-card span {{display:block; margin-top:8px; font-size:26px; font-weight:900; color:var(--gp-text);}}
        .mi-sentiment-card:before {{content:""; display:block; width:26px; height:4px; background:var(--gp-primary); margin-bottom:10px;}}
        .mi-progress-panel {{
            max-height: 140px; margin: 14px 0 20px; padding: 14px 16px;
            border: 1px solid var(--gp-border); background: var(--gp-surface);
            box-shadow: var(--gp-shadow);
        }}
        .mi-progress-head {{display:flex; justify-content:space-between; align-items:center; gap:16px; margin-bottom:10px;}}
        .mi-progress-head strong {{font-size:13px; letter-spacing:.08em; color:var(--gp-text);}}
        .mi-progress-head span {{font-size:13px; font-weight:900; color:var(--gp-text);}}
        .mi-progress-track {{display:grid; grid-template-columns:repeat(8, 1fr); gap:5px; margin-bottom:10px;}}
        .mi-progress-segment {{height:9px; background:var(--gp-border); display:block;}}
        .mi-progress-segment.is-done {{background:color-mix(in srgb, var(--gp-primary) 52%, var(--gp-text));}}
        .mi-progress-segment.is-active {{background:var(--gp-primary);}}
        .mi-progress-segment.is-error {{background:var(--gp-magenta); outline:2px solid var(--gp-magenta);}}
        .mi-progress-meter {{height:8px; background:var(--gp-border); margin:0 0 9px; overflow:hidden;}}
        .mi-progress-meter span {{display:block; height:100%; background:var(--gp-primary);}}
        .mi-progress-current {{font-size:13px; font-weight:900; color:var(--gp-text);}}
        .mi-progress-detail {{margin-top:5px; color:var(--gp-text-secondary); font-size:12px;}}
        .mi-method-steps {{
            display:grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap:10px;
            margin: 8px 0 18px;
        }}
        .mi-report-link {{
            display:inline-flex; margin: 0 0 18px; padding:7px 10px; border:1px solid var(--gp-primary);
            color:var(--gp-primary) !important; background:var(--gp-surface); text-decoration:none !important; font-weight:900; font-size:12px;
        }}
        .mi-chart-wrap {{
            width:100%; margin:0; border:1px solid var(--gp-border); background:var(--gp-surface);
            padding:12px; overflow:hidden;
        }}
        .mi-chart-wrap img, .mi-chart-wrap canvas, .mi-chart-wrap svg {{width:100%; height:auto; object-fit:contain; object-position:center; display:block; margin:0;}}
        @media (max-width: 1100px) {{
          [data-testid="stHorizontalBlock"] {{flex-wrap:wrap !important;}}
          [data-testid="stHorizontalBlock"] > [data-testid="column"], [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{min-width:100% !important; flex:1 1 100% !important;}}
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
          .brand-hero {{padding: clamp(18px, 6vw, 28px);}}
          .brand-hero__inner {{gap:22px;}}
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

        .mi-corner-frame {{position:relative;}}
        .mi-corner-frame:before {{
            content:""; position:absolute; inset:0; z-index:2; pointer-events:none;
            background-repeat: no-repeat;
            background-image:
              linear-gradient(var(--gp-blue), var(--gp-blue)), linear-gradient(var(--gp-blue), var(--gp-blue)),
              linear-gradient(var(--gp-blue), var(--gp-blue)), linear-gradient(var(--gp-blue), var(--gp-blue)),
              linear-gradient(var(--gp-blue), var(--gp-blue)), linear-gradient(var(--gp-blue), var(--gp-blue)),
              linear-gradient(var(--gp-blue), var(--gp-blue)), linear-gradient(var(--gp-blue), var(--gp-blue));
            background-size: 14px 2px, 2px 14px, 14px 2px, 2px 14px, 14px 2px, 2px 14px, 14px 2px, 2px 14px;
            background-position:
              top 8px left 8px, top 8px left 8px,
              top 8px right 8px, top 8px right 8px,
              bottom 8px left 8px, bottom 8px left 8px,
              bottom 8px right 8px, bottom 8px right 8px;
            opacity:.85;
        }}
        @keyframes gp-boot-in {{
          from {{opacity:0; transform:translateY(10px);}}
          to {{opacity:1; transform:translateY(0);}}
        }}
        .mi-sidebar-brand-name, .mi-author-label, .mi-author-name {{
            animation: gp-boot-in .5s cubic-bezier(.16,1,.3,1) both;
        }}
        .mi-author-label {{animation-delay:.08s;}}
        .mi-author-name {{animation-delay:.14s;}}

        @keyframes gp-landing-flash {{
          0% {{opacity:0; background:#111111;}}
          8% {{opacity:.85; background:#111111;}}
          16% {{opacity:0;}}
          24% {{opacity:.55; background:var(--gp-primary);}}
          34% {{opacity:0;}}
          100% {{opacity:0;}}
        }}
        @keyframes gp-landing-scan {{
          0% {{opacity:0;}}
          30% {{opacity:.9;}}
          70% {{opacity:.5;}}
          100% {{opacity:0;}}
        }}
        @keyframes gp-landing-title-glitch {{
          0% {{opacity:0; transform:translate(0,0); clip-path: inset(0 0 0 0);}}
          10% {{opacity:1; transform:translate(-6px,0); clip-path: inset(0 0 0 0);}}
          20% {{opacity:0; transform:translate(4px,0);}}
          32% {{opacity:1; transform:translate(3px,-2px); clip-path: inset(0 0 40% 0);}}
          45% {{opacity:.25; transform:translate(-3px,1px); clip-path: inset(30% 0 0 0);}}
          60% {{opacity:1; transform:translate(2px,0); clip-path: inset(0 0 0 0);}}
          100% {{opacity:1; transform:translate(0,0); clip-path: inset(0 0 0 0);}}
        }}
        @keyframes gp-landing-ai-in {{
          0% {{opacity:0; transform:translate(40px,0) rotate(-2deg);}}
          100% {{opacity:1; transform:translate(0,0) rotate(-2deg);}}
        }}
        @keyframes gp-landing-float {{
          0%, 100% {{transform:translate(0,0) rotate(-2deg);}}
          50% {{transform:translate(0,-3px) rotate(-2deg);}}
        }}
        @keyframes gp-contour-draw {{
          0% {{opacity:0; stroke-dashoffset:1400;}}
          15% {{opacity:.34;}}
          100% {{opacity:.34; stroke-dashoffset:0;}}
        }}
        @keyframes gp-contour-node {{
          0%, 60% {{opacity:0; transform:scale(.4);}}
          100% {{opacity:1; transform:scale(1);}}
        }}
        @keyframes gp-panel-in-left {{
          0% {{opacity:0; transform: translate(-46px, 18px) rotate(-2deg);}}
          100% {{opacity:1; transform: translate(0,0) rotate(0deg);}}
        }}
        @keyframes gp-panel-in-right {{
          0% {{opacity:0; transform: translate(46px, 12px) rotate(2deg);}}
          100% {{opacity:1; transform: translate(0,0) rotate(0deg);}}
        }}
        @keyframes gp-panel-in-bottom {{
          0% {{opacity:0; transform: translate(0, 34px) rotate(1deg);}}
          100% {{opacity:1; transform: translate(0,0) rotate(0deg);}}
        }}

        .st-key-boot_screen {{
            position: relative; overflow: hidden;
            min-height: 62vh; box-sizing: border-box;
            display:flex; flex-direction:column; justify-content:center;
            padding: clamp(32px, 6vw, 72px) clamp(24px, 6vw, 64px);
            border: 1px solid var(--gp-border);
            background:
              radial-gradient(circle at 72% 24%, rgba(241, 230, 0, .16), transparent 30%),
              linear-gradient(var(--gp-grid-1) 1px, transparent 1px),
              linear-gradient(90deg, var(--gp-grid-1) 1px, transparent 1px),
              var(--gp-bg);
            background-size: auto, 42px 42px, 42px 42px, auto;
        }}
        .st-key-boot_actions {{
            position: relative; z-index:1;
            display:flex; justify-content:center;
            animation: gp-boot-in .4s cubic-bezier(.16,1,.3,1) 1.75s both;
        }}
        .st-key-boot_screen div[data-testid="stButton"], .st-key-boot_screen div[data-testid="stHorizontalBlock"] {{
            position: relative; z-index: 1;
        }}
        .st-key-boot_screen div[data-testid="stElementContainer"]:has(.landing-page) {{
            position: static !important;
        }}
        .landing-page__flash {{
            position:absolute; inset:0; z-index:5; pointer-events:none;
            opacity:0; background:#111111;
            animation: gp-landing-flash .35s steps(1,end) both;
        }}
        .landing-page__scan {{
            position:absolute; inset:0; z-index:4; pointer-events:none;
            opacity:0;
            background-repeat: no-repeat;
            background-image:
              linear-gradient(var(--gp-blue), var(--gp-blue)), linear-gradient(var(--gp-blue), var(--gp-blue)),
              linear-gradient(var(--gp-blue), var(--gp-blue)), linear-gradient(var(--gp-blue), var(--gp-blue)),
              linear-gradient(var(--gp-blue), var(--gp-blue)), linear-gradient(var(--gp-blue), var(--gp-blue)),
              linear-gradient(var(--gp-blue), var(--gp-blue)), linear-gradient(var(--gp-blue), var(--gp-blue));
            background-size: 18px 2px, 2px 18px, 18px 2px, 2px 18px, 18px 2px, 2px 18px, 18px 2px, 2px 18px;
            background-position:
              top 10px left 10px, top 10px left 10px,
              top 10px right 10px, top 10px right 10px,
              bottom 10px left 10px, bottom 10px left 10px,
              bottom 10px right 10px, bottom 10px right 10px;
            animation: gp-landing-scan .35s steps(1,end) both;
        }}
        .landing-page__contours {{
            position:absolute; inset:0; z-index:0; width:100%; height:100%;
            pointer-events:none; overflow:hidden;
        }}
        .landing-contour {{
            fill:none; stroke:var(--gp-border); stroke-width:2;
            stroke-dasharray:1400; stroke-dashoffset:1400; opacity:0;
            animation: gp-contour-draw 1.1s ease-out .45s both;
        }}
        .landing-contour-2 {{animation-delay:.6s; stroke:color-mix(in srgb, var(--gp-blue) 45%, var(--gp-border));}}
        .landing-contour-3 {{animation-delay:.75s;}}
        .landing-contour-4 {{animation-delay:.9s; stroke:color-mix(in srgb, var(--gp-magenta) 40%, var(--gp-border));}}
        .landing-contour-node {{
            fill:var(--gp-blue); opacity:0; transform-origin:center;
            animation: gp-contour-node .3s ease-out 1.05s both;
        }}
        .landing-contour-node-2 {{fill:var(--gp-magenta); animation-delay:1.15s;}}
        .landing-hero {{position:relative; z-index:1; text-align:center; max-width:920px; margin:0 auto;}}
        .landing-hero__badge {{
            display:inline-block; margin-bottom:18px; padding-left:12px;
            border-left:4px solid var(--gp-primary); color:var(--gp-text-secondary);
            font-size:12px; font-weight:900; letter-spacing:.16em;
            animation: gp-boot-in .3s cubic-bezier(.16,1,.3,1) .05s both;
        }}
        .landing-hero__title {{
            position:relative; margin:0 0 10px;
            font-size: clamp(78px, 10vw, 142px);
            line-height: 0.82; font-weight: 950; letter-spacing: -0.065em;
            color: var(--gp-text);
            white-space: nowrap;
        }}
        .landing-hero__title-ghost {{
            position:absolute; inset:0; z-index:0;
            color: transparent;
            -webkit-text-stroke: 1px color-mix(in srgb, var(--gp-text) 10%, transparent);
            transform: scale(1.08);
            pointer-events:none; user-select:none;
        }}
        .landing-hero__title-main {{
            position:relative; z-index:1; display:inline-block;
            animation: gp-landing-title-glitch .55s steps(1,end) .25s both;
        }}
        .landing-hero__title-ai {{
            position:relative; z-index:1; display:inline-block;
            margin-left:.08em; padding: 0 .12em; background:var(--gp-yellow); color:var(--gp-on-accent);
            animation:
              gp-landing-ai-in .5s cubic-bezier(.16,1,.3,1) .55s both,
              gp-landing-float 5s ease-in-out 1.2s infinite;
        }}
        .landing-hero__subtitle {{
            position:relative; z-index:1;
            font-size: clamp(30px, 3.2vw, 44px); font-weight:900; color:var(--gp-text);
            margin: 0 0 18px;
            animation: gp-boot-in .3s cubic-bezier(.16,1,.3,1) .65s both;
        }}
        .landing-hero__value {{
            position:relative; z-index:1;
            font-size: clamp(17px,1.9vw,21px); font-weight:700; color:var(--gp-text);
            width: fit-content; max-width:680px;
            line-height:1.6; margin: 0 auto 30px !important;
            text-align: center !important;
            animation: gp-boot-in .4s cubic-bezier(.16,1,.3,1) .9s both;
        }}
        .landing-panels {{
            position: relative; z-index:1;
            display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:16px;
            max-width: 980px; margin: 6px auto 8px;
        }}
        .landing-panel {{
            position: relative; text-align:left;
            border:1px solid var(--gp-border); background:var(--gp-surface);
            padding:16px 16px 22px; min-height:110px;
            box-shadow: var(--gp-shadow);
        }}
        .landing-panel:after {{content:""; position:absolute; right:0; bottom:0; width:34px; height:4px; background:var(--gp-primary);}}
        .landing-panel__index {{display:block; color:var(--gp-accent-text); font-size:12px; font-weight:900; margin-bottom:8px;}}
        .landing-panel__title {{margin:0 0 4px; font-size:14px; font-weight:900; color:var(--gp-text);}}
        .landing-panel__code {{display:block; font-size:11px; font-weight:800; letter-spacing:.1em; color:var(--gp-text-secondary);}}
        .landing-panel--left {{animation: gp-panel-in-left .55s cubic-bezier(.16,1,.3,1) .85s both;}}
        .landing-panel--right {{animation: gp-panel-in-right .55s cubic-bezier(.16,1,.3,1) 1.05s both;}}
        .landing-panel--bottom {{animation: gp-panel-in-bottom .55s cubic-bezier(.16,1,.3,1) 1.25s both;}}
        .st-key-boot_secondary_action div[data-testid="stButton"] button {{
            border-color: transparent !important; background: transparent !important;
            color: var(--gp-text-secondary) !important; font-weight:700 !important;
            text-decoration: underline;
        }}
        .st-key-boot_secondary_action div[data-testid="stButton"] button:hover {{
            color: var(--gp-text) !important;
        }}

        @media (max-width: 720px) {{
          .landing-panels {{grid-template-columns: 1fr;}}
        }}
        @media (max-width: 640px) {{
          .landing-hero__title {{font-size: clamp(44px, 14vw, 72px); white-space: normal; line-height: .95;}}
          .landing-hero__title-ghost {{display:none;}}
        }}
        @media (max-width: 768px) {{
          .st-key-boot_actions div[data-testid="stHorizontalBlock"] {{
              flex-direction: column; align-items: center; width: min(90%, 360px); margin: 0 auto;
          }}
          .st-key-boot_actions div[data-testid="column"], .st-key-boot_actions div[data-testid="stColumn"] {{width:100% !important;}}
        }}

        @media (prefers-reduced-motion: reduce) {{
          .mi-sidebar-brand-name, .mi-author-label, .mi-author-name {{
              animation: none !important;
          }}
          .landing-page *, .landing-page, .st-key-boot_screen *,
          .home-page *, .st-key-home_hero_grid, .st-key-home_hero_grid * {{
              animation: none !important;
              transition: none !important;
          }}
          .landing-page__flash, .landing-page__scan {{
              opacity: 0 !important;
          }}
          .landing-contour, .landing-contour-node {{
              opacity: .34 !important;
          }}
        }}
        .gp-anim-skip, .gp-anim-skip * {{
            animation: none !important;
        }}
        .gp-anim-skip .landing-page__flash, .gp-anim-skip .landing-page__scan {{
            opacity: 0 !important;
        }}
        .gp-anim-skip .landing-contour, .gp-anim-skip .landing-contour-node {{
            opacity: .34 !important;
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
        <div class="mi-sidebar-brand mi-corner-frame">
          <div class="mi-sidebar-brand-name">GamePulse AI</div>
          <div class="mi-sidebar-brand-subtitle">游戏市场决策</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_footer() -> None:
    st.markdown(
        """
        <div class="mi-sidebar-footer">
          <div class="mi-author-label">Designed &amp; Developed by</div>
          <div class="mi-author-name">Yihan Yao</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def brand_hero(page_code: str, page_name: str, description: str, english_tag: str) -> None:
    st.markdown(
        f"""
        <div class="brand-hero">
          <div class="brand-hero__inner">
            <div class="brand-hero__copy">
              <div class="brand-hero__kicker">GamePulse AI / {english_tag}</div>
              <div class="brand-hero__page">
                <span class="brand-hero__page-code">{page_code}</span>
                <span class="brand-hero__page-name">{page_name}</span>
              </div>
              <p class="brand-hero__description">{description}</p>
            </div>
            <div class="brand-hero__visual">
              <div class="brand-hero__visual-frame">
                <span class="brand-hero__visual-code">{page_code} / {english_tag}</span>
                <span class="brand-hero__visual-tag">{english_tag}</span>
                <div class="brand-hero__visual-nodes">
                  <span class="brand-hero__node"></span>
                  <span class="brand-hero__node brand-hero__node--blue"></span>
                  <span class="brand-hero__node brand-hero__node--magenta"></span>
                </div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def home_hero():
    with st.container(key="home_hero_grid"):
        col_copy, col_art = st.columns([1.08, 1.0])
        st.markdown(
            """
            <a class="mi-scroll-hint" href="#core-capability-matrix" aria-label="向下探索 · 核心能力与分析流程">
              <span class="mi-scroll-hint__text">向下探索 · 核心能力与分析流程</span>
              <span class="mi-scroll-hint__arrow" aria-hidden="true">&#8595;</span>
            </a>
            """,
            unsafe_allow_html=True,
        )
    col_copy.markdown(
        """
        <div class="mi-hero-copy">
          <div class="mi-kicker">MOBILE GAME<br>MARKET INTELLIGENCE</div>
          <h1 class="mi-title">
            <span class="mi-title-line">移动游戏</span>
            <span class="mi-title-line"><span class="mi-title-mark">市场决策</span>工具</span>
          </h1>
          <p><span class="accent">GamePulse<span class="mi-title-mark">AI</span></span>&emsp;MOBILE GAME MARKET INTELLIGENCE</p>
          <p>从玩家评论中提取真实反馈，比较不同市场表现，辅助游戏市场决策。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_art.markdown(
        """
        <div class="mi-hero-art">
          <div class="mi-hero-visual">
            <div class="mi-flow-label">DATA FLOW</div>
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
        """,
        unsafe_allow_html=True,
    )
    return col_copy


def boot_background_layer() -> None:
    st.markdown(
        """
        <div class="landing-page">
          <div class="landing-page__flash" aria-hidden="true"></div>
          <div class="landing-page__scan" aria-hidden="true"></div>
          <svg class="landing-page__contours" viewBox="0 0 1000 600" preserveAspectRatio="none" aria-hidden="true">
            <path class="landing-contour landing-contour-1" d="M-20,120 C180,60 320,220 520,140 C720,60 860,180 1020,110" />
            <path class="landing-contour landing-contour-2" d="M-20,260 C160,320 340,180 540,260 C740,340 880,220 1020,280" />
            <path class="landing-contour landing-contour-3" d="M-20,400 C200,460 380,340 560,400 C760,460 860,360 1020,420" />
            <path class="landing-contour landing-contour-4" d="M-20,520 C220,470 400,560 600,500 C780,450 880,540 1020,500" />
            <circle class="landing-contour-node landing-contour-node-1" cx="320" cy="220" r="5" />
            <circle class="landing-contour-node landing-contour-node-2" cx="740" cy="340" r="5" />
          </svg>
        </div>
        """,
        unsafe_allow_html=True,
    )


def boot_hero() -> None:
    st.markdown(
        """
        <div class="landing-page">
          <div class="landing-hero">
            <div class="landing-hero__badge">GAMEPULSE AI &middot; MARKET INTELLIGENCE</div>
            <h1 class="landing-hero__title">
              <span class="landing-hero__title-ghost" aria-hidden="true">GamePulse AI</span>
              <span class="landing-hero__title-main">GamePulse</span><span class="landing-hero__title-ai">AI</span>
            </h1>
            <p class="landing-hero__subtitle">游戏市场决策</p>
            <p class="landing-hero__value">从玩家评论中提取真实反馈，比较不同市场表现，辅助游戏市场判断。</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def boot_panels(items: list[tuple[str, str, str]]) -> None:
    directions = ["left", "right", "bottom"]
    cards = "".join(
        f"<div class='landing-panel landing-panel--{directions[i % 3]}'>"
        f"<span class='landing-panel__index'>{index}</span>"
        f"<div class='landing-panel__title'>{title}</div>"
        f"<span class='landing-panel__code'>{code}</span>"
        f"</div>"
        for i, (index, title, code) in enumerate(items)
    )
    st.markdown(f"<div class='landing-page'><div class='landing-panels'>{cards}</div></div>", unsafe_allow_html=True)


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


def section_label(text: str, anchor_id: str | None = None) -> None:
    anchor = f" id='{anchor_id}'" if anchor_id else ""
    st.markdown(f"<div class='mi-section-title'{anchor}>{text}</div>", unsafe_allow_html=True)


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
      --gp-text-secondary: {tokens['text_secondary']};
      --gp-border: {tokens['border']};
      --gp-tag: {tokens['tag']};
      --gp-primary: {tokens['primary']};
      --gp-accent-text: {tokens['accent_text']};
      --gp-primary-hover: {tokens['primary_hover']};
      --gp-focus: {tokens['focus']};
      --gp-blue: {theme.GP_BLUE};
      --gp-yellow: {theme.GP_YELLOW};
      --gp-magenta: {theme.GP_MAGENTA};
      --gp-on-accent: {theme.GP_TEXT};
      --gp-shadow: {tokens['shadow']};
      --gp-card-hover-shadow: {tokens['card_hover_shadow']};
      --gp-grid-1: {tokens['grid_1']};
      --gp-grid-2: {tokens['grid_2']};
      --gp-contour: {tokens['contour']};
      --gp-table-bg: {tokens['table_bg']};
      --gp-table-head: {tokens['table_head']};
      --gp-table-cell: {tokens['table_cell']};
      --gp-table-alt: {tokens['table_alt']};
      --gp-table-hover: {tokens['table_hover']};
    """
