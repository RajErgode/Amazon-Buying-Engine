"""
Rules Manager — reads classification rules from Sheet 2 (Rules Library).
The team can update rules directly in the sheet without touching code.
"""

import os
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

RULES_SHEET_NAME = "Rules Library"

# Rule types supported
RULE_TYPES = [
    "category_keyword",   # Match against full category path
    "title_keyword",      # Match against product title
    "asin_override",      # Exact ASIN match — highest priority
    "brand_override",     # Match against Brand / Supplier field
]

# Default rules — loaded into sheet on first run, editable from sheet afterwards
DEFAULT_RULES = [
    # ── Hazmat / Flammable ────────────────────────────────────────────────────
    ("category_keyword", "aerosol",                "Non-Returnable", "High", "Hazmat - aerosol propellant"),
    ("category_keyword", "hazardous material",      "Non-Returnable", "High", "Hazmat classification"),
    ("category_keyword", "dangerous good",          "Non-Returnable", "High", "Dangerous goods"),
    ("category_keyword", "flammable",               "Non-Returnable", "High", "Flammable material"),
    ("category_keyword", "explosive",               "Non-Returnable", "High", "Explosive material"),
    ("category_keyword", "ammunition",              "Non-Returnable", "High", "Ammunition"),
    ("category_keyword", "compressed gas",          "Non-Returnable", "High", "Compressed gas"),
    ("category_keyword", "propane",                 "Non-Returnable", "High", "Flammable gas"),
    ("category_keyword", "butane",                  "Non-Returnable", "High", "Flammable gas"),
    ("category_keyword", "corrosive",               "Non-Returnable", "High", "Corrosive material"),
    ("category_keyword", "oxidizer",                "Non-Returnable", "High", "Oxidizing agent"),
    ("category_keyword", "radioactive",             "Non-Returnable", "High", "Radioactive material"),
    # ── Pesticides / Pest Control ─────────────────────────────────────────────
    ("category_keyword", "fly & mosquito control",  "Non-Returnable", "High", "Pesticide - regulated"),
    ("category_keyword", "flea & tick",             "Non-Returnable", "High", "Pesticide - regulated"),
    ("category_keyword", "insect control",          "Non-Returnable", "High", "Pesticide - regulated"),
    ("category_keyword", "pesticide",               "Non-Returnable", "High", "Pesticide"),
    ("category_keyword", "herbicide",               "Non-Returnable", "High", "Herbicide"),
    ("category_keyword", "fertilizer",              "Non-Returnable", "High", "Fertilizer"),
    # ── Consumables — Human & Animal ─────────────────────────────────────────
    ("category_keyword", "vitamins & supplements",  "Non-Returnable", "High", "Consumable - ingestible supplement"),
    ("category_keyword", "treats",                  "Non-Returnable", "High", "Consumable - food/treats"),
    ("category_keyword", "health supplies",         "Non-Returnable", "High", "Consumable - animal health product"),
    ("category_keyword", "grocery",                 "Non-Returnable", "High", "Food product"),
    ("category_keyword", "fresh food",              "Non-Returnable", "High", "Perishable food"),
    ("category_keyword", "perishable",              "Non-Returnable", "High", "Perishable product"),
    ("category_keyword", "live plant",              "Non-Returnable", "High", "Live/perishable"),
    ("category_keyword", "live animal",             "Non-Returnable", "High", "Live product"),
    # ── Amazon Officially Exempt Categories ──────────────────────────────────
    ("category_keyword", "handmade",                    "Non-Returnable", "High", "Amazon exempt: All handmade products"),
    ("category_keyword", "amazon handmade",             "Non-Returnable", "High", "Amazon exempt: All handmade products"),
    ("category_keyword", "amazon custom",               "Non-Returnable", "High", "Amazon exempt: Customized items"),
    ("category_keyword", "customized",                  "Non-Returnable", "High", "Amazon exempt: Customized/personalized items"),
    ("category_keyword", "sexual wellness",             "Non-Returnable", "High", "Amazon exempt: All sexual wellness products"),
    ("category_keyword", "certified pre-owned watches", "Non-Returnable", "High", "Amazon exempt: Certified pre-owned watch category"),
    ("category_keyword", "certified preowned watches",  "Non-Returnable", "High", "Amazon exempt: Certified pre-owned watch category"),
    ("category_keyword", "professional medical",        "Non-Returnable", "High", "Amazon exempt: Professional Medical Supplies subcategory"),
    ("category_keyword", "professional dental",         "Non-Returnable", "High", "Amazon exempt: Professional Dental Supplies subcategory"),
    # ── Digital / Non-physical ────────────────────────────────────────────────
    ("category_keyword", "software",                "Non-Returnable", "High", "Digital product"),
    ("category_keyword", "downloadable",            "Non-Returnable", "High", "Digital product"),
    ("category_keyword", "gift card",               "Non-Returnable", "High", "Gift card"),
    ("category_keyword", "e-gift",                  "Non-Returnable", "High", "Digital gift card"),
    # ── Title Keywords — Hazmat ───────────────────────────────────────────────
    ("title_keyword",    "aerosol",                 "Non-Returnable", "High", "Aerosol product"),
    ("title_keyword",    "flammable",               "Non-Returnable", "High", "Flammable"),
    ("title_keyword",    "propane",                 "Non-Returnable", "High", "Flammable gas"),
    ("title_keyword",    "butane",                  "Non-Returnable", "High", "Flammable gas"),
    ("title_keyword",    "hazmat",                  "Non-Returnable", "High", "Hazmat"),
    ("title_keyword",    "compressed gas",          "Non-Returnable", "High", "Compressed gas"),
    ("title_keyword",    "explosive",               "Non-Returnable", "High", "Explosive"),
    ("title_keyword",    "ammunition",              "Non-Returnable", "High", "Ammunition"),
    ("title_keyword",    "corrosive",               "Non-Returnable", "High", "Corrosive"),
    ("title_keyword",    "oxidizer",                "Non-Returnable", "High", "Oxidizing agent"),
    ("title_keyword",    "paint thinner",           "Non-Returnable", "High", "Hazardous solvent"),
    ("title_keyword",    "acetone",                 "Non-Returnable", "High", "Hazardous solvent"),
    ("title_keyword",    "isopropyl alcohol",       "Non-Returnable", "High", "Hazardous solvent"),
    ("title_keyword",    "lithium battery",         "Non-Returnable", "High", "Lithium battery"),
    ("title_keyword",    "lithium batteries",       "Non-Returnable", "High", "Lithium batteries"),
    # ── Title Keywords — Pesticides ───────────────────────────────────────────
    ("title_keyword",    "fly spray",               "Non-Returnable", "High", "Pesticide - fly spray"),
    ("title_keyword",    "fly repellent",           "Non-Returnable", "High", "Pesticide - repellent"),
    ("title_keyword",    "insecticide",             "Non-Returnable", "High", "Insecticide"),
    ("title_keyword",    "pesticide",               "Non-Returnable", "High", "Pesticide"),
    ("title_keyword",    "mosquito repellent",      "Non-Returnable", "High", "Pesticide - repellent"),
    ("title_keyword",    "insect repellent",        "Non-Returnable", "High", "Insecticide"),
    ("title_keyword",    "bug spray",               "Non-Returnable", "High", "Pesticide"),
    ("title_keyword",    "emulsifiable concentrate","Non-Returnable", "High", "Pesticide concentrate"),
    # ── Title Keywords — Pharmaceutical / Medical ─────────────────────────────
    ("title_keyword",    "ophthalmic",              "Non-Returnable", "High", "Pharmaceutical - eye product"),
    ("title_keyword",    "ointment",                "Non-Returnable", "High", "Pharmaceutical - topical"),
    ("title_keyword",    "medicated",               "Non-Returnable", "High", "Medicated product"),
    # ── Title Keywords — Consumable liquids / oils ────────────────────────────
    ("title_keyword",    "mink oil",                "Non-Returnable", "High", "Liquid oil - consumable/perishable"),
    ("title_keyword",    "linseed oil",             "Non-Returnable", "High", "Liquid oil"),
    ("title_keyword",    "neatsfoot oil",           "Non-Returnable", "High", "Liquid oil"),
    ("title_keyword",    "liquid concentrate",      "Non-Returnable", "High", "Liquid concentrate"),
    # ── Title Keywords — Custom / Personalised ───────────────────────────────
    ("title_keyword",    "customized",              "Non-Returnable", "High", "Customized/personalized product"),
    ("title_keyword",    "personalized",            "Non-Returnable", "High", "Personalized product"),
    ("title_keyword",    "engraved",                "Non-Returnable", "High", "Engraved/custom product"),
    ("title_keyword",    "custom made",             "Non-Returnable", "High", "Custom made product"),
    ("title_keyword",    "made to order",           "Non-Returnable", "High", "Made to order product"),
    # ── Title Keywords — Explicitly labelled ─────────────────────────────────
    ("title_keyword",    "non-returnable",          "Non-Returnable", "High", "Explicitly labelled"),
    ("title_keyword",    "not returnable",          "Non-Returnable", "High", "Explicitly labelled"),
    # ── Generally Returnable Categories ──────────────────────────────────────
    ("category_keyword", "electronics",             "Returnable",     "Medium", "Standard returnable category"),
    ("category_keyword", "computers",               "Returnable",     "Medium", "Standard returnable category"),
    ("category_keyword", "clothing",                "Returnable",     "Medium", "Standard returnable category"),
    ("category_keyword", "shoes",                   "Returnable",     "Medium", "Standard returnable category"),
    ("category_keyword", "toys & games",            "Returnable",     "Medium", "Standard returnable category"),
    ("category_keyword", "sports & outdoors",       "Returnable",     "Medium", "Standard returnable category"),
    ("category_keyword", "office products",         "Returnable",     "Medium", "Standard returnable category"),
    ("category_keyword", "books",                   "Returnable",     "Medium", "Standard returnable category"),
    ("category_keyword", "automotive",              "Returnable",     "Medium", "Standard returnable category"),
    ("category_keyword", "musical instruments",     "Returnable",     "Medium", "Standard returnable category"),
    ("category_keyword", "arts, crafts & sewing",   "Returnable",     "Medium", "Standard returnable category"),
    ("category_keyword", "tools & home improvement","Returnable",     "Medium", "Standard returnable category"),
    ("category_keyword", "home & kitchen",          "Returnable",     "Medium", "Standard returnable category"),
    ("category_keyword", "industrial & scientific", "Returnable",     "Medium", "Standard returnable category"),
]


