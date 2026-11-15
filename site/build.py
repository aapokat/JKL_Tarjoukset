#!/usr/bin/env python3
"""Merge the fetched offers and the browser snapshots into the published page.

Writes public/offers.json (compact data the page and the email alerts read), public/index.html
(the page, loads offers.json) and preview.html (one self-contained file with the data inside).

The same offer is often sold at the same price in many stores (K-Ruoka chain offers, S-kaupat
cooperative offers), so rows with the same product, price and terms are merged into one card
that lists every store it is valid in.
"""
import json
import os, re, sys
from datetime import datetime, timezone
from pathlib import Path

from catalog import CAT_ORDER, categorize

HERE = Path(__file__).parent
DATA = HERE / "data"
PUBLIC = HERE.parent / "public"

CHAINS = [("K-Citymarket", "K-Citymarket"), ("K-Supermarket", "K-Supermarket"), ("K-Market", "K-Market"),
          ("Prisma", "Prisma"), ("S-market", "S-market"), ("Sale", "S-market"),
          ("Lidl", "Lidl"), ("Tokmanni", "Tokmanni"), ("Kärkkäinen", "Kärkkäinen"), ("Rusta", "Rusta")]
CHAIN_ORDER = ["K-Citymarket", "K-Supermarket", "K-Market", "Prisma", "S-market", "Lidl", "Tokmanni", "Kärkkäinen", "Rusta", "Muut"]
NATIONAL = {"Lidl": "Lidlin viikkotarjoukset, samat kaikissa Lidleissä.",
            "Tokmanni": "Tokmannin viikkotarjoukset, samat kaikissa Tokmanneissa.",
            "Rusta": "Rustan kampanja- ja Club Rusta -tarjoukset, joita myydään tavarataloissa (Jyväskylässä Keljo ja Palokka).",
            "Kärkkäinen": "Kampanjatuotteet, joita on saatavilla Jyväskylän myymälästä."}


def chain_of(store):
    return next((c for prefix, c in CHAINS if store.startswith(prefix)), "Muut")


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def load(name):
    path = DATA / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


STORES = json.loads((DATA / "stores.json").read_text(encoding="utf-8"))
MIN_PCT = STORES.get("minDiscountPercent", 0)


