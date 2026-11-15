// Each alert is its own entry in Netlify Blobs (key "a/<token>"), so two people signing up at the same
// moment never write to the same place. Listing reads every entry, which is fine for hundreds of alerts.
import { getStore } from "@netlify/blobs";

function store() {
  return getStore({ name: "hintavahdit", consistency: "strong" });
}

const keyOf = token => "a/" + token;

export async function getAlert(token) {
  return store().get(keyOf(token), { type: "json" });
}

export async function putAlert(alert) {
  await store().setJSON(keyOf(alert.token), alert);
}

export async function deleteAlert(token) {
  await store().delete(keyOf(token));
}

export async function listAlerts() {
  const s = store();
  const { blobs } = await s.list({ prefix: "a/" });
  const out = [];
  for (let i = 0; i < blobs.length; i += 25) {
    const part = await Promise.all(blobs.slice(i, i + 25).map(b => s.get(b.key, { type: "json" })));
    out.push(...part.filter(Boolean));
  }
  return out;
}
