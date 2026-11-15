// S-kaupat offers collector, a browser fallback for fetch_offers.py's "skaupat" source.
// fetch_offers.py normally reads api.s-kaupat.fi directly. If that ever stops working from a script,
// open https://www.s-kaupat.fi, paste this file into the developer console and save the downloaded
// file as site/data/s-kaupat-snapshot.json. Same row format as fetch_offers.py.
(async () => {
  const STORES = window.S_STORES || {
    "725799735": "Prisma Seppälä", "590771861": "Prisma Keljo", "631792405": "Prisma Palokka",
    "542868831": "S-market Kuokkala", "638099390": "S-market Savela", "519887772": "S-market Palokka",
    "726235364": "S-market Tourula", "708271234": "S-market Vaajala"
  };
  const HASH = window.S_HASH || "85a4eed2f0a1e3269ac49b94276ca952922568369d85ddd5dcee34481e4c0f91";
  const UNITS = {KG: "kg", KGM: "kg", LTR: "l", L: "l", KPL: "kpl", PCE: "kpl", MTR: "m", M: "m"};
  const eur = x => x.toFixed(2).replace(".", ",");
  const dmy = s => { const m = /(\d{4})-(\d\d)-(\d\d)/.exec(s || ""); return m ? +m[3] + "." + +m[2] + "." : ""; };
  async function page(storeId, from) {
    const v = {facets: [], filters: [{key: "labels", value: ["DISCOUNTED"]}], fetchSponsoredContent: false, limit: 100, from,
               queryString: "", storeId, useRandomId: false};
    const u = "https://api.s-kaupat.fi/?operationName=RemoteFilteredProducts&variables=" + encodeURIComponent(JSON.stringify(v)) +
              "&extensions=" + encodeURIComponent(JSON.stringify({persistedQuery: {version: 1, sha256Hash: HASH}}));
    const j = await (await fetch(u)).json();
    if (j.errors) throw new Error(j.errors[0].message);
    return j.data.store.products;
  }
  function row(store, item) {
    const p = item.product || {}, pr = (p.store && p.store.pricing) || p.pricing || {};
    let price = pr.campaignPrice || pr.currentPrice || p.price;
    if (!price) return null;
    let was = pr.regularPrice && pr.regularPrice > price ? pr.regularPrice : pr.lowest30DayPrice;
    let unit = "", note = "";
    if (pr.comparisonPrice && pr.comparisonUnit) unit = eur(pr.comparisonPrice) + " €/" + (UNITS[pr.comparisonUnit] || pr.comparisonUnit.toLowerCase());
    for (const l of item.labels || []) {
      const t = l.labelText || "", m = /(\d+)\s*kpl\s*=\s*(\d+(?:,\d+)?)\s*€/.exec(t);
      if (m) { const n = +m[1], total = +m[2].replace(",", "."); was = Math.round((pr.regularPrice || price) * n * 100) / 100; price = total; note = n + " kpl = " + eur(total) + " €"; }
      else if (t && t !== "Kampanja") note = t;
    }
    if (!was || was <= price) was = null;
    const pct = was ? Math.round((1 - price / was) * 100) : null;
    const path = (p.hierarchyPath || []).map(h => h.name).join(" > ");
    const tpl = ((((p.productDetails || {}).productImages || {}).mainImage) || {}).urlTemplate || "";
    const valid = pr.campaignPriceValidUntil;
    return [store, path, (p.name || "").trim(), Math.round(price * 100) / 100, unit, was, pct || null, note,
            valid ? "Voimassa " + dmy(valid) + " asti" : "", "https://www.s-kaupat.fi/tuote/" + p.slug + "/" + p.ean,
            tpl.replace("{MODIFIERS}", "w300h300@_q75").replace("{EXTENSION}", "webp"), p.ean || "", p.brandName || ""];
  }
  const rows = [], counts = {};
  for (const [id, store] of Object.entries(STORES)) {
    let from = 0, total = 1;
    while (from < total && from < 3000) {
      const prods = await page(id, from);
      total = prods.total || 0;
      const items = prods.productListItems || [];
      for (const it of items) { const r = row(store, it); if (r) rows.push(r); }
      if (!items.length) break;
      from += items.length;
    }
    counts[store] = total;
    window.S_PROGRESS = counts;
  }
  const out = {source: "s-kaupat", collected: new Date().toISOString(), counts, offers: rows};
  window.S_RESULT = out;
  if (!window.S_NO_DOWNLOAD) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(out)], {type: "application/json"}));
    a.download = "s-kaupat-snapshot.json";
    a.click();
  }
  return counts;
})().catch(e => { window.S_ERROR = String((e && e.message) || e); console.error(e); });
