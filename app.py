"""
VirVentures Returnability Engine — Dashboard (main page).
"""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.ui_utils import apply_theme, page_header, kpi_card, render_sidebar, ORANGE, NAVY, GREEN, RED, AMBER
from src.storage import load_results_db, get_stats

st.set_page_config(
    page_title="VirVentures · Returnability Engine",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
render_sidebar("dashboard")

# ── Header ────────────────────────────────────────────────────────────────────
page_header(
    "📊 Dashboard",
    "Real-time overview of your product returnability intelligence",
)

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Loading database…"):
    df   = load_results_db()
    s    = get_stats(df)

if df.empty:
    st.info(
        "**No data yet.** Go to **📤 Upload & Classify** to process your first Keepa export.",
        icon="ℹ️",
    )
    st.stop()

# ── KPI Row ───────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    kpi_card("Total Products", f"{s['total']:,}", "in database", "navy")
with c2:
    kpi_card("Non-Returnable", f"{s['non_ret_pct']}%",
             f"{s['non_returnable']:,} products", "red")
with c3:
    kpi_card("Returnable", f"{s['ret_pct']}%",
             f"{s['returnable']:,} products", "green")
with c4:
    kpi_card("High Confidence", f"{s['confidence_pct']}%",
             f"{s['high_confidence']:,} products", "orange")
with c5:
    review_colour = "amber" if s["unknown"] > 0 else "green"
    kpi_card("Review Queue", str(s["unknown"]),
             "items need attention", review_colour)

st.markdown("<br>", unsafe_allow_html=True)

# ── Charts Row ────────────────────────────────────────────────────────────────
left, right = st.columns([1, 1], gap="large")

with left:
    st.markdown('<div class="section-card"><div class="section-title">Status Breakdown</div>',
                unsafe_allow_html=True)
    pie_df = df["Status"].value_counts().reset_index()
    pie_df.columns = ["Status", "Count"]
    color_map = {"Non-Returnable": RED, "Returnable": GREEN, "Unknown": AMBER}
    fig = px.pie(
        pie_df, values="Count", names="Status",
        color="Status", color_discrete_map=color_map,
        hole=0.55,
    )
    fig.update_traces(textposition="outside", textinfo="percent+label",
                      textfont_size=13)
    fig.update_layout(
        showlegend=False, margin=dict(t=10, b=10, l=10, r=10),
        height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=NAVY),
        annotations=[dict(text=f"<b>{s['total']}</b><br>products",
                          x=0.5, y=0.5, font_size=14, showarrow=False,
                          font_color=NAVY)]
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="section-card"><div class="section-title">Confidence Distribution</div>',
                unsafe_allow_html=True)

    conf_order = ["High", "Medium", "Low"]
    conf_counts = df.groupby(["Status", "Confidence"]).size().reset_index(name="Count")
    fig2 = go.Figure()
    conf_colors = {"High": GREEN, "Medium": AMBER, "Low": RED}
    for conf in conf_order:
        subset = conf_counts[conf_counts["Confidence"] == conf]
        status_vals = subset.set_index("Status")["Count"].reindex(
            ["Non-Returnable", "Returnable", "Unknown"], fill_value=0
        )
        fig2.add_trace(go.Bar(
            name=conf,
            x=status_vals.index.tolist(),
            y=status_vals.values.tolist(),
            marker_color=conf_colors[conf],
        ))
    fig2.update_layout(
        barmode="stack",
        legend_title_text="Confidence",
        height=300,
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=NAVY),
        xaxis=dict(gridcolor="#F3F4F6"),
        yaxis=dict(gridcolor="#F3F4F6"),
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ── Rule Type Breakdown ───────────────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Classification Source Breakdown</div>',
            unsafe_allow_html=True)

if "Classified By" in df.columns:
    by_source = df["Classified By"].value_counts().reset_index()
    by_source.columns = ["Source", "Count"]
    fig3 = px.bar(
        by_source, x="Count", y="Source", orientation="h",
        color_discrete_sequence=[ORANGE],
        text="Count",
    )
    fig3.update_traces(textposition="outside")
    fig3.update_layout(
        height=max(120, len(by_source) * 45),
        margin=dict(t=0, b=0, l=0, r=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=NAVY),
        xaxis=dict(gridcolor="#F3F4F6"),
        showlegend=False,
        yaxis_title="",
        xaxis_title="Items classified",
    )
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Source tracking will appear after next upload.")

st.markdown("</div>", unsafe_allow_html=True)

# ── Recent Activity ───────────────────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Recent Activity (last 20 items)</div>',
            unsafe_allow_html=True)

display_cols = [c for c in ["ASIN", "Title", "Brand", "Status", "Confidence", "Reason", "Run Date"]
                if c in df.columns]
recent = df.sort_values("Run Date", ascending=False).head(20)[display_cols]

st.dataframe(
    recent,
    use_container_width=True,
    hide_index=True,
    column_config={
        "ASIN":       st.column_config.TextColumn("ASIN",       width=120),
        "Title":      st.column_config.TextColumn("Title",      width=280),
        "Brand":      st.column_config.TextColumn("Brand",      width=120),
        "Status":     st.column_config.TextColumn("Status",     width=130),
        "Confidence": st.column_config.TextColumn("Confidence", width=100),
        "Reason":     st.column_config.TextColumn("Reason",     width=260),
        "Run Date":   st.column_config.TextColumn("Date",       width=130),
    },
)

st.markdown("</div>", unsafe_allow_html=True)
