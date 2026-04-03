"""
Rules Library — view, add, and manage classification rules.
Team members can add rules here without touching any code.
"""

import pandas as pd
import streamlit as st

from src.ui_utils import apply_theme, page_header, kpi_card, render_sidebar, NAVY
from src.rules_manager import load_rules
from src.credentials import _get_client, _get_sheet_id

RULES_SHEET_NAME = "Rules Library"

RULE_TYPES = [
    "category_keyword",
    "title_keyword",
    "asin_override",
    "brand_override",
]
RULE_TYPE_DESCRIPTIONS = {
    "category_keyword": "Matches the full Category path (e.g. 'aerosol', 'grocery')",
    "title_keyword":    "Matches the product title (e.g. 'flammable', 'propane')",
    "asin_override":    "Exact ASIN match — highest priority, overrides all rules",
    "brand_override":   "Matches Brand / Supplier field for the entire brand",
}

st.set_page_config(
    page_title="Rules Library · VirVentures",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
from src.auth import require_login, render_logout
require_login()
render_logout()
render_sidebar("rules")
page_header("📋 Rules Library",
            "Manage classification rules — no code changes needed")


# ── Load rules from Google Sheets ─────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def _load_rules_df() -> pd.DataFrame:
    client      = _get_client()
    sheet_id    = _get_sheet_id()
    spreadsheet = client.open_by_key(sheet_id)
    try:
        ws = spreadsheet.worksheet(RULES_SHEET_NAME)
    except Exception:
        return pd.DataFrame()
    records = ws.get_all_records()
    return pd.DataFrame(records) if records else pd.DataFrame()


def _get_ws():
    client      = _get_client()
    sheet_id    = _get_sheet_id()
    return client.open_by_key(sheet_id).worksheet(RULES_SHEET_NAME)


with st.spinner("Loading Rules Library…"):
    rules_df = _load_rules_df()

# ── Summary KPIs ───────────────────────────────────────────────────────────────
if not rules_df.empty:
    active_df = rules_df[rules_df.get("Active", pd.Series(["Yes"]*len(rules_df))).astype(str).str.lower() == "yes"]
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Total Rules", len(rules_df), "in library", "navy")
    with c2: kpi_card("Active", len(active_df), "currently applied", "green")
    with c3:
        cat = (rules_df["Rule Type"] == "category_keyword").sum() if "Rule Type" in rules_df else 0
        kpi_card("Category Rules", cat, "keyword matches", "orange")
    with c4:
        asin_ov = (rules_df["Rule Type"] == "asin_override").sum() if "Rule Type" in rules_df else 0
        kpi_card("ASIN Overrides", asin_ov, "exact matches", "amber")

    st.markdown("<br>", unsafe_allow_html=True)

# ── Add New Rule ───────────────────────────────────────────────────────────────
with st.expander("➕ Add New Rule", expanded=False):
    st.markdown("Rules added here are applied on the next classification run.")
    with st.form("add_rule_form", clear_on_submit=True):
        fc1, fc2 = st.columns(2)
        with fc1:
            rule_type = st.selectbox("Rule Type", RULE_TYPES)
            st.caption(RULE_TYPE_DESCRIPTIONS.get(rule_type, ""))
        with fc2:
            classification = st.selectbox("Classification", ["Non-Returnable", "Returnable"])

        fv1, fv2 = st.columns(2)
        with fv1:
            value = st.text_input(
                "Value / Keyword",
                placeholder="e.g. aerosol  OR  B00XXXXXXXX (ASIN)  OR  3m (brand)",
            )
        with fv2:
            confidence = st.selectbox("Confidence", ["High", "Medium", "Low"])

        notes    = st.text_input("Notes", placeholder="Brief explanation, e.g. Hazmat aerosol")
        added_by = st.text_input("Added By", placeholder="Your name")

        submitted = st.form_submit_button("💾 Add Rule", type="primary",
                                           use_container_width=True)
        if submitted:
            if not value.strip():
                st.error("Value/Keyword cannot be empty.")
            else:
                try:
                    ws = _get_ws()
                    import time
                    from datetime import date
                    ws.append_row([
                        rule_type,
                        value.strip().lower() if rule_type != "asin_override" else value.strip().upper(),
                        classification,
                        confidence,
                        notes.strip(),
                        added_by.strip() or "Team",
                        str(date.today()),
                        "Yes",
                    ])
                    time.sleep(0.5)
                    _load_rules_df.clear()
                    st.success(f"✅ Rule added: `{rule_type}` → `{value.strip()}`")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save rule: {e}")

# ── Rules Table ────────────────────────────────────────────────────────────────
if rules_df.empty:
    st.info("Rules Library is empty. Run `main.py` once to create it with defaults.", icon="ℹ️")
    st.stop()

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">All Rules</div>', unsafe_allow_html=True)

# Filters
tf1, tf2, tf3 = st.columns(3)
with tf1:
    type_filter = st.multiselect(
        "Rule Type",
        options=rules_df["Rule Type"].unique().tolist() if "Rule Type" in rules_df else [],
        default=[],
        placeholder="All types",
    )
with tf2:
    class_filter = st.multiselect(
        "Classification",
        options=["Non-Returnable", "Returnable"],
        default=[],
        placeholder="All",
    )
with tf3:
    active_filter = st.selectbox("Active", ["All", "Active only", "Inactive only"])

filtered = rules_df.copy()
if type_filter:
    filtered = filtered[filtered["Rule Type"].isin(type_filter)]
if class_filter and "Classification" in filtered.columns:
    filtered = filtered[filtered["Classification"].isin(class_filter)]
if active_filter == "Active only" and "Active" in filtered.columns:
    filtered = filtered[filtered["Active"].astype(str).str.lower() == "yes"]
elif active_filter == "Inactive only" and "Active" in filtered.columns:
    filtered = filtered[filtered["Active"].astype(str).str.lower() != "yes"]

st.markdown(f"**{len(filtered):,} rules**", unsafe_allow_html=True)

show_cols = [c for c in ["Rule Type", "Value", "Classification", "Confidence",
                           "Notes", "Added By", "Date Added", "Active"]
             if c in filtered.columns]

st.dataframe(
    filtered[show_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Rule Type":      st.column_config.TextColumn(width=140),
        "Value":          st.column_config.TextColumn("Keyword / Value", width=200),
        "Classification": st.column_config.TextColumn(width=130),
        "Confidence":     st.column_config.TextColumn(width=100),
        "Notes":          st.column_config.TextColumn(width=260),
        "Added By":       st.column_config.TextColumn(width=100),
        "Date Added":     st.column_config.TextColumn(width=110),
        "Active":         st.column_config.TextColumn(width=70),
    },
)
st.markdown("</div>", unsafe_allow_html=True)

# ── Toggle Active/Inactive ─────────────────────────────────────────────────────
with st.expander("🔧 Deactivate / Reactivate a Rule", expanded=False):
    st.markdown(
        "Enter the exact keyword/ASIN value of the rule you want to toggle.",
        unsafe_allow_html=True,
    )
    col_v, col_a, col_btn = st.columns([3, 1, 1])
    with col_v:
        toggle_value = st.text_input("Rule value (keyword or ASIN)", key="toggle_val",
                                      label_visibility="collapsed",
                                      placeholder="Exact keyword or ASIN…")
    with col_a:
        new_active = st.selectbox("Set to", ["Yes", "No"], key="toggle_active",
                                   label_visibility="collapsed")
    with col_btn:
        if st.button("Apply", use_container_width=True):
            if toggle_value.strip():
                try:
                    ws       = _get_ws()
                    records  = ws.get_all_records()
                    headers  = ws.row_values(1)
                    val_col  = headers.index("Value") + 1
                    act_col  = headers.index("Active") + 1
                    updated  = 0
                    for i, rec in enumerate(records, start=2):
                        if str(rec.get("Value", "")).strip().lower() == toggle_value.strip().lower():
                            ws.update_cell(i, act_col, new_active)
                            updated += 1
                    import time; time.sleep(0.5)
                    _load_rules_df.clear()
                    if updated:
                        st.success(f"✅ Updated {updated} rule(s) to Active={new_active}")
                        st.rerun()
                    else:
                        st.warning("No matching rule found.")
                except Exception as e:
                    st.error(f"Error: {e}")

# ── Export rules ───────────────────────────────────────────────────────────────
st.divider()
st.download_button(
    "⬇  Export Rules Library (CSV)",
    data=rules_df.to_csv(index=False).encode("utf-8"),
    file_name="virventures_rules_library.csv",
    mime="text/csv",
)
