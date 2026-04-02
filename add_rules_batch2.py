"""Add confirmed rules from batch 2 feedback."""
import os, gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"), scopes=SCOPES)
client = gspread.authorize(creds)
ws = client.open_by_key(os.getenv("GOOGLE_SHEET_ID")).worksheet("Rules Library")

DATE = "2026-04-01"
NR, R, H = "Non-Returnable", "Returnable", "High"

new_rules = [
    # A — Nexcare cloth tape → Returnable
    ["asin_override","B001TSJ8XC",R,H,"Nexcare Durable Cloth Tape — confirmed returnable","VirVentures",DATE,"Yes"],

    # B — Compression knee/ankle braces
    ["title_keyword","compression knee",NR,H,"Compression knee support — hygiene non-returnable","VirVentures",DATE,"Yes"],
    ["title_keyword","knee sleeve",NR,H,"Knee sleeve — hygiene non-returnable","VirVentures",DATE,"Yes"],
    ["title_keyword","knee stabilizer",NR,H,"Knee stabilizer brace — hygiene non-returnable","VirVentures",DATE,"Yes"],
    ["title_keyword","ankle sleeve",NR,H,"Ankle compression sleeve — hygiene non-returnable","VirVentures",DATE,"Yes"],
    ["title_keyword","compression ankle",NR,H,"Compression ankle — hygiene non-returnable","VirVentures",DATE,"Yes"],
    ["asin_override","B0057D80FC",NR,H,"FUTURO Comfort Knee with Stabilizers","VirVentures",DATE,"Yes"],
    ["asin_override","B0FC45BTR6",NR,H,"ACE Flex Comfort Compression Knee Sleeve","VirVentures",DATE,"Yes"],
    ["asin_override","B0FC4LJ5F1",NR,H,"Futuro Premium Compression Ankle Sleeve","VirVentures",DATE,"Yes"],

    # C — Air / furnace filters
    ["title_keyword","air filter",NR,H,"AC/furnace air filter — single use","VirVentures",DATE,"Yes"],
    ["title_keyword","furnace filter",NR,H,"Furnace air filter — single use","VirVentures",DATE,"Yes"],
    ["title_keyword","filtrete",NR,H,"Filtrete branded filter — single use","VirVentures",DATE,"Yes"],
    ["category_keyword","hvac",NR,H,"HVAC category — filters non-returnable","VirVentures",DATE,"Yes"],
    ["asin_override","B005F5D3RW",NR,H,"Filtrete 20x20x1 MERV 13 air filter","VirVentures",DATE,"Yes"],
    ["asin_override","B00TUDHM5O",NR,H,"Filtrete 16x30x1 MERV 12 air filter","VirVentures",DATE,"Yes"],

    # D — Command adhesive products
    ["title_keyword","command hook",NR,H,"3M Command adhesive hook — single use","VirVentures",DATE,"Yes"],
    ["title_keyword","command strip",NR,H,"3M Command adhesive strip — single use","VirVentures",DATE,"Yes"],
    ["title_keyword","command hanger",NR,H,"3M Command adhesive hanger — single use","VirVentures",DATE,"Yes"],
    ["title_keyword","command caddy",NR,H,"3M Command adhesive caddy — single use","VirVentures",DATE,"Yes"],
    ["asin_override","B071RCDFHL",NR,H,"Command Under Sink Sponge Caddy","VirVentures",DATE,"Yes"],
    ["asin_override","B00OI6JATE",NR,H,"Command Large Multi-Hook","VirVentures",DATE,"Yes"],
    ["asin_override","B00100NH5O",NR,H,"Command Wire-Back Frame Hanger","VirVentures",DATE,"Yes"],
    ["asin_override","B0794JJ5GH",NR,H,"3M Mini Hook — adhesive non-returnable","VirVentures",DATE,"Yes"],

    # E — Tapes and foam mounting
    ["title_keyword","foam mounting",NR,H,"Foam mounting tape/squares — single use adhesive","VirVentures",DATE,"Yes"],
    ["title_keyword","mounting squares",NR,H,"Mounting squares — single use adhesive","VirVentures",DATE,"Yes"],
    ["asin_override","B004MEBBWG",NR,H,"3M Automotive Performance Masking Tape","VirVentures",DATE,"Yes"],
    ["asin_override","B016Z5TWSO",NR,H,"Highland Invisible Permanent Mending Tape","VirVentures",DATE,"Yes"],
    ["asin_override","B00006IF63",NR,H,"Scotch Double Sided Tape","VirVentures",DATE,"Yes"],
    ["asin_override","B01H9K73JY",NR,H,"Post-It Note Labeling Tape","VirVentures",DATE,"Yes"],
    ["asin_override","B00347A8EY",NR,H,"Scotch Permanent Foam Mounting Squares","VirVentures",DATE,"Yes"],
    ["asin_override","B000FP8HFK",NR,H,"3M Automotive Refinish Masking Tape","VirVentures",DATE,"Yes"],
    ["asin_override","B0C2ZS1W32",NR,H,"Scotch Tape Dispenser","VirVentures",DATE,"Yes"],

    # F — Post-it brand
    ["title_keyword","post-it",NR,H,"Post-it branded products — brand policy non-returnable","VirVentures",DATE,"Yes"],
    ["asin_override","B00006IF84",NR,H,"Post-it Labeling & Cover-Up Tape","VirVentures",DATE,"Yes"],
    ["asin_override","B0002T54K0",NR,H,"Post-it Flags + Highlighter","VirVentures",DATE,"Yes"],
    ["asin_override","B00006JNMF",NR,H,"Post-it Flags in Dispenser","VirVentures",DATE,"Yes"],
    ["asin_override","B004IKXTHE",NR,H,"Post-it Mini Notes","VirVentures",DATE,"Yes"],

    # G — Scissors and felt pads
    ["title_keyword","furniture pad",NR,H,"Felt furniture pads — adhesive non-returnable","VirVentures",DATE,"Yes"],
    ["title_keyword","felt pad",NR,H,"Felt pads — adhesive non-returnable","VirVentures",DATE,"Yes"],
    ["asin_override","B000I1Z0T2",NR,H,"Scotch 8in Home & Office Scissors","VirVentures",DATE,"Yes"],
    ["asin_override","B004QJU99I",NR,H,"Scotch Precision Ultra-Edge Titanium Scissors","VirVentures",DATE,"Yes"],
    ["asin_override","B002QUZNQ8",NR,H,"Scotch Multi-Purpose Scissors 6in","VirVentures",DATE,"Yes"],
    ["asin_override","B0CGC865NP",NR,H,"Scotch Non-Stick Unboxing Scissors","VirVentures",DATE,"Yes"],
    ["asin_override","B01N8VO7OB",NR,H,"Scotch Felt Furniture Pads 32 PCS","VirVentures",DATE,"Yes"],

    # I — Cable splice kit + paint spray gun system
    ["asin_override","B07HXVMFJ2",NR,H,"Scotchcast Inline Resin Power Cable Splice Kit","VirVentures",DATE,"Yes"],
    ["title_keyword","spray gun system",NR,H,"Paint spray gun system — industrial kit non-returnable","VirVentures",DATE,"Yes"],
    ["asin_override","B001UO50LY",NR,H,"3M PPS 2.0 Paint Spray Gun System Starter Kit","VirVentures",DATE,"Yes"],
]

# Check existing to avoid duplicates
records = ws.get_all_records()
existing = set()
for r in records:
    existing.add((str(r.get("Rule Type","")).strip(), str(r.get("Value","")).strip().lower()))

to_add = [r for r in new_rules if (r[0], r[1].lower()) not in existing]
skipped = len(new_rules) - len(to_add)

if to_add:
    ws.append_rows(to_add, value_input_option="USER_ENTERED")

print(f"Added {len(to_add)} new rules. Skipped {skipped} duplicates.")
