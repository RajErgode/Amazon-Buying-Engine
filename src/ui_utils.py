"""
Shared UI helpers — brand colours, CSS, sidebar, logo.
Import apply_theme() and render_sidebar() at the top of every page.
"""

import os
from pathlib import Path
import streamlit as st

# ── Brand palette ─────────────────────────────────────────────────────────────
ORANGE = "#F47920"
NAVY   = "#1B3A5C"
WHITE  = "#FFFFFF"
LIGHT  = "#F0F2F6"
GREEN  = "#27AE60"
RED    = "#E74C3C"
AMBER  = "#F39C12"

LOGO_PATH = Path(__file__).parent.parent / "assets" / "logo.png"


# ── Global CSS ────────────────────────────────────────────────────────────────
_CSS = f"""
<style>
/* ── Page header banner ─────────────────────────────────── */
.vv-header {{
    background: linear-gradient(135deg, {NAVY} 0%, #2E5E8E 100%);
    color: {WHITE};
    padding: 22px 28px;
    border-radius: 12px;
    margin-bottom: 28px;
}}
.vv-header h1 {{ margin: 0; font-size: 1.6rem; font-weight: 700; color: {WHITE}; }}
.vv-header p  {{ margin: 4px 0 0; font-size: 0.9rem; opacity: 0.82; color: {WHITE}; }}

/* ── KPI metric cards ────────────────────────────────────── */
.kpi-card {{
    background: {WHITE};
    border-radius: 12px;
    padding: 20px 22px;
    box-shadow: 0 2px 10px rgba(27,58,92,0.09);
    border-left: 5px solid {ORANGE};
    height: 100%;
}}
.kpi-card.green  {{ border-left-color: {GREEN}; }}
.kpi-card.red    {{ border-left-color: {RED}; }}
.kpi-card.amber  {{ border-left-color: {AMBER}; }}
.kpi-card.navy   {{ border-left-color: {NAVY}; }}
.kpi-label  {{ font-size: 0.78rem; font-weight: 600; color: #6B7280;
               text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }}
.kpi-value  {{ font-size: 2.1rem; font-weight: 700; color: {NAVY}; line-height: 1; }}
.kpi-sub    {{ font-size: 0.82rem; color: #9CA3AF; margin-top: 4px; }}

/* ── Status badges ───────────────────────────────────────── */
.badge {{
    display: inline-block; border-radius: 20px;
    padding: 3px 10px; font-size: 0.75rem; font-weight: 600;
}}
.badge-nr  {{ background: #FDE8E8; color: #C0392B; }}
.badge-ret {{ background: #E8F8F0; color: #1E8449; }}
.badge-unk {{ background: #FEF9E7; color: #B7950B; }}

/* ── Section card ────────────────────────────────────────── */
.section-card {{
    background: {WHITE};
    border-radius: 12px;
    padding: 22px 24px;
    box-shadow: 0 2px 10px rgba(27,58,92,0.07);
    margin-bottom: 20px;
}}
.section-title {{
    font-size: 1rem; font-weight: 700; color: {NAVY};
    margin-bottom: 16px; padding-bottom: 10px;
    border-bottom: 2px solid #F3F4F6;
}}

/* ── Sidebar branding ────────────────────────────────────── */
[data-testid="stSidebarContent"] {{
    background: {NAVY} !important;
}}
[data-testid="stSidebarContent"] * {{
    color: {WHITE} !important;
}}
[data-testid="stSidebarContent"] .stSelectbox label,
[data-testid="stSidebarContent"] p {{
    color: rgba(255,255,255,0.75) !important;
    font-size: 0.82rem;
}}
[data-testid="stSidebarContent"] hr {{
    border-color: rgba(255,255,255,0.15) !important;
}}

/* ── Streamlit metric overrides ──────────────────────────── */
[data-testid="stMetricValue"] {{ color: {NAVY} !important; }}
[data-testid="stMetricLabel"] {{ color: #6B7280 !important; }}

/* ── Dataframe table header ──────────────────────────────── */
[data-testid="stDataFrame"] thead th {{
    background-color: {NAVY} !important;
    color: {WHITE} !important;
}}

/* ── Primary button ──────────────────────────────────────── */
.stButton > button[kind="primary"] {{
    background-color: {ORANGE} !important;
    border-color: {ORANGE} !important;
    color: {WHITE} !important;
    border-radius: 8px;
    font-weight: 600;
}}
.stButton > button[kind="primary"]:hover {{
    background-color: #d9650f !important;
}}

/* ── Upload zone ─────────────────────────────────────────── */
[data-testid="stFileUploader"] {{
    border: 2px dashed {ORANGE} !important;
    border-radius: 12px;
    padding: 10px;
}}

/* ── Info/success/warning boxes ──────────────────────────── */
.vv-info    {{ background:#EBF4FF; border-left:4px solid #3B82F6;
               border-radius:8px; padding:12px 16px; margin:8px 0; }}
.vv-success {{ background:#E8F8F0; border-left:4px solid {GREEN};
               border-radius:8px; padding:12px 16px; margin:8px 0; }}
.vv-warning {{ background:#FEF9E7; border-left:4px solid {AMBER};
               border-radius:8px; padding:12px 16px; margin:8px 0; }}
</style>
"""


