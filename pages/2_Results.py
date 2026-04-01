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

# ── Top KPI row ───────────────────────────────────────────────────────────────
s = get_stats(df)
c1, c2, c3, c4 = st.columns(4)
with c1: kpi_card("Total Products",   f"{s['total']:,}",        "in database",     "navy")
with c2: kpi_card("Non-Returnable",   f"{s['non_returnable']:,}", f"{s['non_ret_pct']}% of total", "red")
with c3: kpi_card("Returnable",       f"{s['returnable']:,}",    f"{s['ret_pct']}% of total",     "green")
with c4: kpi_card("Review Queue",     f"{s['unknown']:,}",       "need attention",  "amber")

st.markdown("<br>", unsafe_allow_html=True)

# ── Filters ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">🔎 Filter & Search</div>', unsafe_allow_html=True)

f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
with f1:
    search = st.text_input("Search", placeholder="ASIN, product name, brand, or keyword…",
                           label_visibility="collapsed")
with f2:
    status_filter = st.multiselect("Status",
        options=["Non-Returnable", "Returnable", "Unknown"],
        default=["Non-Returnable", "Returnable", "Unknown"])
with f3:
    conf_filter = st.multiselect("Confidence",
        options=["High", "Medium", "Low"],
        default=["High", "Medium", "Low"])
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

filtered = filtered.sort_values("Run Date", ascending=False).reset_index(drop=True)

