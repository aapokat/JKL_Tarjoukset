// Sending email. Set ONE of these in Netlify (Site configuration → Environment variables):
//   RESEND_API_KEY                         Resend (resend.com), with a domain you have verified there
//   SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS   any SMTP server, e.g. Gmail with an app password
// and MAIL_FROM, e.g.  Jyväskylän tarjoukset <vahti@example.fi>  (with Gmail use your Gmail address).
import nodemailer from "nodemailer";

export function mailConfigured() {
  return !!(process.env.RESEND_API_KEY || (process.env.SMTP_HOST && process.env.SMTP_USER)) && !!process.env.MAIL_FROM;
}

let transport;
function smtp() {
  if (!transport) {
    const port = Number(process.env.SMTP_PORT || 465);
    transport = nodemailer.createTransport({
      host: process.env.SMTP_HOST, port, secure: port === 465,
      auth: process.env.SMTP_PASS ? { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS } : undefined,
    });
  }
  return transport;
}

/** msg = {to, subject, text, html, unsubscribe}. Throws if sending fails. */
export async function sendMail(msg) {
  const headers = msg.unsubscribe
    ? { "List-Unsubscribe": "<" + msg.unsubscribe + ">", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click" } : {};
  if (process.env.RESEND_API_KEY) {
    const r = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { "Authorization": "Bearer " + process.env.RESEND_API_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({ from: process.env.MAIL_FROM, to: [msg.to], subject: msg.subject, text: msg.text, html: msg.html, headers }),
    });
    if (!r.ok) throw new Error("Resend " + r.status + ": " + (await r.text()).slice(0, 200));
    return;
  }
  await smtp().sendMail({ from: process.env.MAIL_FROM, to: msg.to, subject: msg.subject, text: msg.text, html: msg.html, headers });
}
