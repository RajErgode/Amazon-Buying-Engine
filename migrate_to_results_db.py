"""
One-time migration: push all classified items from the main Google Sheet
into the Results Database tab used by the Streamlit dashboard.
Run once: python migrate_to_results_db.py
"""
import os
import sys
import time
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from src.sheets import read_sheet
from src.storage import upsert_results, _get_results_ws, RESULT_COLUMNS


def main():
    print("Reading all classified items from main Google Sheet...")
    df = read_sheet()

    # Keep only rows that have been classified
    classified = df[df["Current Returnable Status"].notna() &
                    (df["Current Returnable Status"] != "") &
                    (df["Current Returnable Status"] != "Unknown") |
                    (df.get("Confidence", pd.Series(dtype=str)).notna())]

    classified = df[df["Current Returnable Status"].isin(
        ["Returnable", "Non-Returnable", "Unknown"]
    )].copy()

    print(f"Found {len(classified)} classified rows to migrate.")

    # Map main sheet columns → Results Database columns
    rows = []
    for _, row in classified.iterrows():
        rows.append({
            "ASIN":          str(row.get("ASIN", "")).strip().upper(),
            "Title":         str(row.get("Product Name / Title", "")).strip(),
            "Brand":         str(row.get("Brand / Supplier", "")).strip(),
            "Category":      str(row.get("Category", "")).strip(),
            "Status":        str(row.get("Current Returnable Status", "Unknown")).strip(),
            "Returnable?":   str(row.get("Returnable?", "Review")).strip(),
            "Confidence":    str(row.get("Confidence", "")).strip(),
            "Reason":        str(row.get("Classification Reason", "")).strip(),
            "Classified By": "rules",
            "Run Date":      str(row.get("Last Checked", "2026-03-27")).strip(),
            "Source File":   "Migration from main sheet",
        })

    # Remove rows with no ASIN
    rows = [r for r in rows if len(r["ASIN"]) == 10]

    print(f"Migrating {len(rows)} valid rows to Results Database tab...")
    written = upsert_results(rows, source_file="Migration from main sheet")
    print(f"\nDone! {written} rows written to Results Database.")
    print("Refresh the Streamlit dashboard to see the data.")


if __name__ == "__main__":
    main()
