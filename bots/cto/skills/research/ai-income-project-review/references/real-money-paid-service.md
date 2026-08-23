# Real-money paid service (the constructive pivot)

When an "AI earns money" pitch fails verification, build the user a REAL owned
paid service instead of another fantasy. Pattern proven this session for an
India-based user with an open-source video engine.

## Concept
Wrap a product the user ALREADY controls in a static order site:
- Pricing tiers (pay-per-deliverable, INR).
- Order form -> opens a pre-filled WhatsApp chat to the user's number.
- Payment via UPI (India) — zero gateway fees, no 85% middleman.
- Deploy $0 on Vercel Hobby (static, no build step).

## Files (static, no framework)
- `index.html` — hero, use-cases, pricing cards, "How it works", order form.
- `style.css` — dark theme, responsive.
- `script.js` — config block (`WHATSAPP_NUMBER` intl digits-only) + order form
  builds a `https://wa.me/<NUMBER>?text=<encoded message>` and `window.open`s it.
- `vercel.json` — `{"version":2,"buildCommand":null,"outputDirectory":".","framework":null,"rewrites":[{"source":"/(.*)","destination":"/index.html"}]}`
- `README.md` — setup + live link.

## WhatsApp deep-link builder (script.js core)
```js
const WHATSAPP_NUMBER = "919345568244"; // international, digits only, NO +
function buildMessage(){ /* name, package, type, script -> multiline */ }
const url = "https://wa.me/" + WHATSAPP_NUMBER + "?text=" + encodeURIComponent(msg);
window.open(url, "_blank");
```

## UPI (critical: never fabricate)
Leave a placeholder in index.html: `<code id="upiId">YOUR_UPI_ID_HERE</code>`.
Tell the user to replace it with their real UPI handle. Do NOT invent one.

## Deploy
```bash
cd <site-dir>
vercel deploy --prod --yes --name aivid-studio   # --name is deprecated but works
# After edits: vercel deploy --prod --yes
```

## Verify (ad-hoc, not a suite)
- `curl -sL <live-url>` returns 200 and hero copy present.
- `curl` each asset (style.css, script.js) returns 200.
- GitHub: each file `raw.githubusercontent.com/USER/REPO/main/<f>` returns 200.
- `git status --porcelain` clean; temp files removed.

## Why this beats the pitches
- 100% of every UPI payment is the user's (no marketplace cut).
- Cost to fulfill = minutes of their own machine + free engine = near-pure margin.
- No crypto, no dead marketplace, no "survival tier" theater.

## Live example (this session)
https://github.com/itsPremkumar/aivid-studio  ->  https://aivid-studio-rust.vercel.app
Built on top of: https://github.com/itsPremkumar/Automated-Video-Generator
