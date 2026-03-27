"""
Keepa API client with local disk cache.
Cached ASINs are never re-fetched — zero token cost on repeat runs.
"""

import os
import json
import time
import requests
from pathlib import Path

KEEPA_API_URL = "https://api.keepa.com/product"
CACHE_FILE = Path("keepa_cache.json")
DOMAIN_MAP = {"US": 1, "CA": 6, "UK": 2, "DE": 3}
BATCH_SIZE = 20
LOW_TOKEN_THRESHOLD = 50

# Keepa product type codes — digital = non-returnable
DIGITAL_TYPES = {1, 2}   # 1=downloadable software, 2=ebook

# Keepa hazardousMaterialType codes
HAZMAT_LABELS = {
    1: "Flammable liquid",
    2: "Toxic / Poison",
    3: "Corrosive",
    4: "Oxidizer",
    5: "Explosive",
    6: "Compressed gas",
    7: "Radioactive",
    8: "Other hazmat",
    9: "Lithium battery",
}

# productGroup values that indicate consumable / non-returnable products
NON_RETURNABLE_PRODUCT_GROUPS = [
    "grocery", "food", "food and beverage",
    "health and beauty", "health & beauty",
    "pet food", "pet supplies",
    "vitamin", "supplement",
    "medicine", "pharmaceutical", "drug",
    "personal care", "beauty",
    "lawn and garden", "garden",        # fertilizers, pesticides
    "chemical",
]

# Keepa binding values indicating non-returnable
NON_RETURNABLE_BINDINGS = [
    "grocery", "health and beauty",
]


class KeepaClient:

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.cache = self._load_cache()

    # ── Cache ─────────────────────────────────────────────────────────────────

    def _load_cache(self) -> dict:
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        with open(CACHE_FILE, "w") as f:
            json.dump(self.cache, f, indent=2)

    # ── Public ────────────────────────────────────────────────────────────────

    def get_products(self, asins: list, marketplace: str = "US") -> dict:
        """
        Returns dict of {asin: extracted_signals}.
        Cached ASINs never hit the API.
        """
        domain = DOMAIN_MAP.get(marketplace.upper(), 1)
        results = {}
        to_fetch = []

        for asin in asins:
            if asin in self.cache:
                results[asin] = self.cache[asin]
            else:
                to_fetch.append(asin)

        cached_count = len(asins) - len(to_fetch)
        if cached_count > 0:
            print(f"      {cached_count} ASINs loaded from cache (0 tokens used)")

        if not to_fetch:
            return results

        batches = [to_fetch[i:i+BATCH_SIZE]
                   for i in range(0, len(to_fetch), BATCH_SIZE)]

        for i, batch in enumerate(batches, 1):
            print(f"      Keepa batch {i}/{len(batches)} ({len(batch)} ASINs)...")
            fetched = self._fetch_batch(batch, domain)
            results.update(fetched)
            for asin, signals in fetched.items():
                self.cache[asin] = signals
            self._save_cache()

        return results

    # ── Internal ──────────────────────────────────────────────────────────────

    def _fetch_batch(self, asins: list, domain: int) -> dict:
        params = {
            "key":  self.api_key,
            "domain": domain,
            "asin": ",".join(asins),
            "history": 0,              # skip price history  — saves tokens
            "offers": 0,               # skip seller offers  — saves tokens
            "stats": 0,                # skip statistics     — saves tokens
            "rating": 0,               # skip review history — saves tokens
            "buyBoxSellerIdHistory": 0,
        }

        for attempt in range(3):
            try:
                r = requests.get(KEEPA_API_URL, params=params, timeout=30)
                data = r.json()

                tokens_left = data.get("tokensLeft", 0)
                refill_ms = data.get("refillIn", 60000)
                if tokens_left < LOW_TOKEN_THRESHOLD:
                    wait = min(refill_ms / 1000, 60)
                    print(f"      Tokens low ({tokens_left}). Pausing {wait:.0f}s...")
                    time.sleep(wait)

                result = {}
                for p in data.get("products") or []:
                    asin = p.get("asin")
                    if asin:
                        result[asin] = self._extract_signals(p)
                return result

            except Exception as e:
                if attempt == 2:
                    print(f"      Keepa fetch failed: {e}")
                    return {}
                time.sleep(5)

        return {}

    def _extract_signals(self, product: dict) -> dict:
        """
        Pull all fields relevant to return policy from a raw Keepa product.
        Keeps cache lean — only stores signals, not the full product blob.
        """
        hazmat_code = 0
        try:
            hazmat_code = int(product.get("hazardousMaterialType") or 0)
        except (ValueError, TypeError):
            pass

        battery_type = (product.get("batteryType") or "").lower()
        has_lithium = "lithium" in battery_type

        product_group = (product.get("productGroup") or "").lower()
        binding = (product.get("binding") or "").lower()
        product_type_str = (product.get("productType") or "").lower()

        # Derive non-returnable signal from product group
        product_group_flag = any(
            g in product_group for g in NON_RETURNABLE_PRODUCT_GROUPS
        )
        binding_flag = any(
            b in binding for b in NON_RETURNABLE_BINDINGS
        )

        return {
            # Digital type detection
            "type": product.get("type", 0),

            # Hazmat
            "hazardousMaterialType": hazmat_code,
            "hazmatLabel": HAZMAT_LABELS.get(hazmat_code, ""),

            # Product classification signals
            "productGroup": product_group,
            "productGroupFlag": product_group_flag,
            "binding": binding,
            "bindingFlag": binding_flag,
            "productType": product_type_str,

            # Battery (lithium = non-returnable in many cases)
            "batteriesRequired": bool(product.get("batteriesRequired")),
            "batteryType": battery_type,
            "hasLithium": has_lithium,

            # Category context
            "rootCategory": product.get("rootCategory", 0),
            "manufacturer": product.get("manufacturer") or "",
        }
