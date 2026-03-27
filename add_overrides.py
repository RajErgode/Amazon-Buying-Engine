"""
One-time script: adds ASIN-level overrides for the 40 previously Unknown items.
Run once: python add_overrides.py
Safe to re-run — skips ASINs that already exist in the sheet.
"""

import os
import time
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
RULES_SHEET_NAME = "Rules Library"
TODAY = "2026-03-27"

# ── All 40 ASIN overrides ─────────────────────────────────────────────────────
# Format: (ASIN, Classification, Confidence, Notes)
OVERRIDES = [

    # ── Group A: First-aid tapes — Non-Returnable (ASIN-specific; similar items returnable) ──
    ("B00IARW9TA", "Non-Returnable", "High",  "First aid tape — brand policy non-returnable"),
    ("B001EPQGDK", "Non-Returnable", "High",  "First aid tape — brand policy non-returnable"),
    ("B005OFM6JE", "Non-Returnable", "High",  "First aid tape — brand policy non-returnable"),
    ("B00KOC7FFM", "Non-Returnable", "High",  "First aid tape — brand policy non-returnable"),
    ("B001CBBZD2", "Non-Returnable", "High",  "First aid tape — brand policy non-returnable"),
    ("B00CPLCH30", "Non-Returnable", "High",  "First aid tape — brand policy non-returnable"),
    ("B002ZJ4SWU", "Non-Returnable", "High",  "First aid tape — brand policy non-returnable"),
    ("B000GCRWQM", "Non-Returnable", "High",  "First aid tape — brand policy non-returnable"),

    # ── Group B: Bandages & wraps — Non-Returnable ───────────────────────────
    ("B00IAVV5NW", "Non-Returnable", "High",  "Bandage/wrap — hygiene non-returnable"),
    ("B002ZV6R7C", "Non-Returnable", "High",  "No-hurt wrap — hygiene non-returnable"),
    ("B000RI3ZVG", "Non-Returnable", "High",  "Vetrap bandaging tape — hygiene non-returnable"),
    ("B004OTXE1K", "Non-Returnable", "High",  "Vetrap bandaging tape — hygiene non-returnable"),
    ("B07QF2JXL9", "Non-Returnable", "High",  "ACE elastic bandage — hygiene non-returnable"),
    ("B000GG7UEW", "Non-Returnable", "High",  "Tegaderm transparent dressing — hygiene non-returnable"),
    ("B00K2FJH2A", "Non-Returnable", "High",  "Tegaderm transparent dressing — hygiene non-returnable"),
    ("B00BRGUNV2", "Non-Returnable", "High",  "Acne cover — hygiene non-returnable"),

    # ── Group C: Scotch-Brite sponges & dishwand refills — Returnable ────────
    ("B000T9ODX2", "Returnable",     "High",  "Scotch-Brite sponge — confirmed returnable"),
    ("B00565V2W4", "Returnable",     "High",  "Dishwand refills — confirmed returnable"),
    ("B0043P0GRA", "Returnable",     "High",  "Scotch-Brite sponge — confirmed returnable"),
    ("B004IR3044", "Returnable",     "High",  "Scotch-Brite sponge — confirmed returnable"),

    # ── Group D: Sandpaper sheets — Returnable ───────────────────────────────
    ("B00002N6FF", "Returnable",     "High",  "Sandpaper sheets — confirmed returnable"),
    ("B00002N6FH", "Returnable",     "High",  "Sandpaper sheets — confirmed returnable"),
    ("B00004Z4BF", "Returnable",     "High",  "Sandpaper sheets — confirmed returnable"),
    ("B002NEV6GS", "Returnable",     "High",  "Sandpaper sheets — confirmed returnable"),

    # ── Group E: Abrasive/bristle discs + utility knife — Returnable ─────────
    ("B000V9YDGM", "Returnable",     "High",  "Roloc bristle disc — confirmed returnable"),
    ("B002P50DS2", "Returnable",     "High",  "Roloc bristle disc — confirmed returnable"),
    ("B00KKUYGO6", "Returnable",     "High",  "Utility knife — confirmed returnable"),

    # ── Group F: Earplugs + back brace + ankle brace — Non-Returnable ────────
    ("B00K0Y46VU", "Non-Returnable", "High",  "Earplugs — hygiene non-returnable"),
    ("B006BV08SQ", "Non-Returnable", "High",  "Back support brace — hygiene non-returnable"),
    ("B005YU8WS8", "Non-Returnable", "High",  "Ankle compression support — hygiene non-returnable"),

    # ── Group G: Stationery — Non-Returnable (ASIN-specific; similar returnable) ──
    ("B0002DOEOS", "Non-Returnable", "High",  "Post-it notes — brand policy non-returnable"),
    ("B001A3XZB2", "Non-Returnable", "High",  "Tacky glue — brand policy non-returnable"),
    ("B005UE9GX8", "Non-Returnable", "High",  "Label tape — brand policy non-returnable"),
    ("B005UE9H7S", "Non-Returnable", "High",  "Label tape — brand policy non-returnable"),
    ("B0006HVKOC", "Non-Returnable", "High",  "Scotch tape dispenser pack — brand policy non-returnable"),

    # ── Group H: Glass cleaner / bumper guards / cable & splice kits — Non-Returnable ──
    ("B00KE9HO56", "Non-Returnable", "High",  "Glass cleaner — chemical product non-returnable"),
    ("B00OI6Y2H4", "Non-Returnable", "High",  "Bumpon protective bumpers — adhesive non-returnable"),
    ("B008BJY6W0", "Non-Returnable", "High",  "Cable repair kit — electrical kit non-returnable"),
    ("B0081JXBTE", "Non-Returnable", "High",  "Inline splice kit — electrical kit non-returnable"),
]


def main():
    key_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")

    creds = Credentials.from_service_account_file(key_file, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(sheet_id)

    try:
        ws = spreadsheet.worksheet(RULES_SHEET_NAME)
    except gspread.WorksheetNotFound:
        print("Rules Library sheet not found — run main.py first to create it.")
        return

    # Load existing ASINs to avoid duplicates
    records = ws.get_all_records()
    existing_asins = set()
    for r in records:
        if str(r.get("Rule Type", "")).strip().lower() == "asin_override":
            existing_asins.add(str(r.get("Value", "")).strip().upper())

    print(f"Found {len(existing_asins)} existing ASIN overrides in sheet.")

    rows_to_add = []
    skipped = []
    for asin, classification, confidence, notes in OVERRIDES:
        if asin.upper() in existing_asins:
            skipped.append(asin)
        else:
            rows_to_add.append([
                "asin_override",
                asin.upper(),
                classification,
                confidence,
                notes,
                "VirVentures",
                TODAY,
                "Yes",
            ])

    if skipped:
        print(f"Skipped {len(skipped)} already-existing overrides: {', '.join(skipped)}")

    if not rows_to_add:
        print("Nothing to add — all overrides already exist.")
        return

    # Write in one batch
    ws.append_rows(rows_to_add, value_input_option="USER_ENTERED")
    time.sleep(1)

    ret = sum(1 for r in rows_to_add if r[2] == "Returnable")
    non_ret = sum(1 for r in rows_to_add if r[2] == "Non-Returnable")
    print(f"\nDone! Added {len(rows_to_add)} overrides:")
    print(f"  Non-Returnable : {non_ret}")
    print(f"  Returnable     : {ret}")
    print(f"\nRe-run main.py to re-classify the sheet with the new overrides.")


if __name__ == "__main__":
    main()