# ── Pagination ────────────────────────────────────────────────────────────────
PAGE_SIZE = 30
total_rows = len(filtered)
total_pages = max(1, -(-total_rows // PAGE_SIZE))   # ceiling division

col_count, col_page = st.columns([3, 1])
with col_count:
    st.markdown(
        f"<p style='color:{NAVY};font-weight:600;margin:8px 0'>"
        f"{total_rows:,} products match your filters</p>",
        unsafe_allow_html=True,
    )
with col_page:
    page = st.number_input("Page", min_value=1, max_value=total_pages,
                           value=1, step=1, label_visibility="collapsed")

start = (page - 1) * PAGE_SIZE
end   = min(start + PAGE_SIZE, total_rows)
page_df = filtered.iloc[start:end]

st.markdown(
    f"<p style='font-size:0.8rem;color:#9CA3AF;margin-bottom:8px'>"
    f"Showing {start+1}–{end} of {total_rows:,}  •  Page {page} of {total_pages}</p>",
    unsafe_allow_html=True,
)

# ── Badge helpers ─────────────────────────────────────────────────────────────
def status_badge(val):
    styles = {
        "Non-Returnable": ("background:#FDE8E8;color:#C0392B", "Non-Returnable"),
        "Returnable":     ("background:#E8F5E9;color:#1E8449", "Returnable"),
        "Unknown":        ("background:#FEF9E7;color:#B7950B", "Review"),
    }
    s, label = styles.get(val, ("background:#F3F4F6;color:#6B7280", val))
    return (f'<span style="{s};padding:3px 12px;border-radius:20px;'
            f'font-size:0.75rem;font-weight:700;white-space:nowrap">{label}</span>')

def conf_badge(val):
    styles = {
        "High":   "background:#E8F5E9;color:#1E8449",
        "Medium": "background:#FEF9E7;color:#B7950B",
        "Low":    "background:#FDE8E8;color:#C0392B",
    }
    s = styles.get(val, "background:#F3F4F6;color:#6B7280")
    return (f'<span style="{s};padding:2px 10px;border-radius:4px;'
            f'font-size:0.72rem;font-weight:600">{val}</span>')

def trunc(text, n=55):
    t = str(text) if text else ""
    return (t[:n] + "…") if len(t) > n else t

# ── HTML Table ────────────────────────────────────────────────────────────────
ROW_BG = {
    "Non-Returnable": ("#FEF2F2", "#FECACA"),   # light red, alt light red
    "Returnable":     ("#F0FDF4", "#DCFCE7"),   # light green, alt light green
    "Unknown":        ("#FFFBEB", "#FEF3C7"),   # light amber, alt light amber
}

rows_html = ""
for i, (_, row) in enumerate(page_df.iterrows()):
    status = row.get('Status', '')
    bgs = ROW_BG.get(status, ("#FFFFFF", "#F8FAFC"))
    bg = bgs[0] if i % 2 == 0 else bgs[1]

    border = "border-bottom:1px solid rgba(0,0,0,0.06)"
    td      = f'style="padding:10px 14px;{border};background:{bg};vertical-align:middle;"'
    td_mono = f'style="padding:10px 14px;{border};background:{bg};vertical-align:middle;font-family:monospace;font-size:0.85rem;color:{NAVY};font-weight:600;"'
    td_sm   = f'style="padding:10px 14px;{border};background:{bg};vertical-align:middle;font-size:0.8rem;color:#374151;"'

    asin = row.get('ASIN', '')
    asin_link = (f'<a href="https://www.amazon.com/gp/product/{asin}" target="_blank" '
                 f'style="color:{NAVY};text-decoration:none;font-family:monospace;font-weight:700;'
                 f'font-size:0.85rem;border-bottom:1px dotted {ORANGE};" '
                 f'title="Open on Amazon">{asin} ↗</a>')

    rows_html += f"""
    <tr>
        <td {td_mono}>{asin_link}</td>
        <td {td}><span title="{row.get('Title','')}" style="font-size:0.84rem;color:#111827">{trunc(row.get('Title',''), 52)}</span></td>
        <td {td}><span style="font-size:0.83rem;color:#374151;font-weight:500">{trunc(row.get('Brand',''), 18)}</span></td>
        <td {td_sm}>{trunc(row.get('Category',''), 28)}</td>
        <td {td}>{status_badge(row.get('Status',''))}</td>
        <td {td}>{conf_badge(row.get('Confidence',''))}</td>
        <td {td_sm}><span title="{row.get('Reason','')}">{trunc(row.get('Reason',''), 50)}</span></td>
        <td {td_sm}>{str(row.get('Run Date',''))[:10]}</td>
    </tr>"""

th = (f'style="padding:11px 14px;text-align:left;font-size:0.78rem;font-weight:700;'
      f'text-transform:uppercase;letter-spacing:0.05em;color:white;background:{NAVY};'
      f'white-space:nowrap;"')

table_html = f"""
<div style="border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(27,58,92,0.10);margin-bottom:8px;">
<table style="width:100%;border-collapse:collapse;font-family:Arial,sans-serif;">
  <thead>
    <tr>
      <th {th}>ASIN</th>
      <th {th}>Product Title</th>
      <th {th}>Brand</th>
      <th {th}>Category</th>
      <th {th}>Status</th>
      <th {th}>Confidence</th>
      <th {th}>Classification Reason</th>
      <th {th}>Date</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>
</div>
"""

st.markdown(table_html, unsafe_allow_html=True)

# ── ASIN Quick Lookup ─────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">🔎 ASIN Quick Lookup</div>', unsafe_allow_html=True)

lookup_asin = st.text_input("Enter ASIN", placeholder="e.g. B00XXXXXX",
                             max_chars=10).strip().upper()
if lookup_asin:
    match = df[df["ASIN"] == lookup_asin]
    if match.empty:
        st.warning(f"ASIN **{lookup_asin}** not found in database.")
    else:
        row = match.iloc[0]
        status = row.get("Status", "Unknown")
        icon = {"Non-Returnable": "🔴", "Returnable": "🟢", "Unknown": "🟡"}.get(status, "⚪")
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-top:12px;">
          <div><span style="font-size:0.75rem;color:#9CA3AF;text-transform:uppercase;">ASIN</span>
               <p style="font-family:monospace;font-weight:700;color:{NAVY};margin:2px 0">{lookup_asin}</p></div>
          <div><span style="font-size:0.75rem;color:#9CA3AF;text-transform:uppercase;">Status</span>
               <p style="margin:4px 0">{status_badge(status)}</p></div>
          <div><span style="font-size:0.75rem;color:#9CA3AF;text-transform:uppercase;">Confidence</span>
               <p style="margin:4px 0">{conf_badge(row.get('Confidence',''))}</p></div>
          <div style="grid-column:span 3"><span style="font-size:0.75rem;color:#9CA3AF;text-transform:uppercase;">Product Title</span>
               <p style="font-weight:500;color:#111827;margin:2px 0">{row.get('Title','')}</p></div>
          <div><span style="font-size:0.75rem;color:#9CA3AF;text-transform:uppercase;">Brand</span>
               <p style="margin:2px 0">{row.get('Brand','')}</p></div>
          <div><span style="font-size:0.75rem;color:#9CA3AF;text-transform:uppercase;">Classified By</span>
               <p style="margin:2px 0">{row.get('Classified By','')}</p></div>
          <div><span style="font-size:0.75rem;color:#9CA3AF;text-transform:uppercase;">Last Run</span>
               <p style="margin:2px 0">{str(row.get('Run Date',''))[:10]}</p></div>
          <div style="grid-column:span 3"><span style="font-size:0.75rem;color:#9CA3AF;text-transform:uppercase;">Classification Reason</span>
               <p style="color:#374151;margin:2px 0">{row.get('Reason','')}</p></div>
        </div>
        """, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── Export ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">⬇ Export</div>', unsafe_allow_html=True)

ts = datetime.now().strftime("%Y-%m-%d")
display_cols = [c for c in ["ASIN", "Title", "Brand", "Category", "Status",
                             "Confidence", "Reason", "Classified By", "Run Date", "Source File"]
                if c in filtered.columns]

ec1, ec2 = st.columns(2)
with ec1:
    st.download_button(
        "⬇  Export filtered results — CSV",
        data=filtered[display_cols].to_csv(index=False).encode("utf-8"),
        file_name=f"virventures_results_{ts}.csv",
        mime="text/csv",
        use_container_width=True,
    )
with ec2:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        filtered[display_cols].to_excel(writer, index=False, sheet_name="Results")
    buffer.seek(0)
    st.download_button(
        "⬇  Export filtered results — Excel",
        data=buffer.getvalue(),
        file_name=f"virventures_results_{ts}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
st.markdown("</div>", unsafe_allow_html=True)
