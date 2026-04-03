"""
Review Queue — AI-powered analysis for Unknown items.
Batches all unknowns into a single low-cost API call.
"""

import pandas as pd
import streamlit as st

from src.ui_utils import apply_theme, page_header, kpi_card, render_sidebar, ORANGE, NAVY, AMBER
from src.storage import load_results_db, upsert_results, get_stats, invalidate_cache
from src.ai_reviewer import is_available, analyse_batch, estimated_cost

st.set_page_config(
    page_title="Review Queue · VirVentures",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
from src.auth import require_login, render_logout
require_login()
render_logout()
render_sidebar("review")
page_header("🤖 Review Queue",
            "AI analysis for products that couldn't be classified by rules alone")

# ── Load unknowns ──────────────────────────────────────────────────────────────
with st.spinner("Loading queue…"):
    df = load_results_db()

if df.empty:
    st.info("No data yet. Upload products first.", icon="ℹ️")
    st.stop()

unknowns = df[df["Status"] == "Unknown"].copy()

# ── Summary KPIs ───────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
with c1:
    kpi_card("In Review Queue", len(unknowns), "items need attention", "amber")
with c2:
    kpi_card("Est. AI Cost", estimated_cost(len(unknowns)),
             "for entire queue in one call", "orange")
with c3:
    ai_status = "✅ Active" if is_available() else "⚠️ Not configured"
    kpi_card("AI Engine", ai_status, "Claude Haiku", "navy")

if unknowns.empty:
    st.success("✅ Review queue is empty — all products are classified!", icon="✅")
    st.stop()

st.markdown("<br>", unsafe_allow_html=True)

# ── Items table ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Unknown Items</div>', unsafe_allow_html=True)

display_cols = [c for c in ["ASIN", "Title", "Brand", "Category", "Reason", "Run Date"]
                if c in unknowns.columns]

st.dataframe(
    unknowns[display_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "ASIN":     st.column_config.TextColumn(width=120),
        "Title":    st.column_config.TextColumn(width=280),
        "Brand":    st.column_config.TextColumn(width=120),
        "Category": st.column_config.TextColumn(width=180),
        "Reason":   st.column_config.TextColumn(width=260),
        "Run Date": st.column_config.TextColumn(width=130),
    },
)
st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# ── AI Analysis section ────────────────────────────────────────────────────────
st.subheader("🤖 AI Analysis")

if not is_available():
    st.markdown("""
    <div class="vv-warning">
    <b>AI Engine not yet configured.</b><br><br>
    To activate AI analysis:<br>
    1. Get your Anthropic API key at <a href="https://console.anthropic.com" target="_blank">console.anthropic.com</a><br>
    2. Add <code>ANTHROPIC_API_KEY=sk-ant-...</code> to your <b>.env</b> file (local)<br>
       or add it to <b>Streamlit Cloud Secrets</b> (deployed)<br>
    3. Install: <code>pip install anthropic</code><br><br>
    Estimated cost for {n} items: <b>{cost}</b> — using Claude Haiku (most efficient model)
    </div>
    """.format(n=len(unknowns), cost=estimated_cost(len(unknowns))),
    unsafe_allow_html=True)

    # Manual override section (always available)
    st.divider()
    _render_manual_override(unknowns)
    st.stop()

# AI is available — show the analysis UI
st.markdown(f"""
<div class="vv-info">
<b>Ready to analyse {len(unknowns)} items.</b>
All items will be sent in <b>one batched API call</b> — estimated cost: <b>{estimated_cost(len(unknowns))}</b>.<br>
After analysis, accepted results are saved as ASIN overrides so they never need AI again.
</div>
""", unsafe_allow_html=True)

if "ai_results" not in st.session_state:
    st.session_state.ai_results = None

if st.button(f"▶  Run AI Analysis ({len(unknowns)} items)",
             type="primary", use_container_width=True):
    items = [
        {
            "asin":        row.get("ASIN", ""),
            "title":       row.get("Title", ""),
            "brand":       row.get("Brand", ""),
            "category":    row.get("Category", ""),
            "description": row.get("Description", "") if "Description" in row else "",
        }
        for _, row in unknowns.iterrows()
    ]

    with st.spinner(f"Sending {len(items)} items to Claude Haiku…"):
        ai_results = analyse_batch(items)
        st.session_state.ai_results = ai_results

if st.session_state.ai_results:
    results = st.session_state.ai_results
    st.subheader(f"AI returned {len(results)} classifications")

    # Display results with accept/reject per item
    to_save = []

    for res in results:
        asin   = res.get("asin", "")
        status = res.get("status", "Unknown")
        conf   = res.get("confidence", "Low")
        reason = res.get("reason", "")
        rule   = res.get("suggested_rule")

        emoji = {"Non-Returnable": "🔴", "Returnable": "🟢", "Unknown": "🟡"}.get(status, "⚪")

        with st.container():
            ca, cb, cc = st.columns([2, 4, 2])
            with ca:
                title_row = unknowns[unknowns["ASIN"] == asin]
                title = title_row.iloc[0]["Title"][:60] if not title_row.empty else asin
                st.markdown(f"**{asin}**<br><small>{title}</small>",
                            unsafe_allow_html=True)
            with cb:
                st.markdown(
                    f"{emoji} **{status}** · {conf} confidence<br>"
                    f"<small>{reason}</small>"
                    + (f"<br><small>💡 Suggested rule: `{rule['type']}` → `{rule['value']}`</small>"
                       if rule else ""),
                    unsafe_allow_html=True,
                )
            with cc:
                accepted = st.checkbox("Accept", key=f"accept_{asin}", value=(conf == "High"))
                if accepted:
                    to_save.append({
                        "asin":          asin,
                        "status":        status,
                        "returnable":    "Yes" if status == "Returnable" else
                                         "No"  if status == "Non-Returnable" else "Review",
                        "confidence":    conf,
                        "reason":        reason,
                        "classified_by": "AI (Claude Haiku)",
                    })
            st.divider()

    if to_save:
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"💾 Save {len(to_save)} accepted results", type="primary",
                         use_container_width=True):
                with st.spinner("Saving…"):
                    upsert_results(to_save, source_file="AI Review")
                st.success(f"✅ {len(to_save)} results saved and added to database.")
                st.session_state.ai_results = None
                st.rerun()
        with col2:
            if st.button("✅ Accept All & Save", use_container_width=True):
                all_results = [
                    {
                        "asin":          r.get("asin"),
                        "status":        r.get("status", "Unknown"),
                        "returnable":    "Yes" if r.get("status") == "Returnable" else
                                         "No"  if r.get("status") == "Non-Returnable" else "Review",
                        "confidence":    r.get("confidence", "Low"),
                        "reason":        r.get("reason", "AI classification"),
                        "classified_by": "AI (Claude Haiku)",
                    }
                    for r in results
                ]
                with st.spinner("Saving all…"):
                    upsert_results(all_results, source_file="AI Review")
                st.success(f"✅ All {len(all_results)} AI results saved.")
                st.session_state.ai_results = None
                st.rerun()


