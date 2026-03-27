"""
Results Explorer — search, filter, and export all classified products.
"""

from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

from src.ui_utils import apply_theme, page_header, kpi_card, render_sidebar, ORANGE, NAVY
from src.storage import load_results_db, get_stats

st.set_page_config(
    page_title="Results Explorer · VirVentures",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
render_sidebar("results")
page_header("🔍 Results Explorer",
            "Search, filter, and export your full classification database")

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Loading database…"):
    df = load_results_db()

if df.empty:
    st.info("No data yet. Go to **📤 Upload & Classify** to get started.", icon="ℹ️")
    st.stop()

# ── Top stats ─────────────────────────────────────────────────────────────────
s = get_stats(df)
c1, c2, c3, c4 = st.columns(4)
with c1: kpi_card("Total", f"{s['total']:,}", "products", "navy")
with c2: kpi_card("Non-Returnable", f"{s['non_returnable']:,}",
                   f"{s['non_ret_pct']}% of total", "red")
with c3: kpi_card("Returnable", f"{s['returnable']:,}",
                   f"{s['ret_pct']}% of total", "green")
with c4: kpi_card("Review Queue", f"{s['unknown']:,}",
                   "need attention", "amber")

st.markdown("<br>", unsafe_allow_html=True)

# ── Filters ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">🔎 Filter & Search</div>', unsafe_allow_html=True)

f1, f2, f3, f4 = st.columns([2, 1, 1, 1])

with f1:
    search = st.text_input(
        "Search",
        placeholder="ASIN, product name, brand, or keyword…",
        label_visibility="collapsed",
    )

with f2:
    status_filter = st.multiselect(
        "Status",
        options=["Non-Returnable", "Returnable", "Unknown"],
        default=["Non-Returnable", "Returnable", "Unknown"],
    )

with f3:
    conf_filter = st.multiselect(
        "Confidence",
        options=["High", "Medium", "Low"],
        default=["High", "Medium", "Low"],
    )

with f4:
    source_options = sorted(df["Source File"].dropna().unique().tolist()) if "Source File" in df.columns else []
    source_filter = st.multiselect("Source File", options=source_options)

st.markdown("</div>", unsafe_allow_html=True)

# ── Apply filters ─────────────────────────────────────────────────────────────
filtered = df.copy()

if search:
    q = search.strip().lower()
    mask = (
        filtered["ASIN"].str.lower().str.contains(q, na=False) |
        filtered["Title"].str.lower().str.contains(q, na=False) |
        filtered["Brand"].str.lower().str.contains(q, na=False) |
        filtered["Reason"].str.lower().str.contains(q, na=False)
    )
    filtered = filtered[mask]

if status_filter:
    filtered = filtered[filtered["Status"].isin(status_filter)]

if conf_filter and "Confidence" in filtered.columns:
    filtered = filtered[filtered["Confidence"].isin(conf_filter)]

if source_filter and "Source File" in filtered.columns:
    filtered = filtered[filtered["Source File"].isin(source_filter)]

# ── Results table ─────────────────────────────────────────────────────────────
st.markdown(
    f"<br><b style='color:{NAVY}'>{len(filtered):,} products match your filters</b><br><br>",
    unsafe_allow_html=True,
)

display_cols = [c for c in ["ASIN", "Title", "Brand", "Category", "Status",
                              "Confidence", "Reason", "Classified By", "Run Date", "Source File"]
                if c in filtered.columns]

st.dataframe(
    filtered[display_cols].sort_values("Run Date", ascending=False),
    use_container_width=True,
    hide_index=True,
    column_config={
        "ASIN":          st.column_config.TextColumn("ASIN",            width=120),
        "Title":         st.column_config.TextColumn("Product Title",   width=260),
        "Brand":         st.column_config.TextColumn("Brand",           width=120),
        "Category":      st.column_config.TextColumn("Category",        width=160),
        "Status":        st.column_config.TextColumn("Status",          width=130),
        "Confidence":    st.column_config.TextColumn("Confidence",      width=100),
        "Reason":        st.column_config.TextColumn("Reason",          width=280),
        "Classified By": st.column_config.TextColumn("Classified By",   width=110),
        "Run Date":      st.column_config.TextColumn("Date",            width=130),
        "Source File":   st.column_config.TextColumn("Source File",     width=150),
    },
)

# ── ASIN Lookup ───────────────────────────────────────────────────────────────
st.divider()
st.subheader("🔎 ASIN Quick Lookup")
lookup_asin = st.text_input("Enter ASIN", placeholder="B00XXXXXX",
                             max_chars=10).strip().upper()

if lookup_asin:
    match = df[df["ASIN"] == lookup_asin]
    if match.empty:
        st.warning(f"ASIN **{lookup_asin}** not found in database.")
    else:
        row = match.iloc[0]
        status = row.get("Status", "Unknown")
        colour = {"Non-Returnable": "🔴", "Returnable": "🟢", "Unknown": "🟡"}.get(status, "⚪")
        st.markdown(f"""
        <div class="section-card">
            <div class="section-title">{colour} {lookup_asin} — {status}</div>
            <p><b>Title:</b> {row.get('Title','')}</p>
            <p><b>Brand:</b> {row.get('Brand','')}</p>
            <p><b>Category:</b> {row.get('Category','')}</p>
            <p><b>Confidence:</b> {row.get('Confidence','')}</p>
            <p><b>Reason:</b> {row.get('Reason','')}</p>
            <p><b>Classified By:</b> {row.get('Classified By','')}</p>
            <p><b>Last Run:</b> {row.get('Run Date','')}</p>
        </div>
        """, unsafe_allow_html=True)

# ── Export ────────────────────────────────────────────────────────────────────
st.divider()
st.subheader("⬇ Export")
ts = datetime.now().strftime("%Y-%m-%d")

ec1, ec2 = st.columns(2)

with ec1:
    st.download_button(
        "⬇  Export filtered results (CSV)",
        data=filtered[display_cols].to_csv(index=False).encode("utf-8"),
        file_name=f"virventures_results_{ts}.csv",
        mime="text/csv",
        use_container_width=True,
    )

with ec2:
    # Excel export
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        filtered[display_cols].to_excel(writer, index=False, sheet_name="Results")
    buffer.seek(0)
    st.download_button(
        "⬇  Export filtered results (Excel)",
        data=buffer.getvalue(),
        file_name=f"virventures_results_{ts}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
