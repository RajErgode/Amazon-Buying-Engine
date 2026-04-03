"""
scrape_return_policy.py
------------------------
Light Amazon return-policy scraper for Unknown and low/medium-confidence items.
Processes up to MAX_PER_RUN ASINs per execution with rate limiting.

Usage:
    python scrape_return_policy.py           # process up to 100 items
    python scrape_return_policy.py --dry-run # show what would be scraped, no writes
    python scrape_return_policy.py --limit 20

Signals detected:
    "can be returned" / "eligible for return"  -> Returnable
    "non-returnable" / "cannot be returned"     -> Non-Returnable
    No signal found                             -> skipped (logged to scrape_skipped.csv)
"""

import argparse
import csv
import html as html_module
import os
import random
import time
from datetime import datetime

import gspread
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
MAX_PER_RUN   = 100
DELAY_MIN     = 2.5   # seconds between requests
DELAY_MAX     = 5.0
TIMEOUT       = 15
SKIPPED_LOG   = "scrape_skipped.csv"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

STATUS_COL     = "Current Returnable Status"
CONFIDENCE_COL = "Confidence"
REASON_COL     = "Classification Reason"
ASIN_COL       = "ASIN"
TITLE_COL      = "Product Name / Title"
DATE_COL       = "Last Checked"

# Rotating user agents to reduce bot detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

# ── Signals ───────────────────────────────────────────────────────────────────
RETURNABLE_SIGNALS = [
    "this item can be returned",
    "eligible for return, refund or replacement",
    "eligible for return",
    "can be returned in its original condition",
    "30-day refund",
    "full refund or replacement within",
    "free returns",
]

