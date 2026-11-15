#!/usr/bin/env python3
"""Fetch this week's offers for Jyväskylä stores into data/offers.json.

Standard library only, so it runs anywhere (for example GitHub Actions).
Sources a plain script can read:
  - S-kaupat     Prismas and S-markets in Jyväskylä (api.s-kaupat.fi, store-specific prices)
  - Lidl         national weekly offers (lidl.fi search API)
  - Kärkkäinen   campaign products in stock in the Jyväskylä store
  - Tokmanni     national weekly offers (tokmanni.fi)
  - Rusta        current campaigns and Club Rusta offers sold in the stores (rusta.com)
K-Ruoka (K-Citymarkets, K-Supermarkets) sits behind Cloudflare, so it is collected in a real
browser with collectors/k-ruoka.js into data/k-ruoka-snapshot.json.

Each row: [store, category, name, price, unit, normal_price, discount_percent, note, valid, url,
           image, product_id, brand]. Category is the store's own; build.py maps it to common groups.
Run one source only: fetch_offers.py skaupat (names: skaupat, lidl, karkkainen, tokmanni, rusta).
Offers below minDiscountPercent (stores.json) are dropped later, in build.py.
"""
import html as htmllib, json, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36 tarjoushaku/2.0"
PAUSE = 0.7  # seconds between requests, to stay gentle on the stores
OUT = Path(__file__).parent / "data"
STORES = json.loads((OUT / "stores.json").read_text(encoding="utf-8"))


def get(url, headers=None):
    h = {"User-Agent": UA, "Accept-Language": "fi-FI,fi;q=0.9", "Accept": "*/*"}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=45) as f:
                body = f.read().decode("utf-8", "replace")
            time.sleep(PAUSE)
            return body
        except Exception:  # network hiccup: wait and retry
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))


def offer(store, cat, name, price, unit="", was=None, pct=None, note="", valid="", url="", img="", pid="", brand=""):
    price = round(price, 2) if price else None
    was = round(was, 2) if was and price and was > price else None
    if pct is None and price and was:
        pct = round((1 - price / was) * 100)
    if pct is not None and pct <= 0:
        pct = None
    return [store, cat or "", re.sub(r"\s+", " ", name).strip(), price, unit or "", was, pct, note or "", valid or "",
            url or "", img or "", str(pid or ""), brand or ""]


def dmy(iso):
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)", iso or "")
    return "%d.%d." % (int(m.group(3)), int(m.group(2))) if m else ""


def eur(x):
    return ("%.2f" % x).replace(".", ",")


# ---------------------------------------------------------------- S-kaupat (Prisma, S-market)
SK_API = "https://api.s-kaupat.fi/"
SK_UNITS = {"KG": "kg", "KGM": "kg", "LTR": "l", "L": "l", "KPL": "kpl", "PCE": "kpl", "MTR": "m", "M": "m"}


def sk_page(store_id, start):
    variables = {"facets": [], "filters": [{"key": "labels", "value": ["DISCOUNTED"]}], "fetchSponsoredContent": False,
                 "limit": 100, "from": start, "queryString": "", "storeId": store_id, "useRandomId": False}
    ext = {"persistedQuery": {"version": 1, "sha256Hash": STORES["skaupatQueryHash"]}}
    url = SK_API + "?operationName=RemoteFilteredProducts&variables=%s&extensions=%s" % (
        urllib.parse.quote(json.dumps(variables, separators=(",", ":"))), urllib.parse.quote(json.dumps(ext, separators=(",", ":"))))
    d = json.loads(get(url, {"Origin": "https://www.s-kaupat.fi", "Referer": "https://www.s-kaupat.fi/",
                             "Accept": "application/json", "x-client-name": "skaupat-web"}))
    if d.get("errors"):
        raise RuntimeError(d["errors"][0].get("message", "api error"))
    return d["data"]["store"]["products"]


