"""
ingest_keepa_batch.py
---------------------
One-time ingestion of a Keepa XLSX export into the VirVentures pipeline.

Steps:
  1. Read the Keepa export and normalise columns
  2. Merge new entries into keepa_export_lookup.json
  3. Identify which ASINs are NOT yet on the Google Sheet
  4. Append those new ASINs (with title / brand / category) to the sheet
  5. Print a summary so main.py can be run next
"""

import json
import os
import re
import sys
import time

import pandas as pd
import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

# ── paths ──────────────────────────────────────────────────────────────────────
KEEPA_XLSX  = r"C:\Users\rajko\Desktop\Test\KeepaExport-2026-04-02-ProductViewer.xlsx"
LOOKUP_FILE = "keepa_export_lookup.json"

# ── Google Sheets column names (must match sheet header row exactly) ──────────
ASIN_COL        = "ASIN"
MARKETPLACE_COL = "Marketplace"
BRAND_COL       = "Brand / Supplier"
TITLE_COL       = "Product Name / Title"
CATEGORY_COL    = "Category"
DESCRIPTION_COL = "Description"
STATUS_COL      = "Current Returnable Status"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── helpers ────────────────────────────────────────────────────────────────────

def _gspread_client():
    key_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    creds = Credentials.from_service_account_file(key_file, scopes=SCOPES)
    return gspread.authorize(creds)


def _extract_subcategory(rank_str: str) -> str:
    """Turn '# 6 | Top 0.86% | Aerosol Adhesives' → 'Aerosol Adhesives'."""
    if not isinstance(rank_str, str):
        return ""
    parts = [p.strip() for p in rank_str.split("|")]
    return parts[-1] if len(parts) >= 3 else ""


def _clean(val) -> str:
    if pd.isna(val):
        return ""
    return str(val).strip()


# ── Step 1 – read & normalise Keepa export ────────────────────────────────────
print("=" * 60)
print("  VirVentures – Keepa Batch Ingestion")
print("=" * 60)

print("\n[1/4] Reading Keepa export …")
df = pd.read_excel(KEEPA_XLSX, sheet_name=None)
sheet_name = list(df.keys())[0]
df = df[sheet_name]

# Normalise ASIN column
df["ASIN"] = df["ASIN"].astype(str).str.strip().str.upper()
df = df[df["ASIN"].str.match(r"^B[A-Z0-9]{9}$")]   # keep valid ASINs only
print(f"      {len(df)} valid ASINs in export")

# Map to lookup schema
LOOKUP_MAP = {
    "Is HazMat":         "Is HazMat",
    "Is heat sensitive": "Is heat sensitive",
    "Adult Product":     "Adult Product",
    "Batteries Required":"Batteries Required",
    "Batteries Included":"Batteries Included",
    "Item Type":         "Item Type",
    "Material":          "Material",
}


# ── Step 2 – update keepa_export_lookup.json ──────────────────────────────────
print("\n[2/4] Updating keepa_export_lookup.json …")

with open(LOOKUP_FILE) as fh:
    lookup: dict = json.load(fh)

existing_before = len(lookup)
added_to_lookup = 0

for _, row in df.iterrows():
    asin = row["ASIN"]
    entry = {}
    for src_col, dst_key in LOOKUP_MAP.items():
        v = _clean(row.get(src_col, ""))
        entry[dst_key] = v if v else "no" if "haz" in dst_key.lower() or "heat" in dst_key.lower() or "adult" in dst_key.lower() or "batter" in dst_key.lower() else v
    if asin not in lookup:
        lookup[asin] = entry
        added_to_lookup += 1
    else:
        # Merge — fill in any blank fields
        for k, v in entry.items():
            if v and not lookup[asin].get(k):
                lookup[asin][k] = v

with open(LOOKUP_FILE, "w") as fh:
    json.dump(lookup, fh, indent=2)

print(f"      {added_to_lookup} new entries added  |  {len(lookup)} total in lookup")


# ── Step 3 – find ASINs not yet on the Google Sheet ───────────────────────────
print("\n[3/4] Checking Google Sheet for existing ASINs …")

sheet_id = os.getenv("GOOGLE_SHEET_ID")
client   = _gspread_client()
wb       = client.open_by_key(sheet_id)
sheet    = wb.sheet1

all_values = sheet.get_all_values()
headers    = list(all_values[0])

# Ensure required columns exist (add if missing)
required_headers = [ASIN_COL, MARKETPLACE_COL, BRAND_COL, TITLE_COL, CATEGORY_COL, DESCRIPTION_COL]
for col in required_headers:
    if col not in headers:
        headers.append(col)
        sheet.update_cell(1, len(headers), col)
        time.sleep(1)

asin_col_idx = headers.index(ASIN_COL)
sheet_asins  = {r[asin_col_idx].strip().upper() for r in all_values[1:] if len(r) > asin_col_idx and r[asin_col_idx].strip()}

new_asins_df = df[~df["ASIN"].isin(sheet_asins)].copy()
print(f"      {len(sheet_asins)} ASINs already on sheet")
print(f"      {len(new_asins_df)} NEW ASINs to append")


# ── Step 4 – append new rows to Google Sheet ──────────────────────────────────
if new_asins_df.empty:
    print("\n[4/4] Nothing to append — all ASINs already on sheet.")
else:
    print(f"\n[4/4] Appending {len(new_asins_df)} rows to Google Sheet …")

    col_idx = {h: i for i, h in enumerate(headers)}

    rows_to_append = []
    for _, row in new_asins_df.iterrows():
        new_row = [""] * len(headers)

        asin  = row["ASIN"]
        title = _clean(row.get("Title", ""))
        brand = _clean(row.get("Brand", ""))
        item_type = _clean(row.get("Item Type", ""))
        subcategory = _extract_subcategory(_clean(row.get("Sales Rank: Subcategory Sales Ranks", "")))
        category = subcategory or item_type  # prefer human-readable subcategory
        # Column Y (index 24) = "Description & Features: Description"
        import math
        desc_raw = row.iloc[24] if len(row) > 24 else ""
        description = str(desc_raw).strip()[:2000] if not (isinstance(desc_raw, float) and math.isnan(desc_raw)) else ""

        new_row[col_idx[ASIN_COL]]   = asin
        new_row[col_idx[MARKETPLACE_COL]] = "Amazon US"
        if BRAND_COL in col_idx:
            new_row[col_idx[BRAND_COL]] = brand
        if TITLE_COL in col_idx:
            new_row[col_idx[TITLE_COL]] = title
        if CATEGORY_COL in col_idx:
            new_row[col_idx[CATEGORY_COL]] = category
        if DESCRIPTION_COL in col_idx:
            new_row[col_idx[DESCRIPTION_COL]] = description

        rows_to_append.append(new_row)

    # Append in batches of 100 to stay within API limits
    BATCH = 100
    for i in range(0, len(rows_to_append), BATCH):
        batch = rows_to_append[i : i + BATCH]
        sheet.append_rows(batch, value_input_option="USER_ENTERED")
        print(f"      Appended rows {i+1}–{min(i+BATCH, len(rows_to_append))} …")
        if i + BATCH < len(rows_to_append):
            time.sleep(3)

    print(f"      ✓ {len(rows_to_append)} rows appended to Google Sheet")


# ── Summary ────────────────────────────────────────────────────────────────────
print()
print("=" * 60)
print("  Ingestion Complete")
print("=" * 60)
print(f"  Keepa lookup:  {existing_before} → {len(lookup)} entries")
print(f"  New sheet rows: {len(new_asins_df)}")
print()
print("  Next step:  python main.py --skip-keepa")
print("=" * 60)