def main():
    fetched = load("offers.json") or {"fetched": "", "offers": [], "status": {}}
    rows = list(fetched["offers"])
    sources = {"Haku": fetched.get("fetched", "")}
    have = {r[0] for r in rows}
    for name, label in (("k-ruoka-snapshot.json", "K-Ruoka"), ("s-kaupat-snapshot.json", "S-kaupat")):
        snap = load(name)
        if not snap:
            continue
        extra = [r for r in snap["offers"] if r[0] not in have]  # a fetched store always wins over a snapshot
        if extra:
            rows += extra
            sources[label] = snap.get("collected", "")

    # Fill in missing brands from the brands other stores report ("Fazer Marianne ..." -> Fazer).
    brands = sorted({norm(r[12]) for r in rows if len(r) > 12 and len(norm(r[12])) >= 3 and re.search(r"\w\w", r[12])}, key=len, reverse=True)
    lower = [(b.lower() + " ", b) for b in brands]

    groups, order = {}, []
    for r in rows:
        r = list(r) + [""] * (13 - len(r))
        store, raw_cat, name, price, unit, was, pct, note, valid, url, img, pid, brand = r[:13]
        name = norm(name)
        if not name or not (price or pct):
            continue
        if store == "Prisma.fi":
            continue  # online store, not a store offer
        if not pct and price and was and was > price:
            pct = round((1 - price / was) * 100)
        if (pct or 0) < MIN_PCT:
            continue  # smaller discounts (or no known normal price) are left out on purpose
        bundle = re.search(r"(\d+) kpl =", note or "")
        if bundle and int(bundle.group(1)) >= 10:
            continue  # "21 kpl = 4,00 €" is a store's typing error in its till system, not a real offer
        brand = norm(brand) if re.search(r"\w\w", brand or "") else ""
        if re.search(r"\d+ kpl =", note or "") and re.fullmatch(r"\d+ \w+", unit or ""):
            unit = ""  # "3 ps" next to "3 kpl = 1,00 €" says the same thing twice
        if not brand:
            low = name.lower() + " "
            brand = next((b for lb, b in lower if low.startswith(lb)), "")
        cat = categorize(raw_cat, name)
        key = (str(pid) or name.lower(), price, was, note)
        g = groups.get(key)
        if not g:
            g = groups[key] = {"stores": [], "cat": cat, "name": name, "price": price, "unit": unit, "was": was, "pct": pct,
                               "note": note, "valid": valid, "url": url, "img": img, "pid": str(pid), "brand": brand}
            order.append(key)
        if store not in g["stores"]:
            g["stores"].append(store)
        for f, v in (("img", img), ("url", url), ("valid", valid), ("unit", unit)):
            if not g[f] and v:
                g[f] = v

    # Cheapest store for products that are on offer at different prices in different stores.
    def each(g):
        m = re.match(r"(\d+) kpl =", g["note"] or "")
        return (g["price"] or 0) / (int(m.group(1)) if m else 1)
    by_pid = {}
    for k in order:
        g = groups[k]
        if g["price"] and g["pid"] and not g["pid"].startswith("k"):
            by_pid.setdefault(g["pid"], []).append(g)
    for lst in by_pid.values():
        if len(lst) > 1:
            best = min(each(g) for g in lst)
            for g in lst:
                g["best"] = 1 if abs(each(g) - best) < 0.005 else 0
                g["bestPrice"] = round(best, 2)

    store_names = sorted({s for k in order for s in groups[k]["stores"]}, key=lambda s: (CHAIN_ORDER.index(chain_of(s)), s))
    sidx = {s: i for i, s in enumerate(store_names)}
    counts = {s: 0 for s in store_names}
    out_rows = []
    for k in order:
        g = groups[k]
        for s in g["stores"]:
            counts[s] += 1
        out_rows.append([sorted(sidx[s] for s in g["stores"]), CAT_ORDER.index(g["cat"]), g["name"], g["price"], g["unit"],
                         g["was"], g["pct"], g["note"], g["valid"], g["url"], g["img"], g["pid"], g["brand"],
                         g.get("best"), g.get("bestPrice")])
    payload = {
        "built": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": sources,
        "status": fetched.get("status", {}),
        "stores": [{"name": s, "chain": chain_of(s), "count": counts[s], "info": NATIONAL.get(s, "")} for s in store_names],
        "cats": CAT_ORDER,
        "minPct": MIN_PCT,
        "fields": ["stores", "cat", "name", "price", "unit", "was", "pct", "note", "valid", "url", "img", "pid", "brand", "best", "bestPrice"],
        "offers": out_rows,
    }
    PUBLIC.mkdir(exist_ok=True)
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    (PUBLIC / "offers.json").write_text(blob, encoding="utf-8")
    config = load("alerts-config.json") or {"api": "/api/vahti"}
    if "ALERT_API" in os.environ:  # GitHub Pages has no backend: the workflow passes the alert service URL, or ""
        config["api"] = os.environ["ALERT_API"].strip()
    template = (HERE / "template.html").read_text(encoding="utf-8").replace("__CONFIG__", json.dumps(config))
    (PUBLIC / "index.html").write_text(template.replace("__DATA__", "null"), encoding="utf-8")
    (HERE.parent / "preview.html").write_text(template.replace("__DATA__", blob.replace("</", "<\\/")), encoding="utf-8")
    print(len(rows), "rows ->", len(out_rows), "cards,", len(store_names), "stores,", len(blob) // 1024, "KB")


if __name__ == "__main__":
    main()
