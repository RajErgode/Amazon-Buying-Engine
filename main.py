import os
import sys
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime

from src.sheets import read_sheet, get_unclassified, save_results, write_results_to_sheet, STATUS_COL, DESCRIPTION_COL
from src.classifier import ReturnabilityClassifier
from src.keepa_client import KeepaClient
from src.rules_manager import setup_rules_sheet, load_rules

load_dotenv()

KEEPA_API_KEY = os.getenv("KEEPA_API_KEY")
OUTPUT_FILE = "results.csv"
SKIP_KEEPA = "--skip-keepa" in sys.argv


def print_header():
    print()
    print("=" * 52)
    print("  VirVentures - Returnability Classifier v1.1")
    print("=" * 52)


def print_summary(df):
    print()
    print("=" * 52)
    print("  Classification Summary")
    print("=" * 52)
    counts = df["Current Returnable Status"].value_counts()
    total = len(df)
    for status, count in counts.items():
        pct = count / total * 100
        print(f"  {status:<20} {count:>4}  ({pct:.1f}%)")
    print(f"  {'TOTAL':<20} {total:>4}")
    print("=" * 52)
    print(f"  Output saved -> {OUTPUT_FILE}")
    print()


def main():
    print_header()

    # 1. Set up Rules Library sheet if first run, then load rules
    print("\n[1/5] Loading rules from Rules Library...")
    setup_rules_sheet()
    rules = load_rules()
    print(f"      {len(rules['category_non_ret'])} category rules (non-returnable)")
    print(f"      {len(rules['category_ret'])} category rules (returnable)")
    print(f"      {len(rules['title_non_ret'])} title keyword rules")
    print(f"      {len(rules['asin_overrides'])} ASIN overrides")
    print(f"      {len(rules['brand_overrides'])} brand overrides")

    # 2. Read master sheet
    print("\n[2/5] Reading ASINs from Google Sheet...")
    df = read_sheet()
    print(f"      {len(df)} total ASINs loaded")

    # 3. Filter to unclassified only (hybrid cache)
    unclassified = get_unclassified(df)
    already_done = len(df) - len(unclassified)
    print(f"      {already_done} already classified (skipped)")
    print(f"      {len(unclassified)} ASINs to process")

    if unclassified.empty:
        print("\n  All ASINs are already classified. Nothing to do.")
        return

    # 4. Fetch Keepa data (skippable with --skip-keepa flag)
    print("\n[3/5] Fetching Keepa product data...")
    if SKIP_KEEPA:
        print("      Keepa skipped (--skip-keepa flag) — rules-only mode")
        keepa_data = {}
    else:
        keepa = KeepaClient(KEEPA_API_KEY)
        asins = unclassified["ASIN"].dropna().unique().tolist()
        keepa_data = keepa.get_products(asins)
        print(f"      Keepa returned data for {len(keepa_data)} ASINs")

    # 5. Classify each ASIN
    print("\n[4/5] Classifying returnability...")
    classifier = ReturnabilityClassifier(rules=rules)
    rows = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    for _, row in unclassified.iterrows():
        asin        = row.get("ASIN")
        category    = row.get("Category", "")
        title       = row.get("Product Name / Title", "")
        brand       = row.get("Brand / Supplier", "")
        description = row.get(DESCRIPTION_COL, "")

        result = classifier.classify(
            asin=asin,
            category_path=category,
            title=title,
            keepa_data=keepa_data.get(asin),
            brand=brand,
            description=description,
        )

        yes_no = (
            "Yes" if result["status"] == "Returnable" else
            "No" if result["status"] == "Non-Returnable" else
            "Review"
        )
        rows.append({
            **row.to_dict(),
            "Current Returnable Status": result["status"],
            "Returnable?": yes_no,
            "Confidence": result["confidence"],
            "Classification Reason": result["reason"],
            "Last Checked": timestamp,
        })

    # 6. Save results + write back to sheet
    print("\n[5/5] Saving results...")
    df_results = pd.DataFrame(rows)
    save_results(df_results, OUTPUT_FILE)

    print("     Writing back to Google Sheet...")
    try:
        write_results_to_sheet(rows)
    except Exception as e:
        print(f"     Sheet write-back failed: {e}")
        print("     Results are still saved locally in results.csv")

    print_summary(df_results)


if __name__ == "__main__":
    main()
