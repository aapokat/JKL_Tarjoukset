// K-Ruoka offers collector. K-Ruoka sits behind Cloudflare, so this runs inside a real browser:
// open https://www.k-ruoka.fi/kauppa/tarjoushaku, paste this file into the developer console
// (or let site/collect_browser.py run it with Playwright) and save the result as
// site/data/k-ruoka-snapshot.json. Rows use the same format as fetch_offers.py:
// [store, category, name, price, unit, normal_price, discount_percent, note, valid, url, image, product_id, brand]
(async () => {
  // Same list as data/stores.json ("kruoka"); collect_browser.py passes that file's list in window.K_STORES.
  const STORES = window.K_STORES || {"N150": "K-Citymarket Seppälä", "N110": "K-Citymarket Keljo", "N177": "K-Citymarket Palokka", "S337": "K-Supermarket Länsiväylä", "S255": "K-Supermarket Kotikenttä", "S605": "K-Supermarket Paraati", "S528": "K-Supermarket Lutakko", "S590": "K-Supermarket Vaajakoski", "K310": "K-Market Kymppi", "K147": "K-Market Äijälä", "L726": "K-Market Kekkolantie", "L308": "K-Market Schaumanin puistotie", "K202": "K-Market Kangas", "L256": "K-Market Kuokkalanpelto", "K263": "K-Market Kärpänkuja", "K136": "K-Market Kotiväylä", "L266": "K-Market Kypärämäki", "K188": "K-Market Torikeskus", "L104": "K-Market Ainola", "L362": "K-Market Mäyrämäki", "L516": "K-Market Tapionkatu", "K251": "K-Market Nisula", "L143": "K-Market Halssila", "L196": "K-Market Kangaslampi", "L649": "K-Market Lohikoski"};
  const build = ([...document.scripts].map(s => (s.src.match(/\/assets\/b-(\d+)\//) || [])[1]).find(Boolean)) || "";
  const headers = {"content-type": "application/json", "accept": "application/json", "X-K-Build-Number": build};
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  // K-Ruoka allows roughly 500 quick requests and then blocks for up to two hours (429 with a long Retry-After).
  // So: one store at a time, a pause between pages, and if the block comes anyway, the remaining stores are
  // skipped (they keep their previous offers) instead of waiting it out.
  let blocked = false;
  async function post(path, body) {
    for (let attempt = 0; attempt < 6; attempt++) {
      if (blocked) throw new Error("rate limited");
      let r = null;
      try { r = await fetch(path, {method: "POST", headers, body: JSON.stringify(body)}); } catch (e) { /* network hiccup */ }
      if (r && r.ok) return r.json();
      if (r && r.status === 409) throw new Error("K-Ruoka was updated, reload the page and run again");
      if (r && r.status === 429 && Number(r.headers.get("retry-after")) > 300) { blocked = true; throw new Error("rate limited"); }
      await sleep((r && r.status === 429 ? 30000 : 2000) * (attempt + 1));
    }
    throw new Error("request failed: " + path);
  }
  const IMG = "?w=300&h=300&fit=fill&fill-color=ffffff&q=60&auto=format";
  const dmy = iso => { const d = new Date(iso); return isNaN(d) ? "" : d.getDate() + "." + (d.getMonth() + 1) + "."; };
  const now = new Date().toISOString();
  const diet = {dietary: [], avoidable: [], isTargetingOffersAllowed: false};

  function row(store, o, catName) {
    const pr = o.pricing || {}, normal = o.normalPricing || {};
    const p = (o.product && o.product.product) || null;
    const name = ((o.localizedTitle || {}).finnish || (p && p.localizedName && p.localizedName.finnish) || "").trim();
    if (!name) return null;
    const unit = ((pr.unit || {}).fi || "").trim();
    const qty = Number((unit.match(/^(\d+)\s/) || [])[1]) || 1;
    const price = typeof pr.price === "number" ? pr.price : null;
    let was = typeof normal.price === "number" ? Math.round(normal.price * qty * 100) / 100 : null;
    let pct = (pr.discountPercentageRange || {}).min || null;
    if (price && was && was > price) pct = pct || Math.round((1 - price / was) * 100);
    if (!price || !was || was <= price) was = price ? null : was;
    if (!price && !pct) return null;
    const notes = [];
    if (pr.discountType === "PLUSSA") notes.push("Plussa-kortilla");
    if (qty > 1 && price) notes.push(qty + " kpl = " + price.toFixed(2).replace(".", ",") + " €");
    let valid = "";
    const ms = p && p.mobilescan && p.mobilescan.pricing;
    const disc = ms && (ms.discount || ms.batch);
    if (disc && disc.endDate) valid = "Voimassa " + dmy(disc.endDate) + " asti";
    if (disc && disc.reason === "OUTGOING_ITEMS") notes.push("Poistuva erä");
    if (disc && disc.amount >= 10) return null;   // "21 kpl = 4 €": a mistyped store campaign, not a real deal
    if (o.offerType === "store") notes.push("Vain tässä kaupassa");
    const cat = (p && p.category && p.category.tree && p.category.tree[0] && p.category.tree[0].localizedName.finnish) || catName;
    const slug = p && p.productAttributes && p.productAttributes.urlSlug;
    const img = (p && p.productAttributes && p.productAttributes.image && p.productAttributes.image.url) || o.image || "";
    return [store, cat, name, price, unit === "kpl" || qty > 1 ? "" : unit, was, pct, notes.join(", "), valid,
            slug ? "https://www.k-ruoka.fi/kauppa/tuote/" + slug : "",
            img ? img + IMG : "", p ? p.ean : "k" + (o.offerNameId || o.campaignId || o.id),
            (p && p.brand && p.brand.name) || ""];
  }

  // Rows and progress live on window, so a failure late in the run keeps what was already collected.
  const rows = window.K_ROWS = [], counts = {}, failed = window.K_FAILED = [];
  async function collectStore(id, store) {
    const cats = (await post("/kr-api/offer-categories", {storeId: id, requirePromotionValidAt: now})).offerCategories || [];
    const seen = new Set();
    for (const c of cats) {
      for (let off = 0; off < c.count + 24; off += 24) {
        const j = await post("/kr-api/offer-category", {storeId: id, pricing: {requirePromotionValidAt: now}, offset: off, limit: 24,
                                                       category: {kind: "productCategory", slug: c.slug}, dietaryPreferences: diet});
        for (const o of j.offers || []) {
          if (seen.has(o.id)) continue;
          seen.add(o.id);
          const r = row(store, o, c.name.finnish);
          if (r) rows.push(r);
        }
        if (!(j.offers || []).length) break;
        await sleep(1500);
      }
    }
    counts[store] = seen.size;
    window.K_PROGRESS = counts;
    console.log(store, seen.size);
  }
  const queue = Object.entries(STORES);
  await Promise.all([0].map(async () => {   // one store at a time
    while (queue.length) {
      const [id, store] = queue.shift();
      try { await collectStore(id, store); }
      catch (e) { if (/reload/.test(e.message)) throw e; failed.push(store); console.warn(store, e.message); }
    }
  }));
  // K-Ruoka app offers ("Mobiilietu"): valid in the store once activated in the app.
  try {
    const mob = await (await fetch("/kr-api/weekly-mobile-offers", {headers})).json();
    const valid = iso => (iso ? "Voimassa " + dmy(iso) + " asti" : "");
    for (const m of mob.results || []) {
      const was = parseFloat(String(m.NormalPrice || "").replace(",", "."));
      const price = typeof m.Price === "number" ? m.Price : null;
      for (const sid of m.Stores || []) {
        if (!STORES[sid] || !price) continue;
        rows.push([STORES[sid], "", (m.LocalizedName && m.LocalizedName.finnish) || m.Name, price, m.Unit === "kpl" ? "" : (m.Unit || ""),
                   was > price ? was : null, Number(m.DiscountPercentage) || null,
                   "Mobiilietu K-Ruoka-sovelluksessa" + (m.AdditionalInfo ? ", " + m.AdditionalInfo : ""), valid(m.ValidUntil),
                   "", m.Image ? m.Image + IMG : "", (m.Eans && m.Eans[0]) || "k" + m.OfferNameId, m.Brand || ""]);
      }
    }
  } catch (e) { console.warn("mobile offers failed", e); }
  const out = {source: "k-ruoka", collected: new Date().toISOString(), counts, failed, offers: rows};
  window.K_RESULT = out;
  if (window.K_DOWNLOAD !== false && !window.K_NO_DOWNLOAD) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(out)], {type: "application/json"}));
    a.download = "k-ruoka-snapshot.json";
    a.click();
  }
  return counts;
})().catch(e => { window.K_ERROR = String((e && e.message) || e); console.error(e); });