def sk_row(store, item):
    p = item.get("product") or {}
    pr = (p.get("store") or {}).get("pricing") or p.get("pricing") or {}
    price = pr.get("campaignPrice") or pr.get("currentPrice") or p.get("price")
    if not price:
        return None
    labels = [l.get("labelText", "") for l in item.get("labels") or []]
    was = pr.get("regularPrice")
    if not was or was <= price:
        was = pr.get("lowest30DayPrice")
    unit, note = "", ""
    if pr.get("comparisonPrice") and pr.get("comparisonUnit"):
        unit = "%s €/%s" % (eur(pr["comparisonPrice"]), SK_UNITS.get(pr["comparisonUnit"], pr["comparisonUnit"].lower()))
    for lab in labels:
        m = re.search(r"(\d+)\s*kpl\s*=\s*(\d+(?:,\d+)?)\s*€", lab)
        if m:  # multi-buy: show the price of the whole bundle
            n, total = int(m.group(1)), float(m.group(2).replace(",", "."))
            was, price, note = round((pr.get("regularPrice") or price) * n, 2), total, "%d kpl = %s €" % (n, eur(total))
        elif lab and lab != "Kampanja":
            note = lab
    path = " > ".join(h.get("name", "") for h in p.get("hierarchyPath") or [])
    img = ((((p.get("productDetails") or {}).get("productImages") or {}).get("mainImage") or {}).get("urlTemplate") or "")
    img = img.replace("{MODIFIERS}", "w300h300@_q75").replace("{EXTENSION}", "webp")
    valid = pr.get("campaignPriceValidUntil")
    return offer(store, path, p.get("name", ""), price, unit, was, None, note,
                 ("Voimassa %s asti" % dmy(valid)) if valid else "",
                 "https://www.s-kaupat.fi/tuote/%s/%s" % (p.get("slug", ""), p.get("ean", "")),
                 img, p.get("ean"), p.get("brandName") or "")


def skaupat():
    out = []
    for store_id, store in STORES["skaupat"].items():
        start, total = 0, 1
        while start < total and start < 3000:
            prods = sk_page(store_id, start)
            total = prods.get("total") or 0
            items = prods.get("productListItems") or []
            for it in items:
                r = sk_row(store, it)
                if r:
                    out.append(r)
            if not items:
                break
            start += len(items)
    return out


# ---------------------------------------------------------------- Lidl
LIDL_CATS = {
    10068374: "Ruoka ja juoma", 10068166: "Keittiö ja kodinhoito", 10068222: "Remontointi ja puutarha",
    10068226: "Urheilu ja vapaa-aika", 10068371: "Koti ja sisustus", 10068373: "Muoti ja asusteet",
    10068225: "Vauvat, lapset ja lelut",
}


def lidl():
    out, seen = [], set()
    for cid, label in LIDL_CATS.items():
        offset = 0
        while True:
            d = json.loads(get("https://www.lidl.fi/q/api/search?offset=%d&fetchsize=100&locale=fi_FI"
                               "&assortment=FI&version=2.1.0&category.id=%d" % (offset, cid)))
            items = d.get("items", [])
            for it in items:
                g = (it.get("gridbox") or {}).get("data") or {}
                pid = g.get("itemId")
                if not g.get("fullTitle") or pid in seen:
                    continue
                p = g.get("price") or {}
                plus = (g.get("lidlPlus") or [None])[0]
                price, was, pct, note = p.get("price"), p.get("oldPrice") or (p.get("discount") or {}).get("deletedPrice"), None, ""
                unit = (p.get("packaging") or {}).get("text", "")
                if plus and (plus.get("price") or {}).get("price"):
                    pp = plus["price"]
                    was = was or price
                    price = pp["price"]
                    unit = (pp.get("packaging") or {}).get("text", "") or unit
                    note = "Lidl Plus -sovelluksella"
                    m = re.search(r"(\d+)\s*%", plus.get("highlightText") or "")
                    pct = int(m.group(1)) if m else None
                badges = [b.get("text", "") for b in ((g.get("stockAvailability") or {}).get("badgeInfo") or {}).get("badges", [])]
                valid = next((b for b in badges if re.search(r"\d+\.\d+\.", b)), "")
                if not price or not (valid or was or note):
                    continue  # permanent assortment, not an offer
                path = ((g.get("keyfacts") or {}).get("wonCategoryPrimary") or "").split("/")
                raw = path[2] if len(path) > 2 and path[1].startswith("Ruoka") else (path[1] if len(path) > 1 else label)
                if cid != 10068374:
                    raw = label
                seen.add(pid)
                out.append(offer("Lidl", raw, g["fullTitle"].lstrip("- "), price, unit, was, pct, note,
                                 valid.replace(" - ", "–"), "https://www.lidl.fi" + (g.get("canonicalUrl") or ""),
                                 g.get("image") or "", "lidl%s" % pid, (g.get("brand") or {}).get("name") or ""))
            offset += len(items)
            if not items or offset >= d.get("numFound", 0):
                break
    return out


