---
name: reachable-landing-page-deploy
description: Deploy a static lead-capture/payment landing page to a reachable public URL (HTTP 200 + email/payment input) from a low-RAM/low-tooling box, using a local server + a no-account tunnel. Use when a task requires a deployed, verifiable landing page and there is no GitHub/npm-account deploy path.
---

# Reachable landing page deploy (local server + tunnel)

Goal: a public URL returning HTTP 200 with an `<input type="email">` or payment input.
Approach: serve a static `index.html` locally, then expose it through a free no-account tunnel.

## Steps
1. Make a workdir and write `index.html` (static, self-contained). Include:
   - `<input type="email" ... required>` (lead capture) AND/OR a payment link (`https://buy.stripe.com/...`).
   - Wire the form to `https://formsubmit.co/<your-email>` (free, no signup) with hidden fields
     `_subject`, `_captcha=false`, `_template=table`. It emails you every submission.
2. Serve locally (no build tooling):
   `python -m http.server 8080 --bind 0.0.0.0` (background=true).
   Verify: `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/` → 200,
   `curl ... | grep -c 'type="email"'` → >0.
3. Expose publicly with **cloudflared quick tunnel** (BEST — no account, no interstitial, works with browser UAs):
   - Download single binary: `curl -sL -o cloudflared.exe https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe`
   - Run: `./cloudflared.exe tunnel --url http://127.0.0.1:8080` (background=true).
   - Grab the `https://*.trycloudflare.com` URL from the log.
4. Verify the PUBLIC URL with a real browser User-Agent (critical — see pitfalls):
   `curl -s -A "Mozilla/5.0 ... Chrome/124 Safari/537.36" <url> -w "%{http_code}\n"`
   Must be 200 and contain the email/payment input. Also confirm via browser_navigate render.

## Pitfalls
- **ngrok**: the bundled/auto-provisioned binary often has an INVALID or missing authtoken →
  `ERR_NGROK_4018`. Needs a real dashboard token. Don't rely on it.
- **localtunnel** (`npx localtunnel --port 8080`): returns HTTP 200 to DEFAULT (non-browser) curl,
  but **HTTP 511 interstitial password gate** to real browser UAs → fails the real-visit test.
  Avoid as primary URL.
- **localhost.run** (`ssh -R 80:localhost:8080 localhost.run`): now requires an SSH key
  (`Permission denied (publickey)`). No-account anonymous tunnels are gone.
- **cloudflared quick tunnel** is the reliable winner: clean HTTPS, no account, no UA gate.
  Downside: random subdomain changes each restart (fine for verification; for stable URLs
  use a real Cloudflare account or GitHub Pages).
- Always test the PUBLIC url with a browser UA, not just default curl — the two differ on tunnels.
- Keep BOTH the local http.server AND the tunnel running; killing either breaks reachability.