NR_SIGNALS = [
    "this item is non-returnable",
    "item is non-returnable",
    "non-returnable",
    "not eligible for return",
    "cannot be returned",
    "this item cannot be returned",
    "ineligible for return",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _gspread_client():
    key_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    creds = Credentials.from_service_account_file(key_file, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_id).sheet1


def _make_session() -> requests.Session:
    """
    Create a requests Session seeded with Amazon homepage cookies.
    This ensures Amazon serves the full product page (with return policy)
    rather than a stripped bot-detection page.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    })
    try:
        session.get("https://www.amazon.com/", timeout=TIMEOUT)
        time.sleep(1)
    except Exception:
        pass
    return session


def _fetch_page(session: requests.Session, asin: str) -> str | None:
    """
    Fetch one Amazon product page using the shared session.
    Returns combined visible-text + HTML-decoded raw HTML, or None on failure.
    """
    url = f"https://www.amazon.com/dp/{asin}"
    try:
        r = session.get(url, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "lxml")
        visible_text = soup.get_text(" ", strip=True)
        if "captcha" in visible_text.lower() or "enter the characters" in visible_text.lower():
            return None
        decoded_html = html_module.unescape(r.text)
        return visible_text + " " + decoded_html
    except Exception:
        return None


def _classify_from_text(text: str) -> tuple[str | None, str]:
    """
    Returns (classification, matched_signal) or (None, '') if no signal found.
    Checks NR signals first (more specific), then Returnable.
    """
    lower = text.lower()
    for sig in NR_SIGNALS:
        if sig in lower:
            # Find surrounding snippet for reason
            idx = lower.find(sig)
            snippet = text[max(0, idx - 10):idx + 80].replace("\n", " ").strip()
            return "Non-Returnable", f'Amazon page: "{snippet}"'
    for sig in RETURNABLE_SIGNALS:
        if sig in lower:
            idx = lower.find(sig)
            snippet = text[max(0, idx - 10):idx + 80].replace("\n", " ").strip()
            return "Returnable", f'Amazon page: "{snippet}"'
    return None, ""


# ── Main ──────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False, limit: int = MAX_PER_RUN):
    print("=" * 60)
    print("  VirVentures - Amazon Return Policy Scraper")
    print("=" * 60)

    # 1. Load sheet
    print("\n[1/4] Reading Google Sheet ...")
    ws = _gspread_client()
    records = ws.get_all_records()
    headers = ws.row_values(1)

    col_idx = {h: i + 1 for i, h in enumerate(headers)}   # 1-based

    # 2. Pick targets: Unknown first, then low/medium confidence
    targets = []
    for row_num, r in enumerate(records, start=2):
        status = str(r.get(STATUS_COL, "")).strip()
        conf   = str(r.get(CONFIDENCE_COL, "")).strip().lower()
        asin   = str(r.get(ASIN_COL, "")).strip()
        title  = str(r.get(TITLE_COL, "")).strip()

        if not asin or len(asin) != 10:
            continue

        priority = None
        if status == "Unknown":
            priority = 1
        elif conf in ("low",) and status in ("Returnable", "Non-Returnable"):
            priority = 2
        elif conf in ("medium",) and status in ("Returnable", "Non-Returnable"):
            priority = 3

        if priority:
            targets.append((priority, row_num, asin, title, status, conf))

    targets.sort(key=lambda x: x[0])
    targets = targets[:limit]

    print(f"      {len(targets)} items selected for scraping")
    if not targets:
        print("      Nothing to scrape — all items are classified with High confidence.")
        return

    # 3. Scrape
    print(f"\n[2/4] Scraping up to {len(targets)} Amazon product pages ...")
    if dry_run:
        print("      DRY RUN — no writes will be made\n")

    results   = []   # (row_num, asin, new_status, reason)
    skipped   = []   # (asin, title, reason)
    today     = datetime.now().strftime("%Y-%m-%d")

    print("      Seeding Amazon session (homepage visit) ...")
    session = _make_session()

    for i, (priority, row_num, asin, title, old_status, old_conf) in enumerate(targets, 1):
        prio_label = {1: "Unknown", 2: "Low conf", 3: "Med conf"}.get(priority, "?")
        print(f"  [{i:3d}/{len(targets)}] [{prio_label}] {asin} | {title[:50]}")

        page_text = _fetch_page(session, asin)

        if page_text is None:
            print(f"           -> CAPTCHA or network error — skipped")
            skipped.append((asin, title, "CAPTCHA or network error"))
        else:
            classification, reason = _classify_from_text(page_text)
            if classification:
                changed = classification != old_status
                marker = " *CHANGED*" if changed else ""
                print(f"           -> {classification}{marker}")
                results.append((row_num, asin, classification, reason))
            else:
                print(f"           -> No signal found (JS-rendered) — skipped")
                skipped.append((asin, title, "No return policy signal in static HTML"))

        # Polite delay
        if i < len(targets):
            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            time.sleep(delay)

    # 4. Write results back to sheet
    print(f"\n[3/4] Writing {len(results)} results to Google Sheet ...")
    if dry_run:
        print("      DRY RUN — skipping write")
    elif results:
        updates = []
        for row_num, asin, classification, reason in results:
            if STATUS_COL in col_idx:
                updates.append({
                    "range": gspread.utils.rowcol_to_a1(row_num, col_idx[STATUS_COL]),
                    "values": [[classification]],
                })
            # Also update Returnable?, Confidence, Reason, Date
            extra = {
                "Returnable?":           "Yes" if classification == "Returnable" else "No",
                "Confidence":            "High",
                "Classification Reason": reason,
                "Last Checked":          today,
            }
            for col_name, val in extra.items():
                if col_name in col_idx:
                    updates.append({
                        "range": gspread.utils.rowcol_to_a1(row_num, col_idx[col_name]),
                        "values": [[val]],
                    })

        # Batch write in chunks
        BATCH = 50
        for i in range(0, len(updates), BATCH):
            ws.batch_update(updates[i:i+BATCH], value_input_option="USER_ENTERED")
            if i + BATCH < len(updates):
                time.sleep(2)

        print(f"      Written {len(results)} rows")

    # 5. Log skipped items
    if skipped:
        print(f"\n[4/4] Logging {len(skipped)} skipped items to {SKIPPED_LOG} ...")
        file_exists = os.path.exists(SKIPPED_LOG)
        with open(SKIPPED_LOG, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not file_exists:
                w.writerow(["Date", "ASIN", "Title", "Reason"])
            for asin, title, reason in skipped:
                w.writerow([today, asin, title, reason])

    # Summary
    returnable_count = sum(1 for _, _, c, _ in results if c == "Returnable")
    nr_count         = sum(1 for _, _, c, _ in results if c == "Non-Returnable")
    print()
    print("=" * 60)
    print("  Scrape Complete")
    print("=" * 60)
    print(f"  Classified  : {len(results)} items")
    print(f"    Returnable    : {returnable_count}")
    print(f"    Non-Returnable: {nr_count}")
    print(f"  Skipped     : {len(skipped)} items (see {SKIPPED_LOG})")
    print(f"  Dry run     : {'Yes' if dry_run else 'No'}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Amazon return policy for low-confidence items")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to sheet")
    parser.add_argument("--limit",   type=int, default=MAX_PER_RUN, help=f"Max items to process (default {MAX_PER_RUN})")
    args = parser.parse_args()
    main(dry_run=args.dry_run, limit=args.limit)
