"""
VirVentures Returnability Engine — Dashboard (main page).
"""

import altair as alt
import streamlit as st

from src.ui_utils import apply_theme, page_header, kpi_card, render_sidebar, ORANGE, NAVY, GREEN, RED, AMBER
import pandas as pd
from src.storage import load_results_db, get_stats

st.set_page_config(
    page_title="VirVentures · Returnability Engine",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()

from src.auth import check_auth, render_logout
if not check_auth():
    st.stop()
render_logout()

render_sidebar("dashboard")

# ── Header ────────────────────────────────────────────────────────────────────
page_header(
    "📊 Dashboard",
    "Real-time overview of your product returnability intelligence",
)

# ── Credentials check — fail fast, never hang ─────────────────────────────────
from src.credentials import has_credentials
if not has_credentials():
    st.error("### Google Sheets not connected")
    st.markdown("""
To connect your Google Sheet, add the following secrets in Streamlit Cloud:

**Manage app → Settings → Secrets** — paste this block and fill in your values:

```toml
GOOGLE_SHEET_ID = "your-sheet-id-here"

[google_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = "-----BEGIN RSA PRIVATE KEY-----\\n...\\n-----END RSA PRIVATE KEY-----\\n"
client_email = "your-service-account@project.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

After saving secrets, click **Reboot app**.
    """)
    st.stop()

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
    donut = (
        alt.Chart(pie_df)
        .mark_arc(innerRadius=70, outerRadius=120)
        .encode(
            theta=alt.Theta("Count:Q"),
            color=alt.Color(
                "Status:N",
                scale=alt.Scale(
                    domain=["Non-Returnable", "Returnable", "Unknown"],
                    range=[RED, GREEN, AMBER],
                ),
                legend=alt.Legend(orient="bottom"),
            ),
            tooltip=["Status:N", "Count:Q"],
        )
        .properties(height=300)
    )
    st.altair_chart(donut, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="section-card"><div class="section-title">Confidence by Status</div>',
                unsafe_allow_html=True)
    conf_counts = df.groupby(["Status", "Confidence"]).size().reset_index(name="Count")
    conf_chart = (
        alt.Chart(conf_counts)
        .mark_bar()
        .encode(
            x=alt.X("Status:N", title=""),
            y=alt.Y("Count:Q", title="Products"),
            color=alt.Color(
                "Confidence:N",
                scale=alt.Scale(
                    domain=["High", "Medium", "Low"],
                    range=[GREEN, AMBER, RED],
                ),
                legend=alt.Legend(orient="bottom"),
            ),
            tooltip=["Status:N", "Confidence:N", "Count:Q"],
        )
        .properties(height=300)
    )
    st.altair_chart(conf_chart, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ── Rule Type Breakdown ───────────────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Classification Source Breakdown</div>',
            unsafe_allow_html=True)

if "Classified By" in df.columns:
    by_source = df["Classified By"].value_counts().reset_index()
    by_source.columns = ["Source", "Count"]
    source_chart = (
        alt.Chart(by_source)
        .mark_bar(color=ORANGE)
        .encode(
            x=alt.X("Count:Q", title="Items classified"),
            y=alt.Y("Source:N", sort="-x", title=""),
            tooltip=["Source:N", "Count:Q"],
        )
        .properties(height=max(120, len(by_source) * 45))
    )
    st.altair_chart(source_chart, use_container_width=True)
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
