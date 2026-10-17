"""Fetch commercial products and their inactive ingredients from openFDA.

The result is cached in data/openfda_products.json so the demo runs offline.
Refresh it with:  python -m compounder.seed.openfda
"""
import json
import re
import time
import urllib.parse
import urllib.error
import urllib.request
from pathlib import Path

from compounder.seed.knowledge import DRUGS, EXCIPIENTS

SNAPSHOT = Path(__file__).resolve().parents[2] / "data" / "openfda_products.json"
API = "https://api.fda.gov/drug/label.json"

# Ordered: first match wins
FORM_PATTERNS = [
    ("oral_suspension", r"oral suspension|for suspension"),
    ("oral_solution", r"oral solution|elixir|syrup"),
    ("capsule", r"capsule"),
    ("tablet", r"tablet"),
    ("transdermal_gel", r"\bgel\b"),
    ("topical_cream", r"\bcream\b"),
    ("topical_ointment", r"ointment"),
]


def _first(r: dict, key: str) -> str:
    v = r.get(key) or [""]
    return v[0] if isinstance(v, list) else str(v)


def detect_form(r: dict) -> str | None:
    # Try the most specific text first: the package label, then the rest.
    for key in ("package_label_principal_display_panel", "dosage_forms_and_strengths", "description"):
        text = _first(r, key)[:800].lower()
        for form, pat in FORM_PATTERNS:
            if re.search(pat, text):
                return form
    return None


def detect_excipients(r: dict) -> list[str]:
    """Match label text against excipient aliases from the knowledge base."""
    # Only look at ingredient lists, not prose like "soluble in ethanol".
    desc = _first(r, "description")
    m = re.search(r"inactive ingredients?(.*)", desc, re.I | re.S)
    text = " ".join([
        _first(r, "spl_product_data_elements"),
        _first(r, "inactive_ingredient"),
        m.group(1)[:1500] if m else "",
    ]).upper().replace("&AMP;", "&")
    found = []
    for ex_id, _name, _parents, aliases in EXCIPIENTS:
        if any(a in text for a in aliases):
            found.append(ex_id)
    return found


# Repackager labels crowd out the rare liquid and topical products, so those
# get their own searches.
EXTRA_FILTERS = [
    '(package_label_principal_display_panel:"oral suspension" OR package_label_principal_display_panel:"oral solution")',
    'openfda.route:"TOPICAL"',
]


def _search(search: str, limit: int) -> list[dict]:
    q = urllib.parse.urlencode({"search": search, "limit": limit})
    try:
        with urllib.request.urlopen(f"{API}?{q}", timeout=30) as resp:
            return json.load(resp).get("results", [])
    except urllib.error.HTTPError as e:
        if e.code == 404:  # openFDA returns 404 when nothing matches
            return []
        raise


def fetch_drug(generic: str, limit: int = 100) -> list[dict]:
    base = f'openfda.generic_name:"{generic}"'
    results = _search(base, limit)
    for extra in EXTRA_FILTERS:
        results += _search(f"{base} AND {extra}", 50)
    products, seen = [], set()
    for r in results:
        o = r.get("openfda", {})
        # Skip combination products (e.g. amlodipine + benazepril)
        generics = o.get("generic_name", [""])
        if len(generics) != 1 or " AND " in generics[0].upper() or "," in generics[0]:
            continue
        brand = (o.get("brand_name") or ["?"])[0]
        mfr = (o.get("manufacturer_name") or ["?"])[0]
        form = detect_form(r)
        key = (brand.lower(), mfr.lower(), form)
        if key in seen or form is None:
            continue
        seen.add(key)
        products.append({
            "id": r.get("set_id") or r.get("id"),
            "brand": brand,
            "manufacturer": mfr,
            "form": form,
            "route": (o.get("route") or [""])[0].lower(),
            "rxcui": o.get("rxcui", [])[:5],
            "excipients": detect_excipients(r),
            "source": f"openFDA drug label set_id {r.get('set_id')}",
        })
    return products


def refresh() -> dict:
    out = {}
    for drug_id, name, _cls, _aliases in DRUGS:
        try:
            out[drug_id] = fetch_drug(name.lower())
            print(f"{name}: {len(out[drug_id])} products")
        except Exception as e:  # network errors, 404 when nothing matches
            print(f"{name}: skipped ({e})")
            out[drug_id] = []
        time.sleep(0.3)  # be polite to the public API
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(out, indent=1))
    print(f"Saved {SNAPSHOT}")
    return out


def load_snapshot() -> dict:
    if not SNAPSHOT.exists():
        return {}
    return json.loads(SNAPSHOT.read_text())


if __name__ == "__main__":
    refresh()
