import os
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Column order expected in the sheet (0-based)
COL = {
    "ASIN": 0,
    "Marketplace": 1,
    "Brand / Supplier": 2,
    "Product Name / Title": 3,
    "Category": 4,
    "Current Returnable Status": 5,
    "Returnable?": 6,
    "Confidence": 7,
    "Classification Reason": 8,
    "Last Checked": 9,
}

COL_WIDTHS = {
    0: 120,   # ASIN
    1: 90,    # Marketplace
    2: 130,   # Brand / Supplier
    3: 240,   # Product Name / Title
    4: 210,   # Category
    5: 155,   # Current Returnable Status
    6: 95,    # Returnable?
    7: 100,   # Confidence
    8: 310,   # Classification Reason
    9: 140,   # Last Checked
}


def _get_client():
    key_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    creds = Credentials.from_service_account_file(key_file, scopes=SCOPES)
    return gspread.authorize(creds)


def rgb(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
    return {"red": r, "green": g, "blue": b}


def _cond_rule(ws_id, col_idx, num_rows, text, bg_hex, fg_hex, index):
    return {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{
                    "sheetId": ws_id,
                    "startRowIndex": 1, "endRowIndex": num_rows + 200,
                    "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1,
                }],
                "booleanRule": {
                    "condition": {
                        "type": "TEXT_EQ",
                        "values": [{"userEnteredValue": text}]
                    },
                    "format": {
                        "backgroundColor": rgb(bg_hex),
                        "textFormat": {
                            "foregroundColor": rgb(fg_hex),
                            "bold": True,
                        }
                    }
                }
            },
            "index": index
        }
    }


