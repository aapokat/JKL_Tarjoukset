// Finds new matches for active alerts and emails each address one digest.
import { deleteAlert, listAlerts, putAlert } from "./db.mjs";
import { describe, eur, loadOffers, matches, offerKey } from "./match.mjs";
import { sendMail } from "./mail.mjs";

export const SITE = "Jyväskylän tarjoukset";
const MAX_ITEMS = 40;
const MAX_SENT_KEYS = 600;   // per alert; old keys drop off when an offer has long since ended
const PENDING_DAYS = 7;

export function siteUrl(req) {
  return (process.env.URL || (req ? new URL(req.url).origin : "")).replace(/\/$/, "");
}

const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const where = o => o.stores.length > 3 ? o.stores.slice(0, 3).join(", ") + " ja " + (o.stores.length - 3) + " muuta" : o.stores.join(", ");
const priceText = o => o.price ? eur(o.price) : "−" + o.pct + " %";

export function digest(site, email, items, alerts) {
  const shown = items.slice(0, MAX_ITEMS);
  const more = items.length - shown.length;
  const stopAll = site + "/vahti?a=stopall&t=" + alerts[0].token;
  const subject = "Hintavahti: " + items.length + (items.length === 1 ? " uusi tarjous" : " uutta tarjousta");
  const text = "Hintavahtisi löysivät uusia tarjouksia:\n\n" + shown.map(({ o }) =>
      "- " + o.name + ": " + priceText(o) + (o.was ? " (ennen " + eur(o.was) + ")" : "") + (o.note ? ", " + o.note : "") +
      "\n  " + where(o) + (o.valid ? ", " + o.valid : "") + "\n  " + (o.url || site)).join("\n") +
    (more > 0 ? "\n...ja " + more + " muuta sivulla." : "") +
    "\n\nKaikki tarjoukset: " + site + "/\n\n" +
    alerts.map(a => "Poista vahti \"" + describe(a) + "\": " + site + "/vahti?a=stop&t=" + a.token).join("\n") +
    "\nPoista kaikki vahtisi: " + stopAll + "\n";
  const rows = shown.map(({ o }) => `<tr>
      <td style="padding:8px 10px 8px 0;vertical-align:top;width:72px">${o.img ? `<img src="${esc(o.img)}" width="64" height="64" alt="" style="display:block;width:64px;height:64px;object-fit:contain;background:#fff;border:1px solid #e3e7ee;border-radius:6px">` : ""}</td>
      <td style="padding:8px 0;vertical-align:top;font:14px/1.4 system-ui,Segoe UI,sans-serif;color:#14213a">
        <a href="${esc(o.url || site + "/")}" style="color:#14213a;font-weight:600;text-decoration:none">${esc(o.name)}</a><br>
        <span style="display:inline-block;background:#ffd94a;padding:1px 6px;border-radius:3px;font-weight:700">${esc(priceText(o))}</span>
        ${o.was ? `<span style="color:#5c6880;text-decoration:line-through;margin-left:4px">${esc(eur(o.was))}</span>` : ""}
        ${o.pct && o.price ? `<span style="color:#d22d2d;font-weight:700;margin-left:4px">−${o.pct} %</span>` : ""}
        ${o.note ? `<br><span style="color:#14213a;font-size:12px">${esc(o.note)}</span>` : ""}
        <br><span style="color:#5c6880;font-size:12px">${esc(where(o))}${o.valid ? " · " + esc(o.valid) : ""}</span>
      </td></tr>`).join("");
  const html = `<div style="max-width:560px;margin:0 auto;font:14px/1.5 system-ui,Segoe UI,sans-serif;color:#14213a">
    <h1 style="font-size:20px;margin:0 0 4px">Hintavahtisi löysivät ${items.length} ${items.length === 1 ? "uuden tarjouksen" : "uutta tarjousta"}</h1>
    <p style="margin:0 0 12px;color:#5c6880">${esc(alerts.map(describe).join(" · "))}</p>
    <table role="presentation" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse">${rows}</table>
    ${more > 0 ? `<p>...ja ${more} muuta. <a href="${esc(site)}/">Katso kaikki sivulta</a>.</p>` : `<p><a href="${esc(site)}/">Kaikki tarjoukset</a></p>`}
    <p style="color:#5c6880;font-size:12px;border-top:1px solid #e3e7ee;padding-top:10px">Tarkista hinta aina kaupassa.<br>
    ${alerts.map(a => `<a href="${esc(site)}/vahti?a=stop&amp;t=${esc(a.token)}" style="color:#5c6880">Poista vahti "${esc(describe(a))}"</a>`).join("<br>")}<br>
    <a href="${esc(stopAll)}" style="color:#5c6880">Poista kaikki vahtisi</a></p></div>`;
  return { to: email, subject, text, html, unsubscribe: stopAll };
}

/**
 * Check alerts and send digests. only: optional alert object to check just that one (right after confirming).
 * Returns {emails, items, errors}.
 */
export async function runCheck(site, only) {
  const { offers } = await loadOffers(site);
  const all = only ? [only] : await listAlerts();
  const alerts = all.filter(a => a && a.status === "active");
  const byEmail = new Map();
  for (const a of alerts) {
    const sent = new Set(a.sent || []);
    for (const o of offers) {
      if (!matches(a, o)) continue;
      const key = offerKey(o);
      if (sent.has(key)) continue;
      sent.add(key);
      if (!byEmail.has(a.email)) byEmail.set(a.email, []);
      byEmail.get(a.email).push({ a, o, key });
    }
  }
  const delivered = {};   // alert id -> keys
  const result = { emails: 0, items: 0, errors: [] };
  for (const [email, items] of byEmail) {
    items.sort((x, y) => (y.o.pct || 0) - (x.o.pct || 0));
    const mine = [...new Map(items.map(x => [x.a.id, x.a])).values()];
    try {
      await sendMail(digest(site, email, items, mine));
      result.emails++; result.items += items.length;
      for (const x of items) (delivered[x.a.id] = delivered[x.a.id] || []).push(x.key);
    } catch (e) {
      result.errors.push(email.replace(/^(.).*@/, "$1…@") + ": " + e.message);
    }
  }
  for (const a of alerts) {
    if (!delivered[a.id]) continue;
    await putAlert({ ...a, sent: [...(a.sent || []), ...delivered[a.id]].slice(-MAX_SENT_KEYS), lastSent: new Date().toISOString() });
  }
  if (!only) {   // never confirmed within a week: forget it, address included
    const cutoff = Date.now() - PENDING_DAYS * 864e5;
    for (const a of all) if (a.status === "pending" && Date.parse(a.created) < cutoff) await deleteAlert(a.token);
  }
  return result;
}