def apply_theme():
    """Inject global CSS. Call once at the top of every page."""
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    """Render the branded page header banner."""
    sub_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f'<div class="vv-header"><h1>{title}</h1>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value, sub: str = "", colour: str = "orange"):
    """Render a KPI metric card. colour: orange | green | red | amber | navy"""
    cls = {"orange": "", "green": "green", "red": "red",
           "amber": "amber", "navy": "navy"}.get(colour, "")
    st.markdown(
        f"""<div class="kpi-card {cls}">
              <div class="kpi-label">{label}</div>
              <div class="kpi-value">{value}</div>
              <div class="kpi-sub">{sub}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> str:
    cls = {"Non-Returnable": "badge-nr", "Returnable": "badge-ret",
           "Unknown": "badge-unk"}.get(status, "badge-unk")
    return f'<span class="badge {cls}">{status}</span>'


def render_sidebar(active_page: str = ""):
    """Render the branded sidebar with logo and nav info."""
    with st.sidebar:
        # Logo
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=180)
        else:
            st.markdown(
                f"<h2 style='color:{ORANGE};margin:0'>VIR</h2>"
                f"<span style='color:white;font-size:0.8rem'>VENTURES</span>",
                unsafe_allow_html=True,
            )

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(
            "<p style='font-size:0.7rem;opacity:0.6;margin:0'>RETURNABILITY ENGINE</p>",
            unsafe_allow_html=True,
        )
        st.markdown("<hr>", unsafe_allow_html=True)

        # Live stats — only if credentials are configured
        try:
            from src.credentials import has_credentials
            if has_credentials():
                from src.storage import load_results_db, get_stats
                df   = load_results_db()
                s    = get_stats(df)
                unknown_count = s["unknown"]
                total = s["total"]
                st.markdown(
                    f"<p style='margin:2px 0'>📦 <b>{total}</b> products in database</p>"
                    f"<p style='margin:2px 0'>🟠 <b>{s['non_returnable']}</b> Non-Returnable</p>"
                    f"<p style='margin:2px 0'>🟢 <b>{s['returnable']}</b> Returnable</p>"
                    + (f"<p style='margin:2px 0'>🔴 <b>{unknown_count}</b> need review</p>"
                       if unknown_count else ""),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<p style='opacity:0.6;font-size:0.8rem'>Configure secrets to connect</p>",
                    unsafe_allow_html=True,
                )
        except Exception:
            pass

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(
            "<p style='font-size:0.7rem;opacity:0.5;margin:0'>"
            "VirVentures © 2026<br>Powered by Claude AI</p>",
            unsafe_allow_html=True,
        )