def format_sheet():
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    client = _get_client()
    spreadsheet = client.open_by_key(sheet_id)
    sheet = spreadsheet.sheet1
    ws_id = sheet.id

    data = sheet.get_all_values()
    num_rows = max(len(data), 2)
    headers = data[0] if data else []
    num_cols = len(headers)

    # Build column index map dynamically from actual sheet headers
    COL_ACTUAL = {name: idx for idx, name in enumerate(headers)}

    reqs = []

    # ── 1. Freeze header row ─────────────────────────────────────────────────
    reqs.append({
        "updateSheetProperties": {
            "properties": {
                "sheetId": ws_id,
                "gridProperties": {"frozenRowCount": 1}
            },
            "fields": "gridProperties.frozenRowCount"
        }
    })

    # ── 2. Header row styling ────────────────────────────────────────────────
    reqs.append({
        "repeatCell": {
            "range": {
                "sheetId": ws_id,
                "startRowIndex": 0, "endRowIndex": 1,
                "startColumnIndex": 0, "endColumnIndex": num_cols,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": rgb("#1B3A5C"),
                    "textFormat": {
                        "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                        "bold": True,
                        "fontSize": 10,
                        "fontFamily": "Arial",
                    },
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                    "wrapStrategy": "CLIP",
                    "padding": {"top": 6, "bottom": 6, "left": 8, "right": 8},
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy,padding)",
        }
    })

    # ── 3. Header row height ─────────────────────────────────────────────────
    reqs.append({
        "updateDimensionProperties": {
            "range": {"sheetId": ws_id, "dimension": "ROWS",
                      "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 36},
            "fields": "pixelSize",
        }
    })

    # ── 4. Data rows — base font ─────────────────────────────────────────────
    reqs.append({
        "repeatCell": {
            "range": {
                "sheetId": ws_id,
                "startRowIndex": 1, "endRowIndex": num_rows + 200,
                "startColumnIndex": 0, "endColumnIndex": num_cols,
            },
            "cell": {
                "userEnteredFormat": {
                    "textFormat": {"fontSize": 10, "fontFamily": "Arial"},
                    "verticalAlignment": "MIDDLE",
                    "wrapStrategy": "CLIP",
                    "padding": {"top": 4, "bottom": 4, "left": 8, "right": 8},
                }
            },
            "fields": "userEnteredFormat(textFormat,verticalAlignment,wrapStrategy,padding)",
        }
    })

    # ── 5. ASIN column — monospace ───────────────────────────────────────────
    reqs.append({
        "repeatCell": {
            "range": {
                "sheetId": ws_id,
                "startRowIndex": 1, "endRowIndex": num_rows + 200,
                "startColumnIndex": 0, "endColumnIndex": 1,
            },
            "cell": {
                "userEnteredFormat": {
                    "textFormat": {"fontFamily": "Courier New", "fontSize": 9},
                    "horizontalAlignment": "LEFT",
                }
            },
            "fields": "userEnteredFormat(textFormat,horizontalAlignment)",
        }
    })

    # ── 6. Center-align: Marketplace, Returnable?, Confidence, Last Checked ──
    center_cols = ["Marketplace", "Returnable?", "Confidence", "Last Checked"]
    for col_idx in [COL_ACTUAL[c] for c in center_cols if c in COL_ACTUAL]:
        if col_idx < num_cols:
            reqs.append({
                "repeatCell": {
                    "range": {
                        "sheetId": ws_id,
                        "startRowIndex": 1, "endRowIndex": num_rows + 200,
                        "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "horizontalAlignment": "CENTER",
                        }
                    },
                    "fields": "userEnteredFormat.horizontalAlignment",
                }
            })

    # ── 7. Alternating row colors ────────────────────────────────────────────
    for i in range(1, num_rows):
        bg = rgb("#F8FAFC") if i % 2 == 0 else rgb("#FFFFFF")
        reqs.append({
            "repeatCell": {
                "range": {
                    "sheetId": ws_id,
                    "startRowIndex": i, "endRowIndex": i + 1,
                    "startColumnIndex": 0, "endColumnIndex": num_cols,
                },
                "cell": {"userEnteredFormat": {"backgroundColor": bg}},
                "fields": "userEnteredFormat.backgroundColor",
            }
        })

    # ── 8. Column widths (by name so order doesn't matter) ───────────────────
    col_width_by_name = {
        "ASIN": 120, "Marketplace": 90, "Brand / Supplier": 130,
        "Product Name / Title": 240, "Category": 210,
        "Current Returnable Status": 155, "Returnable?": 95,
        "Confidence": 100, "Classification Reason": 310, "Last Checked": 140,
    }
    COL_WIDTHS = {COL_ACTUAL[name]: w for name, w in col_width_by_name.items()
                  if name in COL_ACTUAL}
    for col_idx, width in COL_WIDTHS.items():
        if col_idx < num_cols:
            reqs.append({
                "updateDimensionProperties": {
                    "range": {"sheetId": ws_id, "dimension": "COLUMNS",
                              "startIndex": col_idx, "endIndex": col_idx + 1},
                    "properties": {"pixelSize": width},
                    "fields": "pixelSize",
                }
            })

    # ── 9. Conditional formatting: Current Returnable Status ─────────────────
    rule_idx = 0
    if "Current Returnable Status" in COL_ACTUAL:
        for text, bg, fg in [
            ("Returnable",     "#E6F4EA", "#137333"),
            ("Non-Returnable", "#FCE8E6", "#C5221F"),
            ("Unknown",        "#FEF7E0", "#92400E"),
        ]:
            reqs.append(_cond_rule(ws_id, COL_ACTUAL["Current Returnable Status"],
                                   num_rows, text, bg, fg, rule_idx))
            rule_idx += 1

    # ── 10. Conditional formatting: Returnable? (Yes/No/Review) ──────────────
    if "Returnable?" in COL_ACTUAL:
        for text, bg, fg in [
            ("Yes",    "#E6F4EA", "#137333"),
            ("No",     "#FCE8E6", "#C5221F"),
            ("Review", "#FEF7E0", "#92400E"),
        ]:
            reqs.append(_cond_rule(ws_id, COL_ACTUAL["Returnable?"],
                                   num_rows, text, bg, fg, rule_idx))
            rule_idx += 1

    # ── 11. Conditional formatting: Confidence ────────────────────────────────
    if "Confidence" in COL_ACTUAL:
        for text, bg, fg in [
            ("High",   "#E8F5E9", "#2E7D32"),
            ("Medium", "#FFF8E1", "#F57F17"),
            ("Low",    "#FBE9E7", "#BF360C"),
        ]:
            reqs.append(_cond_rule(ws_id, COL_ACTUAL["Confidence"],
                                   num_rows, text, bg, fg, rule_idx))
            rule_idx += 1

    # ── 12. Borders ──────────────────────────────────────────────────────────
    reqs.append({
        "updateBorders": {
            "range": {
                "sheetId": ws_id,
                "startRowIndex": 0, "endRowIndex": num_rows,
                "startColumnIndex": 0, "endColumnIndex": num_cols,
            },
            "bottom": {"style": "SOLID", "color": rgb("#D1D5DB")},
            "innerHorizontal": {"style": "SOLID", "color": rgb("#E5E7EB")},
            "innerVertical": {"style": "SOLID", "color": rgb("#E5E7EB")},
        }
    })

    spreadsheet.batch_update({"requests": reqs})
    print("Sheet formatted successfully.")
