import json
from pathlib import Path

KEEPA_EXPORT_FILE = Path("keepa_export_lookup.json")


def _load_keepa_export() -> dict:
    if KEEPA_EXPORT_FILE.exists():
        try:
            with open(KEEPA_EXPORT_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


class ReturnabilityClassifier:

    def __init__(self, rules=None):
        """
        rules: dict from rules_manager.load_rules()
        If None, falls back to empty rules (Unknown for everything).
        """
        self.rules = rules or {
            "category_non_ret": [],
            "category_ret": [],
            "title_non_ret": [],
            "asin_overrides": {},
            "brand_overrides": {},
        }
        self.keepa_export = _load_keepa_export()

    def classify(self, asin, category_path, title, keepa_data=None, brand=None, description=None):
        """
        Returns dict:
            status      : 'Non-Returnable' | 'Returnable' | 'Unknown'
            confidence  : 'High' | 'Medium' | 'Low'
            reason      : Human-readable explanation
        """
        category_lower = (category_path or "").lower()
        title_lower    = (title or "").lower()
        desc_lower     = (description or "").lower()
        brand_lower    = (brand or "").lower().strip()
        asin_upper     = (asin or "").upper().strip()

        # ── Priority 0: ASIN-level override (highest priority) ────────────────
        if asin_upper in self.rules["asin_overrides"]:
            classification, confidence, notes = self.rules["asin_overrides"][asin_upper]
            return self._result(classification, confidence,
                                f"Manual override: {notes}")

        # ── Priority 1: Brand-level override ──────────────────────────────────
        if brand_lower and brand_lower in self.rules["brand_overrides"]:
            classification, confidence, notes = self.rules["brand_overrides"][brand_lower]
            return self._result(classification, confidence,
                                f"Brand rule ({brand}): {notes}")

        # ── Priority 2: Category keyword — Non-Returnable ─────────────────────
        for keyword, confidence, notes in self.rules["category_non_ret"]:
            if keyword in category_lower:
                return self._result("Non-Returnable", confidence,
                                    f"Category rule: '{keyword}' — {notes}")

        # ── Priority 3: Title keyword — Non-Returnable ────────────────────────
        for keyword, confidence, notes in self.rules["title_non_ret"]:
            if keyword in title_lower:
                return self._result("Non-Returnable", confidence,
                                    f"Title rule: '{keyword}' — {notes}")

        # ── Priority 4: Keepa export lookup (Is HazMat, heat sensitive, adult) ──
        export_data = self.keepa_export.get(asin_upper)
        if export_data:
            result = self._check_keepa_export(export_data)
            if result:
                return result

        # ── Priority 5: Description keyword — Non-Returnable ─────────────────
        if desc_lower:
            result = self._check_description(desc_lower)
            if result:
                return result

        # ── Priority 6: Keepa API product attributes ───────────────────────────
        if keepa_data:
            result = self._check_keepa(keepa_data)
            if result:
                return result

        # ── Priority 6: Category keyword — Returnable ─────────────────────────
        for keyword, confidence, notes in self.rules["category_ret"]:
            if keyword in category_lower:
                return self._result("Returnable", confidence,
                                    f"Category rule: '{keyword}' — {notes}")

        # ── Default ───────────────────────────────────────────────────────────
        return self._result("Unknown", "Low",
                            "No matching rule found — manual review or add rule to Rules Library")

    def _check_keepa_export(self, data: dict):
        """Check Keepa export signals — Is HazMat, heat sensitive, adult product."""

        # HazMat flag — direct non-returnable signal
        if data.get("Is HazMat", "").lower() == "yes":
            hazmat_detail = data.get("Hazardous Materials", "")
            reason = "Keepa export: Is HazMat = yes"
            if hazmat_detail:
                # Extract shipping name if available
                if "Proper Shipping Name:" in hazmat_detail:
                    name = hazmat_detail.split("Proper Shipping Name:")[-1].split(";")[0].strip()[:60]
                    reason = "Keepa HazMat: %s" % name
                elif "UN" in hazmat_detail:
                    reason = "Keepa HazMat: %s" % hazmat_detail[:60]
            return self._result("Non-Returnable", "High", reason)

        # Heat sensitive — shipping restriction
        if data.get("Is heat sensitive", "").lower() == "yes":
            return self._result("Non-Returnable", "High",
                                "Keepa export: heat sensitive product — shipping restriction")

        # Adult product
        if data.get("Adult Product", "").lower() == "yes":
            return self._result("Non-Returnable", "High",
                                "Keepa export: adult product category")

        # Batteries included — lithium battery hazmat check
        batteries = data.get("Batteries Included", "").lower()
        if batteries == "yes":
            material = data.get("Material", "").lower()
            if "lithium" in material:
                return self._result("Non-Returnable", "High",
                                    "Keepa export: lithium batteries included")

        return None

    def _check_description(self, desc_lower: str):
        """
        Scan product description for high-confidence non-returnable signals.
        Only called when category + title rules don't give a clear answer.
        Uses conservative keywords to avoid false positives from long text.
        """
        # Regulatory / transport signals — very high confidence
        regulatory = [
            ("flammable",           "Description: flammable material"),
            ("aerosol",             "Description: aerosol product"),
            ("hazardous material",  "Description: hazardous material warning"),
            ("hazardous substance", "Description: hazardous substance"),
            ("dangerous good",      "Description: dangerous goods classification"),
            ("pressurized",         "Description: pressurized container"),
            ("compressed gas",      "Description: compressed gas"),
            ("non-returnable",      "Description: explicitly states non-returnable"),
            ("not returnable",      "Description: explicitly states not returnable"),
            ("cannot be returned",  "Description: explicitly states cannot be returned"),
            ("do not return",       "Description: explicitly states do not return"),
            ("un1197",              "Description: UN1197 flammable liquid classification"),
            ("un1950",              "Description: UN1950 aerosol classification"),
            ("un1993",              "Description: UN1993 flammable liquid classification"),
            ("dot regulated",       "Description: DOT regulated hazmat"),
            ("iata regulated",      "Description: IATA regulated hazmat"),
        ]

        # Consumable / hygiene signals — high confidence
        consumable = [
            ("contains alcohol",    "Description: alcohol-based product"),
            ("ethyl alcohol",       "Description: ethyl alcohol content"),
            ("isopropyl alcohol",   "Description: isopropyl alcohol content"),
            ("single use",          "Description: single-use product"),
            ("single-use",          "Description: single-use product"),
            ("sterile",             "Description: sterile/hygiene product"),
            ("once opened",         "Description: consumable — cannot verify once opened"),
        ]

        for keyword, reason in regulatory:
            if keyword in desc_lower:
                return self._result("Non-Returnable", "High", reason)

        for keyword, reason in consumable:
            if keyword in desc_lower:
                return self._result("Non-Returnable", "Medium", reason)

        return None

    def _check_keepa(self, data):
        # 1. Digital product (software/ebook)
        if data.get("type", 0) in {1, 2}:
            return self._result("Non-Returnable", "High",
                                "Keepa: digital product (type=ebook/software)")

        # 2. Explicit hazmat classification
        hazmat_code = data.get("hazardousMaterialType", 0)
        if hazmat_code and int(hazmat_code) > 0:
            label = data.get("hazmatLabel") or f"code {hazmat_code}"
            return self._result("Non-Returnable", "High",
                                f"Keepa hazmat: {label}")

        # 3. Lithium battery
        if data.get("hasLithium") or "lithium" in data.get("batteryType", ""):
            return self._result("Non-Returnable", "High",
                                "Keepa: lithium battery product")

        # 4. Product group indicates consumable
        if data.get("productGroupFlag"):
            group = data.get("productGroup", "")
            return self._result("Non-Returnable", "High",
                                f"Keepa productGroup: '{group}' — consumable/regulated")

        # 5. Binding indicates consumable
        if data.get("bindingFlag"):
            binding = data.get("binding", "")
            return self._result("Non-Returnable", "High",
                                f"Keepa binding: '{binding}'")

        return None

    @staticmethod
    def _result(status, confidence, reason):
        return {"status": status, "confidence": confidence, "reason": reason}
