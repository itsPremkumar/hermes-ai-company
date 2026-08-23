# Owned Service Funnel (India-native, manual-fulfillment) — VERIFIED recipe

Built + deployed LIVE 2026-07-14 as `Prem AI Video Studio` (faceless-video service on the
user's own `Automated-Video-Generator` engine). Pays via UPI to the creator — the one payment
method Gumroad/PayPal/Stripe-India do NOT natively support for instant INR. No middleman, no
commission, near-100% margin.

## Why this is the right "make money" path vs the autonomous-agent repos
The user brought 3 "AI earns money for you" repos (Conway automaton, moltlaunch/cashclaw,
ertugrulakben/cashclaw). ALL failed the vetting checklist: empty/unverified marketplaces,
anonymous testimonials, cost-first (you fund compute + wallet), some with 85% commission. This
funnel is the opposite: YOU own the customer, the payout, and the engine.

## Stack
- Hosting: **Vercel Hobby ($0)**, static site, no build step.
- Capture: order HTML form → JS builds a pre-filled **WhatsApp deep-link** → opens on submit.
- Payment: **UPI** (creator-owned ID pasted into one line; e.g. `name@bank`).
- Fulfillment: MANUAL — agent/user renders the deliverable with the user's own open-source engine
  (here: AVG → MP4). So it is NOT "autonomous income"; state that honestly.

## Files (copy from templates/service-order-site/)
- `index.html` — hero, use-cases, 3 pricing tiers (pay-per-video), how-it-works, order form.
- `style.css` — dark theme, responsive, no external deps except Google Fonts.
- `script.js` — CONFIG block at top: set `WHATSAPP_NUMBER` (international digits only,
  NO `+`/spaces, e.g. `919345568244`). Builds wa.me link on submit. Copy-UPI handler.
- `vercel.json` — static config (see below).

## vercel.json (static, no build)
```json
{
  "version": 2,
  "buildCommand": null,
  "outputDirectory": ".",
  "framework": null,
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

## Deploy + verify (verified commands)
```bash
cd C:\one\<site-folder>
vercel deploy --prod --yes --name <slug>      # Hobby; aliases to *.vercel.app
# Then verify:
curl -sL -m 20 https://<alias>.vercel.app -o out.html -w "HTTP %{http_code} bytes %{size_download}\n"
curl -sL -m 15 https://<alias>.vercel.app/style.css -w "style.css %{http_code}\n" -o /dev/null
curl -sL -m 15 https://<alias>.vercel.app/script.js  -w "script.js %{http_code}\n" -o /dev/null
grep -o "<hero headline text>" out.html      # confirm page rendered, not error page
```
All 3 returned `200` + full content for the live site this session.

## GOTCHAS
- **DO NOT hardcode a guessed UPI/phone.** Use obvious placeholders (`YOUR_UPI_ID_HERE`) and tell
  the user to edit ONE line. (I initially wrote a guessed UPI handle and had to revert it — never
  invent payment identifiers.)
- **WhatsApp number format:** digits only, international, no `+`/spaces. `919345568244` not
  `+91 93455 68244`. Wrong format = dead link.
- **MSYS path doubling** still applies (write_file of `/c/Users/...` → `C:\c\Users\...`); use
  Windows-absolute paths. `vercel` CLI lives at `C:\nvm4w\nodejs\vercel` and is already authed as
  `premkumar016555` — no login step needed.
- **Be honest in copy:** the service is *manual AI-assisted fulfillment*, not autonomous. The
  deployed site says "manual AI-assisted video service fulfilled by a human" + "24h delivery".
- **Lint false-alarm:** `script.js` (browser JS) trips the node syntax check when written; it's
  fine — it runs in the browser, not as a module. Don't "fix" it into a broken state.

## Margin reality to tell the user
Each order costs minutes of local compute (engine is free/self-hosted) + a few rupees. So
Rs499-Rs7999/order is almost pure margin — vs an 85% marketplace cut or a dead crypto marketplace.

## Traffic (the part the repos skipped — you must drive it)
The site is the funnel; customers come from where the audience is: own IG/YouTube Shorts samples,
Quora/Reddit answers, creator/freelance Telegram/WhatsApp groups. No traffic = no orders.
