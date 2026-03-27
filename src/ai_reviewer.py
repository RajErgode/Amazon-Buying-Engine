"""
AI Review Engine — Claude Haiku via Anthropic API.

Token minimisation strategy:
  1. Only called for items that survive all rule layers as "Unknown"
  2. All N unknowns sent in ONE batched prompt (not N separate calls)
  3. AI result stored immediately as ASIN override → never called again for same ASIN
  4. If AI spots a clear pattern → auto-generates a rule → future similar items cost 0 tokens

Activation: add ANTHROPIC_API_KEY to .env or Streamlit Cloud secrets.
Until then, every method returns gracefully with is_available() == False.
"""

from __future__ import annotations
import json
import os
import textwrap

ANTHROPIC_AVAILABLE = False
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    pass


def is_available() -> bool:
    """True only when the Anthropic package is installed AND an API key is set."""
    if not ANTHROPIC_AVAILABLE:
        return False
    key = _get_api_key()
    return bool(key)


def _get_api_key() -> str:
    try:
        import streamlit as st
        key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if key:
            return str(key)
    except Exception:
        pass
    return os.getenv("ANTHROPIC_API_KEY", "")


_SYSTEM = textwrap.dedent("""
    You are an Amazon return-policy expert for a professional reseller.
    Your job is to classify products as Returnable, Non-Returnable, or Unknown
    based on Amazon's standard return policies.

    Key Non-Returnable signals:
    - Hazmat / flammable / aerosol / pressurised / corrosive
    - Consumables: food, supplements, vitamins, pet treats, medicine
    - Hygiene / once-opened: bandages, earplugs, personal care
    - Perishables: live plants, fresh food
    - Customised / personalised / engraved / made-to-order
    - Digital: software, e-books, gift cards
    - Amazon-exempt: handmade, sexual wellness, certified pre-owned watches
    - Lithium batteries, hazardous chemicals, pesticides / herbicides

    Returnable unless otherwise flagged:
    - Electronics, tools, household items, clothing, toys, books, office supplies

    Always base your answer on the product's actual nature — not just the category label.
    When uncertain, respond Unknown with a note explaining what additional info is needed.
""").strip()


def analyse_batch(items: list[dict]) -> list[dict]:
    """
    Classify a batch of Unknown items in a single API call.

    Parameters
    ----------
    items : list of dicts with keys: asin, title, brand, category, description

    Returns
    -------
    list of dicts: asin, status, confidence, reason, suggested_rule (optional)
    """
    if not is_available():
        return []

    if not items:
        return []

    # Build the prompt — one line per item
    lines = []
    for i, item in enumerate(items, 1):
        lines.append(
            f"{i}. ASIN: {item.get('asin','?')} | "
            f"Title: {item.get('title','')[:80]} | "
            f"Brand: {item.get('brand','')[:30]} | "
            f"Category: {item.get('category','')[:60]} | "
            f"Description excerpt: {item.get('description','')[:120]}"
        )

    user_msg = (
        "Classify each product below. "
        "Respond ONLY with a JSON array — one object per product — with these exact keys:\n"
        '  "asin", "status" (Returnable|Non-Returnable|Unknown), '
        '"confidence" (High|Medium|Low), "reason" (≤15 words), '
        '"suggested_rule" (optional — if a clear category/title keyword would catch '
        'future similar items, provide {"type":"category_keyword"|"title_keyword","value":"..."} else null)\n\n'
        + "\n".join(lines)
    )

    try:
        client = anthropic.Anthropic(api_key=_get_api_key())
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = response.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        results = json.loads(raw)
        return results if isinstance(results, list) else []

    except Exception as e:
        return [{"asin": item.get("asin"), "status": "Unknown",
                 "confidence": "Low", "reason": f"AI error: {e}",
                 "suggested_rule": None}
                for item in items]


def estimated_cost(n_items: int) -> str:
    """Return a human-readable cost estimate for analysing n_items."""
    # Claude Haiku: $0.80/MTok input, $4/MTok output (as of 2025)
    # ~250 tokens per item input + ~60 tokens output average
    input_tokens  = n_items * 250
    output_tokens = n_items * 60
    cost_usd = (input_tokens / 1_000_000 * 0.80) + (output_tokens / 1_000_000 * 4.0)
    if cost_usd < 0.01:
        return f"< $0.01"
    return f"~${cost_usd:.3f}"