def _get_client():
    key_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    creds = Credentials.from_service_account_file(key_file, scopes=SCOPES)
    return gspread.authorize(creds)


def setup_rules_sheet():
    """
    Create the Rules Library sheet if it doesn't exist and populate
    with default rules. Safe to call on every run — skips if already set up.
    """
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    client = _get_client()
    spreadsheet = client.open_by_key(sheet_id)

    existing = [ws.title for ws in spreadsheet.worksheets()]
    if RULES_SHEET_NAME in existing:
        return  # Already exists — don't overwrite

    ws = spreadsheet.add_worksheet(title=RULES_SHEET_NAME, rows=500, cols=8)

    headers = ["Rule Type", "Value", "Classification",
               "Confidence", "Notes", "Added By", "Date Added", "Active"]
    ws.append_row(headers)

    rows = []
    for rule_type, value, classification, confidence, notes in DEFAULT_RULES:
        rows.append([rule_type, value, classification,
                     confidence, notes, "System", "2026-03-27", "Yes"])
    ws.append_rows(rows)

    # Format header row
    from src.formatter import rgb
    spreadsheet.batch_update({"requests": [{
        "repeatCell": {
            "range": {
                "sheetId": ws.id,
                "startRowIndex": 0, "endRowIndex": 1,
                "startColumnIndex": 0, "endColumnIndex": 8,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": rgb("#1B3A5C"),
                    "textFormat": {
                        "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                        "bold": True, "fontSize": 10, "fontFamily": "Arial",
                    },
                    "horizontalAlignment": "CENTER",
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
        }
    }]})

    col_widths = [140, 220, 150, 90, 280, 100, 110, 70]
    reqs = []
    for i, w in enumerate(col_widths):
        reqs.append({
            "updateDimensionProperties": {
                "range": {"sheetId": ws.id, "dimension": "COLUMNS",
                          "startIndex": i, "endIndex": i + 1},
                "properties": {"pixelSize": w},
                "fields": "pixelSize",
            }
        })
    spreadsheet.batch_update({"requests": reqs})
    print(f"     Rules Library sheet created with {len(DEFAULT_RULES)} default rules.")


def load_rules():
    """
    Load rules from the Rules Library sheet.
    Returns a dict with keys: category_non_ret, category_ret,
    title_non_ret, asin_overrides, brand_overrides
    """
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    client = _get_client()
    spreadsheet = client.open_by_key(sheet_id)

    try:
        ws = spreadsheet.worksheet(RULES_SHEET_NAME)
    except gspread.WorksheetNotFound:
        setup_rules_sheet()
        ws = spreadsheet.worksheet(RULES_SHEET_NAME)

    records = ws.get_all_records()
    df = pd.DataFrame(records)

    # Only use active rules
    if "Active" in df.columns:
        df = df[df["Active"].astype(str).str.strip().str.lower() == "yes"]

    rules = {
        "category_non_ret": [],
        "category_ret": [],
        "title_non_ret": [],
        "asin_overrides": {},
        "brand_overrides": {},
    }

    for _, row in df.iterrows():
        rule_type = str(row.get("Rule Type", "")).strip().lower()
        value = str(row.get("Value", "")).strip().lower()
        classification = str(row.get("Classification", "")).strip()
        confidence = str(row.get("Confidence", "Medium")).strip()
        notes = str(row.get("Notes", "")).strip()

        if not value or not classification:
            continue

        if rule_type == "category_keyword":
            if classification == "Non-Returnable":
                rules["category_non_ret"].append((value, confidence, notes))
            else:
                rules["category_ret"].append((value, confidence, notes))

        elif rule_type == "title_keyword":
            if classification == "Non-Returnable":
                rules["title_non_ret"].append((value, confidence, notes))

        elif rule_type == "asin_override":
            rules["asin_overrides"][value.upper()] = (classification, confidence, notes)

        elif rule_type == "brand_override":
            rules["brand_overrides"][value.lower()] = (classification, confidence, notes)

    return rules