# ---------------------------------------------------------------- Kärkkäinen
KARK = "https://www.karkkainen.com/verkkokauppa"
KARK_CATS = {
    "ruoka-tarjoukset": "Ruoka", "pukeutuminen-tarjoukset-54840001": "Pukeutuminen", "tyokalu-tarjoukset": "Työkalu ja työvaate (työkalu)",
    "koti-ja-sisustus-tarjoukset": "Koti ja sisustus", "era-ja-retkeily-tarjoukset": "Erä ja retkeily",
    "elektroniikka-ja-pelaaminen-tarjoukset": "Elektroniikka ja pelaaminen", "autoilu-ja-caravan-tarjoukset-32379001--11": "Autoilu",
    "lelut-ja-lastentarvikkeet-tarjoukset-32379009--11": "Lelut ja lastentarvikkeet", "piha-ja-puutarha-tarjoukset-32379012--11": "Piha ja puutarha",
    "urheilu-tarjoukset-32379016--11": "Urheilu", "koneet-tarjoukset": "Koneet", "kasityot-taiteet-ja-harrasteet-tarjoukset": "Käsityöt ja harrasteet",
    "lemmikit-tarjoukset": "Lemmikit", "remontointi-tarjoukset-32379013--11": "Remontointi",
}


def karkkainen():
    out, seen = [], set()
    facet = urllib.parse.quote("attributes.Saatavuus myymälästä:" + STORES["karkkainenStore"])
    for slug, label in KARK_CATS.items():
        offset, total = 0, 1
        while offset < total and offset < 1500:
            page = get("%s/%s?facet=%s&offset=%d" % (KARK, slug, facet, offset))
            m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
            if not m:
                break
            fb = json.loads(m.group(1))["props"]["pageProps"].get("fallback", {})
            key = next((k for k in fb if "Product_LISTING" in k), None)
            if not key:
                break
            listing = fb[key]
            total = listing.get("total", 0)
            contents = listing.get("contents", [])
            for p in contents:
                prices = {x.get("usage"): x.get("value") for x in p.get("price") or []}
                now, was = prices.get("Offer"), prices.get("Display")
                if p.get("id") in seen or not now or not was or was <= now:
                    continue
                seen.add(p.get("id"))
                img = re.sub(r"h_\d+", "h_300", re.sub(r"w_\d+", "w_300", p.get("thumbnail") or ""))
                brand = p.get("manufacturer") or ""
                for a in p.get("attributes") or []:
                    if a.get("identifier") == "Tuotemerkki" and a.get("values"):
                        brand = a["values"][0].get("value") or brand
                out.append(offer("Kärkkäinen", label, p.get("name", ""), now, "", was, None, "",
                                 "Saatavilla Jyväskylän myymälästä", KARK + ((p.get("seo") or {}).get("href") or ""),
                                 img, "kark%s" % p.get("partNumber", p.get("id")), brand))
            if not contents:
                break
            offset += len(contents)
    return out


# ---------------------------------------------------------------- Tokmanni
TOK_ITEM = re.compile(r'<li class="item product product-item"(.*?)</li>\s*(?=<li class="item product product-item"|</ol>)', re.S)


def tok_attr(block, rx):
    m = re.search(rx, block, re.S)
    return htmllib.unescape(m.group(1)).strip() if m else ""


def tokmanni():
    out, seen = [], set()
    for page in range(1, 200):
        body = get("https://www.tokmanni.fi/viikkotarjoukset?p=%d&product_list_limit=40" % page)
        blocks = TOK_ITEM.findall(body)
        fresh = 0
        for b in blocks:
            ean = tok_attr(b, r'data-cnstrc-item-id="([^"]+)"')
            if not ean or ean in seen:
                continue
            seen.add(ean)
            fresh += 1
            name = tok_attr(b, r'data-cnstrc-item-name="([^"]+)"')
            final = tok_attr(b, r'data-price-amount="([\d.]+)"\s+data-price-type="finalPrice"')
            old = tok_attr(b, r'data-price-amount="([\d.]+)"\s+data-price-type="oldPrice"')
            label = re.sub(r"\s+", " ", tok_attr(b, r'class="campaign-label[^"]*">(.*?)</div>'))
            price, was = float(final or 0) or None, float(old or 0) or None
            if not price:
                continue
            note = "Tokmanni-klubihinta" if "campaign-label-loyalty" in b else ""
            bundle = re.match(r"(\d+)\s*kpl\s*/\s*(\d+(?:,\d+)?)", label)
            if bundle:  # "3 kpl / 4,00 €": show the bundle price like the other stores do
                n, total = int(bundle.group(1)), float(bundle.group(2).replace(",", "."))
                was, price, note = round(price * n, 2), total, "%d kpl = %s €" % (n, eur(total))
            if not was or was <= price:
                continue  # no normal price: no way to tell how big the discount is
            out.append(offer("Tokmanni", "", name, price, "", was, None, note, "Tokmannin viikkotarjous",
                             tok_attr(b, r'<a href="([^"]+)"'), tok_attr(b, r'<img src="([^"]+)"').replace("h_328,w_328", "h_300,w_300"),
                             ean, tok_attr(b, r"<span class=.brand-name.>(.*?)</span>")))
        if not fresh:
            break
    return out


