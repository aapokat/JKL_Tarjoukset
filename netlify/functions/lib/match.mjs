// Alert matching. The same rules as matches() in site/template.html, so the page and the emails agree.
export const TYPES = { q: "Hakusana", brand: "Tuoteperhe / merkki", cat: "Tuoteryhmä", store: "Kauppa", pid: "Tuote" };

export const norm = s => String(s || "").toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "");
export const eur = x => Number(x).toFixed(2).replace(".", ",") + " €";

export function describe(a) {
  let s = (TYPES[a.t] || a.t) + ": " + (a.t === "pid" ? a.label || a.v : a.v);
  if (a.store && a.t !== "store") s += ", " + a.store;
  if (a.max) s += ", alle " + eur(a.max);
  if (a.minPct) s += ", vähintään −" + a.minPct + " %";
  return s;
}

export function matches(a, o) {
  if (a.store && !o.stores.includes(a.store)) return false;
  if (a.max && !(o.price && o.price <= a.max)) return false;
  if (a.minPct && !((o.pct || 0) >= a.minPct)) return false;
  if (a.t === "q") {
    const words = norm(a.v).split(/\s+/).filter(Boolean);
    return words.length > 0 && words.every(w => o.key.includes(w));
  }
  if (a.t === "brand") {
    const b = norm(a.v), n = norm(o.name);
    return norm(o.brand) === b || n.startsWith(b + " ") || n.includes(" " + b + " ");
  }
  if (a.t === "cat") return o.cat === a.v;
  if (a.t === "store") return o.stores.includes(a.v);
  if (a.t === "pid") return o.pid === a.v || (!!a.label && norm(o.name) === norm(a.label));
  return false;
}

/** Same offer, same price, same validity: mailed once per alert. */
export const offerKey = o => [o.pid || o.name, o.price, o.valid].join("|");

/** offers.json (compact rows with store indexes) -> plain objects. */
export function expandOffers(d) {
  const stores = d.stores.map(s => s.name);
  return d.offers.map(o => {
    const names = o[0].map(i => stores[i]);
    return { stores: names, cat: d.cats[o[1]], name: o[2], price: o[3], unit: o[4], was: o[5], pct: o[6], note: o[7],
             valid: o[8], url: o[9], img: o[10], pid: o[11], brand: o[12],
             key: norm(o[2] + " " + o[12] + " " + names.join(" ")) };
  });
}

export async function loadOffers(siteUrl) {
  const r = await fetch(siteUrl + "/offers.json", { headers: { "cache-control": "no-cache" } });
  if (!r.ok) throw new Error("offers.json: HTTP " + r.status);
  const d = await r.json();
  return { offers: expandOffers(d), stores: d.stores.map(s => s.name), cats: d.cats };
}
