"""
update_descriptions.py
----------------------
Backfills the Description column in Google Sheet for all ASINs
that have a description in the Keepa export but blank in the sheet.
"""

import os
import time
import json
import pandas as pd
import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

KEEPA_XLSX   = r"C:\Users\rajko\Desktop\Test\KeepaExport-2026-04-02-ProductViewer.xlsx"
DESCRIPTION_COL = "Description"
ASIN_COL     = "ASIN"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

WRITE_BATCH  = 50
RATE_PAUSE   = 3

def _gspread_client():
    key_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    creds = Credentials.from_service_account_file(key_file, scopes=SCOPES)
    return gspread.authorize(creds)

print("=" * 60)
print("  Description Backfill")
print("=" * 60)

# 1. Read Keepa descriptions
print("\n[1/3] Reading Keepa descriptions ...")
df_k = pd.read_excel(KEEPA_XLSX, sheet_name=None)
sheet_name = list(df_k.keys())[0]
df_k = df_k[sheet_name]
df_k["ASIN"] = df_k["ASIN"].astype(str).str.strip().str.upper()
desc_col = df_k.columns[24]   # Column Y = "Description & Features: Description"
print(f"      Description column: '{desc_col}'")

desc_map = {}
for _, row in df_k.iterrows():
    asin = row["ASIN"]
    val  = row[desc_col]
    if pd.notna(val) and str(val).strip():
        desc_map[asin] = str(val).strip()[:2000]  # cap at 2000 chars for sheet

print(f"      {len(desc_map)} ASINs have descriptions in export")

# 2. Read Google Sheet
print("\n[2/3] Reading Google Sheet ...")
sheet_id = os.getenv("GOOGLE_SHEET_ID")
client   = _gspread_client()
wb       = client.open_by_key(sheet_id)
sheet    = wb.sheet1

all_values = sheet.get_all_values()
headers    = list(all_values[0])

if DESCRIPTION_COL not in headers:
    print(f"      Adding '{DESCRIPTION_COL}' column to sheet ...")
    headers.append(DESCRIPTION_COL)
    sheet.update_cell(1, len(headers), DESCRIPTION_COL)
    time.sleep(2)

asin_col_idx = headers.index(ASIN_COL)
desc_col_idx = headers.index(DESCRIPTION_COL)

print(f"      Sheet has {len(all_values)-1} data rows")

# 3. Build updates — only rows that have blank Description but have data in our map
print("\n[3/3] Building updates ...")
updates = []
for row_idx, row in enumerate(all_values[1:], start=2):
    asin = row[asin_col_idx].strip().upper() if len(row) > asin_col_idx else ""
    if not asin or asin not in desc_map:
        continue
    # Check current description value
    current_desc = row[desc_col_idx].strip() if len(row) > desc_col_idx else ""
    if current_desc:
        continue  # already has a description
    cell = gspread.utils.rowcol_to_a1(row_idx, desc_col_idx + 1)
    updates.append({"range": cell, "values": [[desc_map[asin]]]})

print(f"      {len(updates)} rows need description update")

if not updates:
    print("      Nothing to update.")
else:
    # Batch write
    batches = [updates[i:i+WRITE_BATCH] for i in range(0, len(updates), WRITE_BATCH)]
    for i, batch in enumerate(batches, 1):
        sheet.batch_update(batch, value_input_option="USER_ENTERED")
        print(f"      Batch {i}/{len(batches)} written ...")
        if i < len(batches):
            time.sleep(RATE_PAUSE)

print()
print("=" * 60)
print(f"  Done — {len(updates)} descriptions written to Google Sheet")
print("=" * 60)
