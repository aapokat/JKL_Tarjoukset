// Daily price alert check (Netlify scheduled function). Runs after the morning data refresh:
// GitHub Actions fetches the offers at 03:17 UTC, Netlify rebuilds the site, and this runs at 06:40 UTC
// (08:40 / 09:40 Finnish time). Each address gets at most one digest per day.
import { runCheck } from "./lib/check.mjs";
import { mailConfigured } from "./lib/mail.mjs";

export default async () => {
  if (!mailConfigured()) {
    console.log("Email is not configured (RESEND_API_KEY or SMTP_*, and MAIL_FROM); skipping.");
    return;
  }
  const site = (process.env.URL || "").replace(/\/$/, "");
  const r = await runCheck(site);
  console.log("alert check:", JSON.stringify(r));
};

export const config = { schedule: "40 6 * * *" };
