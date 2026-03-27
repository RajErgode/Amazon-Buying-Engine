"""
Upload & Classify — drag-and-drop Keepa XLSX → instant classification.
"""

from datetime import datetime
import pandas as pd
import streamlit as st

from src.ui_utils import apply_theme, page_header, kpi_card, render_sidebar, ORANGE, NAVY, GREEN, RED, AMBER
from src.keepa_parser import parse_keepa_xlsx, detected_columns
from src.storage import load_results_db, get_known_asins, upsert_results, get_stats
from src.classifier import ReturnabilityClassifier
from src.rules_manager import load_rules

st.set_page_config(
    page_title="Upload & Classify · VirVentures",
    page_icon="📤",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
render_sidebar("upload")
page_header("📤 Upload & Classify",
            "Upload a Keepa product export — duplicates are detected automatically")

# ── Cached rule loader ─────────────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def _load_rules():
    return load_rules()

# ── File upload ────────────────────────────────────────────────────────────────
uploaded = st.file_uploader(
    "Drag and drop your Keepa XLSX export here",
    type=["xlsx", "xls"],
    help="Export from Keepa Product Viewer. Must contain an ASIN column.",
)

if not uploaded:
    st.markdown("""
    <div class="vv-info">
    <b>How to export from Keepa:</b><br>
    1. Open Keepa Product Viewer<br>
    2. Select your ASINs → click <b>Export</b> → choose XLSX<br>
    3. Upload the file here — all columns are detected automatically
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Parse file ─────────────────────────────────────────────────────────────────
with st.spinner("Reading file…"):
    try:
        file_bytes = uploaded.read()
        df_raw, keepa_export = parse_keepa_xlsx(file_bytes)
        col_info = detected_columns(df_raw)
    except Exception as e:
        st.error(f"❌ Could not read file: {e}")
        st.stop()

total_in_file = len(df_raw)

# ── Column detection summary ───────────────────────────────────────────────────
with st.expander("📋 File summary", expanded=True):
    c1, c2, c3 = st.columns(3)
    c1.metric("ASINs in file", total_in_file)
    c2.metric("Standard columns found",
              f"{len(col_info['standard_found'])} / 4")
    c3.metric("Keepa signal columns found",
              len(col_info['signals_found']))

    if col_info["standard_missing"]:
        st.warning(
            f"Missing columns (will classify with available data): "
            f"{', '.join(col_info['standard_missing'])}",
            icon="⚠️",
        )
    if col_info["signals_found"]:
        st.success(
            "✅ Keepa signals detected: " + ", ".join(col_info["signals_found"]),
        )

# ── Duplicate detection ────────────────────────────────────────────────────────
with st.spinner("Checking database for existing records…"):
    db_df       = load_results_db()
    known_asins = get_known_asins(db_df)

uploaded_asins = set(df_raw["asin"].str.upper())
cached_asins   = uploaded_asins & known_asins
new_asins      = uploaded_asins - known_asins

c1, c2, c3 = st.columns(3)
with c1:
    kpi_card("In file", total_in_file, "total ASINs", "navy")
with c2:
    kpi_card("Already in database", len(cached_asins),
             "instant results (no processing needed)", "green")
with c3:
    kpi_card("New — to classify", len(new_asins),
             "will be processed now", "orange")

if cached_asins:
    with st.expander(f"📦 {len(cached_asins)} cached results (from database)", expanded=False):
        cached_df = db_df[db_df["ASIN"].isin(cached_asins)][
            ["ASIN", "Title", "Status", "Confidence", "Reason", "Run Date"]
        ]
        st.dataframe(cached_df, use_container_width=True, hide_index=True)

if not new_asins:
    st.success("✅ All ASINs already classified. No new processing needed.")
    _show_download(db_df[db_df["ASIN"].isin(uploaded_asins)], uploaded.name)
    st.stop()

st.divider()
st.subheader(f"Ready to classify {len(new_asins)} new ASINs")

# ── Classify button ────────────────────────────────────────────────────────────
if st.button(f"▶  Classify {len(new_asins)} products", type="primary", use_container_width=True):

    progress_bar = st.progress(0, text="Loading rules…")

    # Load rules
    try:
        with st.spinner("Loading Rules Library…"):
            rules = _load_rules()
    except Exception as e:
        st.error(f"Could not load Rules Library: {e}")
        st.stop()

    classifier = ReturnabilityClassifier(rules=rules)

    # Override keepa_export on classifier with the uploaded file's signals
    classifier.keepa_export = {**classifier.keepa_export, **keepa_export}

    new_df    = df_raw[df_raw["asin"].isin(new_asins)].copy()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    results   = []
    n         = len(new_df)

    progress_bar.progress(0, text=f"Classifying 0 / {n}…")

    for i, (_, row) in enumerate(new_df.iterrows(), 1):
        asin        = row.get("asin", "")
        result      = classifier.classify(
            asin=asin,
            category_path=row.get("category", ""),
            title=row.get("title", ""),
            keepa_data=None,          # We use keepa_export, not the API
            brand=row.get("brand", ""),
            description=row.get("description", ""),
        )
        yes_no = ("Yes"    if result["status"] == "Returnable"     else
                  "No"     if result["status"] == "Non-Returnable"  else
                  "Review")
        results.append({
            "asin":          asin,
            "title":         row.get("title", ""),
            "brand":         row.get("brand", ""),
            "category":      row.get("category", ""),
            "status":        result["status"],
            "returnable":    yes_no,
            "confidence":    result["confidence"],
            "reason":        result["reason"],
            "classified_by": "rules",
            "run_date":      timestamp,
        })
        progress_bar.progress(i / n, text=f"Classifying {i} / {n}…")

    progress_bar.progress(1.0, text="Saving to database…")

    # Save
    with st.spinner("Writing to Results Database…"):
        written = upsert_results(results, source_file=uploaded.name)

    progress_bar.empty()

    # ── Run summary ──────────────────────────────────────────────────────────
    results_df = pd.DataFrame(results)
    st.success(f"✅ {written} products classified and saved.")

    s = get_stats(results_df.rename(columns={"status": "Status", "confidence": "Confidence"}))
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Processed", written, "this run", "navy")
    with c2: kpi_card("Non-Returnable", s["non_returnable"],
                       f"{s['non_ret_pct']}%", "red")
    with c3: kpi_card("Returnable", s["returnable"],
                       f"{s['ret_pct']}%", "green")
    with c4: kpi_card("Review needed", s["unknown"],
                       "use AI Review for these", "amber")

    # Results preview
    st.subheader("Classification Results")
    preview = results_df[["asin", "title", "brand", "status",
                           "confidence", "reason"]].copy()
    preview.columns = ["ASIN", "Title", "Brand", "Status", "Confidence", "Reason"]

    st.dataframe(
        preview,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ASIN":       st.column_config.TextColumn(width=120),
            "Title":      st.column_config.TextColumn(width=250),
            "Brand":      st.column_config.TextColumn(width=120),
            "Status":     st.column_config.TextColumn(width=130),
            "Confidence": st.column_config.TextColumn(width=100),
            "Reason":     st.column_config.TextColumn(width=280),
        },
    )

    # Download
    st.divider()
    # Full combined output (cached + new)
    all_asins_df = db_df[db_df["ASIN"].isin(cached_asins)] if not db_df.empty else pd.DataFrame()
    combined = pd.concat([all_asins_df, preview], ignore_index=True)

    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(
            "⬇  Download this run (CSV)",
            data=preview.to_csv(index=False).encode("utf-8"),
            file_name=f"classification_{timestamp[:10]}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_dl2:
        st.download_button(
            "⬇  Download full file results (CSV)",
            data=combined.to_csv(index=False).encode("utf-8"),
            file_name=f"classification_full_{timestamp[:10]}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    if s["unknown"] > 0:
        st.markdown("""
        <div class="vv-warning">
        <b>Review queue has items.</b> Go to <b>🤖 Review Queue</b> to run AI analysis
        on the Unknown items — cost is typically under $0.01 for a full batch.
        </div>
        """, unsafe_allow_html=True)


def _show_download(df: pd.DataFrame, filename: str):
    """Helper: show download button for already-classified results."""
    if df.empty:
        return
    st.divider()
    ts = datetime.now().strftime("%Y-%m-%d")
    st.download_button(
        "⬇  Download results (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"results_{ts}.csv",
        mime="text/csv",
    )
