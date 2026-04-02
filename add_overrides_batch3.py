"""
add_overrides_batch3.py
-----------------------
Adds Non-Returnable ASIN overrides for all 106 Unknown items
from the 2026-04-02 Keepa batch (confirmed NR via prior scraping).
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

NR_OVERRIDES = [
    # Colloidal Silver Supplements
    ("B01CINUBWS",  "Blue Ridge Silver 10ppm 16oz"),
    ("B01DMMJO2M",  "Blue Ridge Silver 25ppm 8oz"),
    ("B074D2MMVB",  "Blue Ridge Silver 10ppm 32oz"),
    # Condoms
    ("B000050B16",  "Kimono MicroThin Condoms 3pk"),
    ("B000VL5N0A",  "Kimono MicroThin Large 3pk"),
    ("B0BLY2FTHW",  "Classic Sampler Condoms 3 sizes"),
    ("B004TTX9TW",  "LifeStyles Ultra Sensitive 12ct"),
    ("B00HA675EG",  "Durex Extra Sensitive 3ct 2pk"),
    ("B07TYZQZN5",  "Rough Rider Original Studded 3pk"),
    # Massage Oils & Candles
    ("B00015QE1S",  "Kama Sutra Massage Oil Serenity 8oz"),
    ("B00OWQ4OUA",  "Kama Sutra Ignite Massage Candle 6oz"),
    ("B0DB2PYFFL",  "Pheromone Massage Oil Candle 6oz"),
    ("B0CWDML5LT",  "Kama Sutra Sex Magnet Pheromone Oil 2oz"),
    # Feminine Wash / Personal Care
    ("B00EKNXDUC",  "Sliquid Splash Feminine Wash 8.5oz"),
    # Adult Toy Cleaner
    ("B07D32YXGX",  "Shine Tea Tree Toy Cleaner 2oz"),
    # Adult Toys
    ("B0C428YZ36",  "Natalies Toy Box Silicone Dildo"),
    ("B0DHDCCVK4",  "Blush Male Performance Cock Sleeve"),
    ("B0DYFB69KW",  "Little Genie ProBlo Deep Throat Spray"),
    # Adult Toy Bag
    ("B0BR8GD8NX",  "Blush Cotton Toy Storage Bag"),
    # Sex Games
    ("B00INYZM80",  "Kheper Games Naked Card Game"),
    ("B01F0PX8G2",  "Kheper Games Boobs Boners Card Game"),
    ("B001RNI5SS",  "Hot Spicey Party Dice"),
    # Guitar Accessories
    ("B0117TLSZS",  "John Petrucci Ultex Jazz III Picks 1.5mm"),
    ("B0016BFBO2",  "MXR Script Phase 90 LED Pedal"),
    ("B001PZ79LC",  "CAE Wah Pedal"),
    ("B0BGMPLMYP",  "Mackie H3Thrash215 Speaker Bag"),
    # Equine / Livestock Supplements
    ("B000HHJL56",  "Pennwoods Essential E Vitamin E 5lb"),
    ("B000HHNY9U",  "Figuerola LaminaSaver 1lb"),
    ("B001CCZOS8",  "Fluid Action HA Joint Therapy 32oz"),
    ("B001CD1KYY",  "Kentucky Performance Electrolyte 5lb"),
    ("B005GWWBWW",  "Formula 707 Joint 6in1 Equine 10lb"),
    ("B00GRTA4BI",  "Ultra 24 Livestock Milk Replacer 8lb"),
    ("B01M0LNUMI",  "Equine Healthcare Bit Butter 4oz"),
    ("B07YDZWBJ3",  "dac Yucca 5 Way PAC"),
    # True Lemon / Drink Mixes
    ("B004AMMPMU",  "True Lemon Crystallized Lemon Shaker 10.6oz"),
    ("B00577057O",  "True Lemon 64 Packets 2 Box"),
    ("B00E0N3OME",  "True Lemon Single Serve Packets"),
    ("B00EIJU19O",  "True Lemon 32pk Box 3 Pack"),
    ("B07BVGXSHD",  "True Citrus Lemon Shaker 1ct"),
    # Candy
    ("B07B3XGZ9D",  "Lil Boobie Pop Candy"),
    # Sewing & Quilting
    ("B07N6ZC6MF",  "Alex DIY Tie Dye Maker Kit"),
    ("B001VA1RZU",  "Round Card Holders with Case Poker"),
    ("B00114RJ9Y",  "SINGER Instant Hem Tape 3/4in 15ft"),
    ("B01CSPUM9I",  "Atkinson YKK Zipper Pulls 30pc"),
    ("B001E5VPVI",  "Machingers Quilting Gloves XS"),
    ("B000WWGLQ8",  "June Tailor Non Stick Pressing Sheet 18x18"),
    ("B00IV5R4I2",  "Superior Threads Magnifico 40wt Cone"),
    ("B07FDMQQ1N",  "Whole Country Caboodle Sewing Pattern"),
    ("B00K4Z3PEE",  "Prym Color Snap Fasteners Dark Grey 30ct"),
    ("B000BNLLHW",  "OLFA 45mm Ergonomic Rotary Cutter"),
    ("B07GVY17LT",  "Best Quilt Precision Piecing Starter Kit"),
    ("B015QJ9ZC8",  "Roxanne Glue Baste-It 6oz Refill"),
    ("B07TZZ3TBG",  "Best Quilt Easy Press 1 Gallon Treatment"),
    # Stain Remover
    ("B0021JD2S0",  "Grandmas Secret Spot Remover"),
    # Party & Novelty
    ("B0099DS8SK",  "Party Candles Birthday Boy"),
    ("B000R4Q1ES",  "Beistle Red Metallic Streamer"),
    ("B09KVLHSJ9",  "36in Happy Birthday Slice Cake Balloon"),
    ("B002W9CM30",  "Pastel Blue Plastic Forks 24ct"),
    ("B005V3LR44",  "Muncie Novelty Pink Ticket Roll 2000"),
    ("B00KXSJSC0",  "Asmodee Mille Bornes Card Game"),
    # Home / Misc
    ("B000078CUB",  "VELCRO ONE-WRAP Roll Double Sided"),
    ("B019FWRKA6",  "Pre De Provence Moroccan Argan Oil 0.5oz"),
    ("B000SM3MRS",  "Cargill Water Softener Salt 40lb"),
    ("B000BPPHYI",  "North American Rock Salt Ice Melter 50lb"),
    ("B0024K22KU",  "RSVP Onion Goggles Fog Free"),
    ("B0014SQU1A",  "RSVP Endurance Onion Goggles Black"),
    ("B09M7RQ2DY",  "Pre de Provence Heritage Reed Diffuser"),
    ("B01LYQ24MN",  "Bucky Millet Hulls Pillow Refill 1lb"),
    ("B01M1B98XA",  "Bucky Buckwheat Hulls Pillow Refill 1lb"),
    ("B0744QRZQZ",  "Design Import Apple Placemat"),
    ("B00C9WJKTY",  "DOG for DOG Hook-On Pail 2qt"),
    ("B002YM78VG",  "Diamond Emergency LED Flasher"),
    ("B08DP1CZ94",  "Hi-Shine Bowling Ball Refill 96oz"),
    ("B0032THIMO",  "Jim Dunlop 65 Lemon Oil Fretboard 1oz"),
    ("B00AZGJ924",  "Smiffys Bride to Be Sash"),
    ("B07NJ4MMMG",  "Smiffys Glitter Bride to Be Sash Gold Black"),
    ("B0CQMDZV15",  "Hot Wheels Monster Trucks Refueling Track"),
    ("B00000IZKX",  "The Original Slinky Metal 2.75in"),
    ("B0C4D47G7M",  "Movie Night Party Supply"),
    # Adult Lingerie / Hosiery / Costumes
    ("B004O8DYOS",  "Smiffys Feather Eyelashes"),
    ("B00AZGFX3S",  "Smiffys Large Feather Eyelashes Aqua Dots"),
    ("B00AZGD3EO",  "Smiffys Feather Eyelashes Plain"),
    ("B00A5JIDH8",  "Rene Rofe Fishnet Thigh Highs Black"),
    ("B000HPYHGBA", "Elegant Moments Sheer Thigh High Stockings"),
    ("B000J3RT1Q",  "Leg Avenue Cuban Heel Backseam Stockings"),
    ("B000ZYSMAG",  "Leg Avenue Trim Bow Thigh Highs White"),
    ("B09R9JMDLS",  "Leg Avenue Dark Alternative Fishnet Tights"),
    ("B0CNV7P775",  "Leg Avenue Dark Alternative Fishnet Tights Plus"),
    ("B0BZ212SGY",  "Leg Avenue Fence Fishnet Tights Rainbow"),
    ("B01JQY57KS",  "2pc Cut Out Hiphugger Set Stockings"),
    ("B019M2P0YC",  "Rene Rofe 2pc Caged Chemise G-String Set"),
    ("B01E8O7XN0",  "Pink Lipstick 3pc Bra Garter G-String Set"),
    ("B00T9R483A",  "Pink Lipstick Juicebox Seamless Bodysuit"),
    ("B0094VPSY4",  "Rene Rofe Crotchless Lace Thong"),
    ("B01DNYZHY8",  "Mens Gage Low Rise Zip Thong"),
    ("B07KG2R1M5",  "Leg Avenue Adult Sized Costume One Size"),
    ("B082DS556P",  "Leg Avenue Costume Neon Yellow One Size"),
    ("B07N1JSXDX",  "Leg Avenue Costume Multi Small"),
    ("B0859P4VZH",  "Fever Lola Wig White"),
    ("B06X99RK2N",  "Fever Rainbow Long Wavy Wig"),
    ("B06WW585D7",  "Smiffys Fever Nicole Wig Silver Blonde"),
    ("B07NHVLHD2",  "Smiffys Bride Headband Women White"),
    ("B00AZGI6K0",  "Smiffys Bride Tiara with Veil"),
    ("B001D953H2",  "Little Genie Miss Bachelorette Sash"),
    ("B01DNZ00O4",  "Envy Tuxedo Cuffs Collar 3pc LXL"),
    ("B01DNZ00JE",  "Envy Tuxedo Cuffs Collar 3pc ML"),
    ("B00AZGJ924",  "Smiffys Bride to Be Sash Plain"),
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
        print("Rules Library sheet not found — run main.py first.")
        return

    records = ws.get_all_records()
    existing_asins = set()
    for r in records:
        if str(r.get("Rule Type", "")).strip().lower() == "asin_override":
            existing_asins.add(str(r.get("Value", "")).strip().upper())

    print(f"Found {len(existing_asins)} existing ASIN overrides in sheet.")

    rows_to_add = []
    skipped = []
    for asin, note in NR_OVERRIDES:
        if asin.upper() in existing_asins:
            skipped.append(asin)
        else:
            rows_to_add.append([
                "asin_override",
                asin.upper(),
                "Non-Returnable",
                "High",
                f"Non-Returnable confirmed via 2026-04-02 scraping — {note}",
                "VirVentures",
                TODAY,
                "Yes",
            ])

    if skipped:
        print(f"Skipped {len(skipped)} duplicates.")

    if not rows_to_add:
        print("Nothing to add — all overrides already exist.")
        return

    ws.append_rows(rows_to_add, value_input_option="USER_ENTERED")
    time.sleep(1)

    print(f"\nAdded {len(rows_to_add)} Non-Returnable overrides.")
    print("Re-run main.py --skip-keepa to apply.")

if __name__ == "__main__":
    main()
