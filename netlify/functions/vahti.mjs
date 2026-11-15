// Price alert sign-up and the links in alert emails.
//   POST /api/vahti                      {email, t, v, label, store, max, minPct}  -> new alert, sends a confirmation email
//   GET  /vahti?a=confirm&t=TOKEN        confirms the alert and sends the current matches right away
//   GET  /vahti?a=stop|stopall&t=TOKEN   asks "remove?" (a button, so email scanners that open links can't unsubscribe anyone)
//   POST /vahti?a=stop|stopall&t=TOKEN   removes one alert or all alerts of that address (also one-click unsubscribe)
import { randomUUID } from "node:crypto";
import { deleteAlert, getAlert, listAlerts, putAlert } from "./lib/db.mjs";
import { describe, TYPES } from "./lib/match.mjs";
import { sendMail, mailConfigured } from "./lib/mail.mjs";
import { runCheck, siteUrl, SITE } from "./lib/check.mjs";

const MAX_ALERTS_PER_EMAIL = 20;      // active + pending
const MAX_NEW_PER_EMAIL_PER_DAY = 8;
const MAX_NEW_TOTAL_PER_DAY = 150;

const json = (obj, status = 200) => new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json; charset=utf-8" } });
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function page(site, title, body, status = 200) {
  return new Response(`<!doctype html><html lang="fi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(title)} · ${SITE}</title><meta name="robots" content="noindex"></head>
<body style="margin:0;background:#f3f5f8;color:#14213a;font:16px/1.5 system-ui,Segoe UI,sans-serif">
<main style="max-width:34rem;margin:3rem auto;padding:24px;background:#fff;border:1px solid #d9dee8;border-radius:8px">
<h1 style="font-size:1.4rem;margin:0 0 12px">${esc(title)}</h1>${body}
<p style="margin-top:24px"><a href="${esc(site)}/" style="color:#14213a">Takaisin tarjouksiin</a></p></main></body></html>`,
    { status, headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
}

async function subscribe(req, site) {
  let p;
  try { p = await req.json(); } catch { return json({ ok: false, error: "bad_request" }, 400); }
  if (p.website) return json({ ok: true });   // honeypot field filled in: a bot, pretend it worked
  if (!mailConfigured()) return json({ ok: false, error: "mail_not_configured" }, 503);
  const email = String(p.email || "").trim().toLowerCase();
  const t = String(p.t || "q");
  const v = String(p.v || "").trim().slice(0, 80);
  const label = String(p.label || "").trim().slice(0, 160);
  const store = String(p.store || "").trim().slice(0, 60);
  const max = p.max ? Math.round(Number(String(p.max).replace(",", ".")) * 100) / 100 : null;
  const minPct = p.minPct ? Math.round(Number(p.minPct)) : null;
  if (!/^[^\s@<>]+@[^\s@<>]+\.[a-z]{2,}$/i.test(email) || email.length > 120) return json({ ok: false, error: "email" }, 400);
  if (!TYPES[t] || !v || (t === "q" && v.length < 2)) return json({ ok: false, error: "alert" }, 400);
  if (max !== null && !(max > 0 && max < 100000)) return json({ ok: false, error: "max" }, 400);
  if (minPct !== null && !(minPct > 0 && minPct < 100)) return json({ ok: false, error: "minPct" }, 400);

  const alert = { id: randomUUID().slice(0, 8), token: randomUUID(), email, t, v, label, store, max, minPct,
                  status: "pending", created: new Date().toISOString(), confirmed: null, sent: [] };
  const list = await listAlerts();
  const dayAgo = Date.now() - 864e5;
  const mine = list.filter(a => a.email === email);
  const same = mine.find(a => a.t === t && a.v === v && a.store === store && a.max === max && a.minPct === minPct);
  if (same && same.status === "active") return json({ ok: true, exists: true });
  if (mine.length >= MAX_ALERTS_PER_EMAIL) return json({ ok: false, error: "limit" });
  if (mine.filter(a => Date.parse(a.created) > dayAgo).length >= MAX_NEW_PER_EMAIL_PER_DAY) return json({ ok: false, error: "limit" });
  if (list.filter(a => Date.parse(a.created) > dayAgo).length >= MAX_NEW_TOTAL_PER_DAY) return json({ ok: false, error: "busy" });
  if (same) await deleteAlert(same.token);   // an unconfirmed duplicate is replaced by the new one
  await putAlert(alert);

  const link = site + "/vahti?a=confirm&t=" + alert.token;
  try {
    await sendMail({
      to: email,
      subject: "Vahvista hintavahti: " + describe(alert),
      text: "Joku (toivottavasti sinä) lisäsi hintavahdin " + SITE + " -sivulla:\n\n  " + describe(alert) +
            "\n\nVahvista vahti tästä:\n" + link + "\n\nJos et lisännyt vahtia, älä tee mitään. Ilman vahvistusta et saa viestejä, " +
            "ja vahvistamaton vahti poistuu viikossa.\n\n" + site + "/\n",
      html: `<div style="max-width:520px;font:15px/1.5 system-ui,Segoe UI,sans-serif;color:#14213a">
        <p>Joku (toivottavasti sinä) lisäsi hintavahdin ${SITE} -sivulla:</p>
        <p style="font-weight:600">${esc(describe(alert))}</p>
        <p><a href="${esc(link)}" style="display:inline-block;background:#14213a;color:#fff;padding:10px 16px;border-radius:8px;text-decoration:none;font-weight:600">Vahvista hintavahti</a></p>
        <p style="color:#5c6880;font-size:13px">Jos et lisännyt vahtia, älä tee mitään. Ilman vahvistusta et saa viestejä, ja vahvistamaton vahti poistuu viikossa.</p></div>`,
    });
  } catch (e) {
    console.error("confirmation email failed", e);
    await deleteAlert(alert.token);
    return json({ ok: false, error: "send" }, 502);
  }
  return json({ ok: true });
}

async function confirm(site, token) {
  const hit = await getAlert(token);
  if (!hit) return page(site, "Linkki ei ole voimassa", "<p>Vahtia ei löytynyt. Se on ehkä poistettu, tai vahvistus vanheni. Voit lisätä vahdin uudelleen sivulla.</p>", 404);
  if (hit.status !== "active") {
    hit.status = "active"; hit.confirmed = new Date().toISOString();
    await putAlert(hit);
  }
  let extra = "<p>Saat sähköpostia aina, kun uusi sopiva tarjous löytyy. Tarjoukset tarkistetaan joka aamu.</p>";
  try {
    const r = await runCheck(site, hit);
    if (r.items) extra = `<p>Lähetimme juuri ${r.items === 1 ? "yhden tarjouksen, joka sopii" : r.items + " tarjousta, jotka sopivat"} vahtiin jo nyt. Jatkossa saat viestin aina, kun uusi sopiva tarjous löytyy. Tarjoukset tarkistetaan joka aamu.</p>`;
    else if (!r.errors.length) extra = "<p>Juuri nyt sopivia tarjouksia ei ole. Saat viestin heti, kun sellainen löytyy. Tarjoukset tarkistetaan joka aamu.</p>";
  } catch (e) {
    console.error("first check failed", e);
  }
  return page(site, "Hintavahti on päällä", `<p><strong>${esc(describe(hit))}</strong></p>${extra}`);
}

async function stop(site, req, token, all) {
  const a = await getAlert(token);
  if (!a) return page(site, "Vahti on jo poistettu", "<p>Tätä vahtia ei ole enää päällä.</p>");
  if (req.method !== "POST") {
    const what = all ? "kaikki osoitteen " + a.email.replace(/^(.).*@/, "$1…@") + " hintavahdit" : "hintavahdin \u201d" + describe(a) + "\u201d";
    return page(site, all ? "Poistetaanko kaikki vahdit?" : "Poistetaanko vahti?",
      `<p>Haluatko poistaa ${esc(what)}?</p><form method="post"><button style="font:inherit;font-weight:600;padding:10px 16px;border-radius:8px;border:0;background:#d22d2d;color:#fff;cursor:pointer">Poista</button></form>`);
  }
  // Removed alerts are deleted outright, address included.
  const gone = all ? (await listAlerts()).filter(x => x.email === a.email) : [a];
  for (const x of gone) await deleteAlert(x.token);
  return page(site, "Poistettu", `<p>${all ? "Kaikki hintavahtisi on poistettu. Et saa niistä enää viestejä." : "Hintavahti on poistettu. Et saa siitä enää viestejä."}</p>`);
}

export default async (req) => {
  const site = siteUrl(req);
  const url = new URL(req.url);
  try {
    if (url.pathname.startsWith("/api/")) {
      if (req.method !== "POST") return json({ ok: false, error: "method" }, 405);
      return await subscribe(req, site);
    }
    const a = url.searchParams.get("a"), t = url.searchParams.get("t") || "";
    if (!/^[0-9a-f-]{36}$/.test(t)) return page(site, "Linkki ei ole voimassa", "<p>Linkki on vajaa. Kopioi se sähköpostista kokonaan.</p>", 400);
    if (a === "confirm") return await confirm(site, t);
    if (a === "stop" || a === "stopall") return await stop(site, req, t, a === "stopall");
    return page(site, "Linkki ei ole voimassa", "<p>Tuntematon linkki.</p>", 400);
  } catch (e) {
    console.error(e);
    return url.pathname.startsWith("/api/") ? json({ ok: false, error: "server" }, 500)
      : page(site, "Jokin meni pieleen", "<p>Yritä hetken päästä uudelleen.</p>", 500);
  }
};

export const config = { path: ["/api/vahti", "/vahti"] };
