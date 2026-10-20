"""Retailer classification used by the released model; unknown names remain explicit."""
import re
import pandas as pd

def normalize_text(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower()) if pd.notna(value) else ""


def classify_retailer(value):
    """Fascia scenarios are explicit proxies; they are not a legal control finding."""
    s = normalize_text(value)
    rules = [
        ("Tesco", "major", ["tesco"]), ("Sainsburys", "major", ["sainsbury"]),
        ("Asda", "major", ["asda"]), ("Morrisons", "major", ["morrison", "mccoll"]),
        ("Waitrose", "major", ["waitrose"]), ("Marks and Spencer", "discounter", ["marksandspencer", "marksspencer", "mands", "msfood", "mssimply"]),
        ("Aldi", "discounter", ["aldi"]), ("Lidl", "discounter", ["lidl"]),
        ("Co-op unresolved society", "major", ["coop", "cooperative"]),
        ("Spar", "symbol", ["spar"]), ("Nisa", "symbol", ["nisa"]),
        ("Londis", "symbol", ["londis"]), ("Premier", "symbol", ["premier"]),
        ("Budgens", "symbol", ["budgens"]), ("Costcutter", "symbol", ["costcutter"]),
        ("One Stop", "symbol", ["onestop"]), ("Best One", "symbol", ["bestone"]),
        ("Mace", "symbol", ["mace"]), ("Iceland", "specialist", ["iceland", "foodwarehouse"]),
        ("Farmfoods", "specialist", ["farmfoods"]), ("Heron", "specialist", ["heronfoods"]),
        ("Cook", "specialist", ["cookshop", "cookfrozen"]), ("Costco", "specialist", ["costco"]),
        ("Planet Organic", "specialist", ["planetorganic"]),
    ]
    for fascia, kind, tokens in rules:
        if any(t in s for t in tokens):
            return fascia, kind
    if s == "cook":
        return "Cook", "specialist"
    if s == "ms":
        return "Marks and Spencer", "discounter"
    return "Independent / unclassified", "independent"

def classify_for_cma(row):
    """Return public-rule classes; do not relabel specialist chains independent."""
    combined = " ".join(str(row.get(k, "")) for k in ["brand_raw", "fascia_raw", "name", "fascia"])
    s = normalize_text(combined)
    extra = [("Whole Foods", "major", "wholefoods"), ("Dunnes", "major", "dunnes"),
             ("Family Shopper", "symbol", "familyshopper"), ("Central PH Retail", "symbol", "centralconvenience"),
             ("Key Store", "symbol", "keystore"), ("Key Shop", "symbol", "keyshop"),
             ("Centra", "symbol", "centra"), ("CK Supermarkets", "symbol", "cksupermarket")]
    for fascia, kind, token in extra:
        if token in s:
            return fascia, kind
    return row.fascia, row.retailer_type


def classify_source_observation(observation):
    """Use brand, then fascia, then store name; retain an explicit unknown class."""
    for column in ['brand_raw', 'fascia_raw', 'name']:
        category = classify_retailer(observation.get(column, ''))
        if category[1] != 'independent':
            return category
    return 'Independent / unclassified', 'independent'
