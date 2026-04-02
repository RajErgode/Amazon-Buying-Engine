"""
add_category_rules_batch1.py
-----------------------------
Adds NR category_keyword rules for product types confirmed NR
from the 2026-04-02 Keepa batch.

Category keyword matching is substring-based (case-insensitive) against
the Item Type / Subcategory fields — so 'adult-exotic' covers
adult-exotic-hosiery, adult-exotic-lingerie-sets, adult-exotic-costumes, etc.
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
TODAY = "2026-04-02"

# (keyword, note)
# keyword is matched as substring against item type / subcategory (case-insensitive)
NEW_CATEGORY_RULES = [
    # ── Condoms & Sexual Health ───────────────────────────────────────────────
    ("male-condoms",            "Condoms — health/hygiene, non-returnable"),
    ("condoms",                 "Condoms — health/hygiene, non-returnable"),
    ("sexual-lubricants",       "Sexual lubricants — liquid personal care, non-returnable"),
    ("water-based-sexual",      "Water-based sexual lubricants — liquid, non-returnable"),
    ("feminine-washes",         "Feminine wash — personal hygiene liquid, non-returnable"),
    ("bondage-restraints",      "Bondage/restraints — adult intimate product, non-returnable"),
    ("sex-toys",                "Sex toys — adult intimate product, non-returnable"),
    ("sex-games",               "Sex games/novelties — adult product, non-returnable"),
    ("sex-and-sensuality",      "Adult sensuality products — non-returnable"),
    ("harness-and-strap",       "Adult harness/strap-on — intimate product, non-returnable"),
    ("adult-novelty",           "Adult novelty — non-returnable"),
    ("multipurpose-cleaners",   "Adult toy cleaner / cleaners — consumable, non-returnable"),

    # ── Adult Apparel / Lingerie ──────────────────────────────────────────────
    ("adult-exotic",            "Adult exotic lingerie/hosiery/costume — non-returnable per Amazon policy"),

    # ── Massage & Body Oils ───────────────────────────────────────────────────
    ("massage-oils",            "Massage oils — liquid personal care, non-returnable"),
    ("massage-candles",         "Massage candles — consumable, non-returnable"),
    ("body-oils",               "Body oils — liquid personal care, non-returnable"),

    # ── Supplements & Consumables ─────────────────────────────────────────────
    ("colloidal-silver",        "Colloidal silver supplement — consumable, non-returnable"),
    ("mineral-supplements",     "Mineral supplements — consumable, non-returnable"),
    ("horse-vitamins",          "Equine vitamins/minerals — consumable supplement, non-returnable"),
    ("horse-digestive",         "Equine digestive supplements — consumable, non-returnable"),
    ("horse-skin-coat",         "Equine skin/coat supplements — consumable, non-returnable"),
    ("equine-supplement",       "Equine supplement — consumable, non-returnable"),
    ("livestock-health",        "Livestock health supplement — consumable, non-returnable"),
    ("pet-hip-and-joint",       "Pet joint supplement — consumable, non-returnable"),

    # ── Food & Drink ──────────────────────────────────────────────────────────
    ("fruit-juices",            "Juice/drink product — food consumable, non-returnable"),
    ("powdered-soft-drink",     "Powdered drink mix — food consumable, non-returnable"),
    ("drink-mixes",             "Drink mixes — food consumable, non-returnable"),
    ("coarse-salt",             "Salt/de-icing product — consumable, non-returnable"),
    ("snow-and-ice-melting",    "Ice melt product — consumable, non-returnable"),
    ("candy",                   "Candy/confectionery — food consumable, non-returnable"),
    ("dried-millet",            "Dried grain/millet — consumable, non-returnable"),
    ("stuffing-and-polyester",  "Pillow fill/stuffing — consumable fill, non-returnable"),

    # ── Craft Consumables ─────────────────────────────────────────────────────
    ("fabric-dyes",             "Fabric dye — consumable craft supply, non-returnable"),
    ("glue-sticks",             "Glue/adhesive — consumable, non-returnable"),
    ("machine-embroidery-thread","Embroidery thread — consumable craft supply, non-returnable"),
    ("reed-diffuser",           "Reed diffuser — liquid fragrance consumable, non-returnable"),
]


def main():
    key_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    creds = Credentials.from_service_account_file(key_file, scopes=SCOPES)
    client = gspread.authorize(creds)
    ws = client.open_by_key(sheet_id).worksheet(RULES_SHEET_NAME)

    records = ws.get_all_records()
    existing_keywords = set()
    for r in records:
        if str(r.get("Rule Type", "")).strip().lower() == "category_keyword":
            existing_keywords.add(str(r.get("Value", "")).strip().lower())

    print(f"Existing category_keyword rules: {len(existing_keywords)}")

    rows_to_add = []
    skipped = []
    for keyword, note in NEW_CATEGORY_RULES:
        if keyword.lower() in existing_keywords:
            skipped.append(keyword)
        else:
            rows_to_add.append([
                "category_keyword",
                keyword,
                "Non-Returnable",
                "High",
                note,
                "VirVentures",
                TODAY,
                "Yes",
            ])

    if skipped:
        print(f"Skipped {len(skipped)} already-existing: {', '.join(skipped)}")

    if not rows_to_add:
        print("Nothing to add.")
        return

    ws.append_rows(rows_to_add, value_input_option="USER_ENTERED")
    time.sleep(1)

    print(f"\nAdded {len(rows_to_add)} new category_keyword rules (Non-Returnable).")
    print("Run main.py --skip-keepa to apply.")


if __name__ == "__main__":
    main()