def _render_manual_override(unknowns: pd.DataFrame):
    """Manual classification section — always available even without AI."""
    st.subheader("✏️ Manual Classification")
    st.markdown(
        "Classify individual items manually while AI is being configured.",
        unsafe_allow_html=True,
    )

    asin_choice = st.selectbox(
        "Select ASIN to classify",
        options=unknowns["ASIN"].tolist(),
        format_func=lambda a: f"{a} — {unknowns[unknowns['ASIN']==a]['Title'].values[0][:60] if not unknowns[unknowns['ASIN']==a].empty else ''}",
    )

    if asin_choice:
        mc1, mc2 = st.columns(2)
        with mc1:
            manual_status = st.selectbox("Classification",
                                          ["Non-Returnable", "Returnable", "Unknown"])
            manual_conf   = st.selectbox("Confidence", ["High", "Medium", "Low"])
        with mc2:
            manual_reason = st.text_input("Reason", placeholder="e.g. Hygiene product — brand policy")

        if st.button("💾 Save manual classification", type="primary"):
            yes_no = ("Yes" if manual_status == "Returnable" else
                      "No"  if manual_status == "Non-Returnable" else "Review")
            upsert_results([{
                "asin":          asin_choice,
                "status":        manual_status,
                "returnable":    yes_no,
                "confidence":    manual_conf,
                "reason":        manual_reason or "Manual classification",
                "classified_by": "Manual",
            }], source_file="Manual Review")
            st.success(f"✅ {asin_choice} saved as {manual_status}.")
            invalidate_cache()
            st.rerun()