# ---------------------------------------------------------------- Rusta
def rusta_page(page):
    i = page.find("window.CURRENT_PAGE = ")
    if i < 0:
        return None
    return json.JSONDecoder().raw_decode(page, i + len("window.CURRENT_PAGE = "))[0]


def rusta():
    out, seen, base = [], set(), STORES["rustaCampaignUrl"]
    page, total, per = 1, 1, 24
    while page <= -(-total // per) and page <= 80:
        cp = rusta_page(get(base + ("?page=%d" % page if page > 1 else "")))
        if not cp:
            break
        total, per = cp.get("totalProductCount") or 0, cp.get("countPerPage") or 24
        for p in cp.get("products") or []:
            code = p.get("code")
            if not code or code in seen or not p.get("buyableInStore"):
                continue  # online-only products are not store offers
            seen.add(code)
            pr = p.get("price") or {}
            member = p.get("memberPrice") and (pr.get("memberCurrent") or {}).get("inclVat")
            price = member or (pr.get("current") or {}).get("inclVat")
            was = (pr.get("memberOriginal") or {}).get("inclVat") if member else None
            was = max(was or 0, (pr.get("original") or {}).get("inclVat") or 0) or None
            name = " ".join(x for x in (p.get("displayName"), p.get("subTitle")) if x)
            img = ((p.get("images") or [{}])[0] or {}).get("url") or ""
            out.append(offer("Rusta", p.get("category") or "", name, price, "", was, None, "Club Rusta -hinta" if member else "",
                             "Saatavilla Rustan tavarataloista", "https://www.rusta.com" + (p.get("url") or ""),
                             ("https://www.rusta.com/cdn-cgi/image/width=300,height=300,fit=pad,background=white,format=auto" + img) if img else "",
                             "rusta%s" % code, p.get("brand") or ""))
        page += 1
    return out


SOURCES = {"skaupat": skaupat, "lidl": lidl, "karkkainen": karkkainen, "tokmanni": tokmanni, "rusta": rusta}
# Which store names each source writes, so a failed source can fall back to its previous rows.
SOURCE_STORES = {"skaupat": set(STORES["skaupat"].values()), "lidl": {"Lidl"}, "karkkainen": {"Kärkkäinen"},
                 "tokmanni": {"Tokmanni"}, "rusta": {"Rusta"}}


def main(only=None):
    OUT.mkdir(exist_ok=True)
    previous, prev_status = [], {}
    try:  # keep last run's offers for a source that fails this time
        old = json.loads((OUT / "offers.json").read_text(encoding="utf-8"))
        previous, prev_status = old["offers"], old.get("status", {})
    except Exception:
        pass
    offers, status = [], {}
    for name, fn in SOURCES.items():
        mine = [o for o in previous if o[0] in SOURCE_STORES[name]]
        if only and name not in only:
            offers += mine
            status[name] = prev_status.get(name, len(mine))
            continue
        try:
            got = fn()
            if not got:
                raise RuntimeError("no offers found")
            status[name] = len(got)
            offers += got
        except Exception as e:  # one store failing must not lose the others
            status[name] = "virhe: %s (käytetään edellistä hakua, %d tarjousta)" % (e, len(mine))
            offers += mine
            print("FAILED", name, e, file=sys.stderr)
    payload = {"fetched": datetime.now(timezone.utc).isoformat(timespec="seconds"), "status": status, "offers": offers}
    (OUT / "offers.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
