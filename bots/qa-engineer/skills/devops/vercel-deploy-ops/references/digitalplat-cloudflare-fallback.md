# DigitalPlat "nameservers unhealthy" → Cloudflare Subdomain Setup fallback (Vercel CNAME)

## Symptom
DigitalPlat dashboard → **"Use DigitalPlat DNS"** button shows a red banner:
`DigitalPlat DNS cannot create or restore zones while its nameservers are unhealthy`
`nslookup <sub>.dpdns.org` → `Non-existent domain` (zone never created).

You CANNOT create the DNS zone via DigitalPlat. Do NOT click **Update** while
`dns1/dns2.digitalplat.org` is prefilled in the manual NS form — that just delegates the
subdomain to the broken zone and fixes nothing.

## Root cause
DigitalPlat's zone-creation service fails its own internal health check. Their NS hostnames
resolve (`dns1`=192.9.243.240, `dns2`=150.230.46.101) but the automation that mints the
`<sub>.dpdns.org` zone is down. This is a provider-backend outage, not a user error.

## The reliable workaround — delegate the subdomain to Cloudflare (Subdomain/partial setup)
Normal Cloudflare "add domain" needs Cloudflare to own the whole zone — impossible for a
subdomain under a parent you don't control (`dpdns.org` NS are `ns1/2/3.dpdns.org`).
**Cloudflare Subdomain setup** is built for exactly this: you delegate ONLY `<sub>.dpdns.org`
to Cloudflare via an NS record at the parent. DigitalPlat's **manual Nameservers form (NS1–NS8)**
IS that parent-delegation mechanism.

Steps (user-driven unless a CF API token is supplied):
1. **Cloudflare → Add a Site → `<sub>.dpdns.org` → Free.** Accept the offered **Subdomain setup**.
2. Copy the **2 Cloudflare nameservers** assigned (e.g. `cruz.ns.cloudflare.com`, `tina.ns.cloudflare.com`).
3. **DigitalPlat dashboard → manual Nameservers form** → REPLACE `dns1/dns2.digitalplat.org` with
   the 2 CF nameservers → **Update**.
4. **Cloudflare → DNS → Add record**: `CNAME`, Name `<sub>`, Target `cname.vercel-dns.com`, TTL Auto.
   (Proxy ▶️ on or off both work; off = simpler.)
5. Wait ~5–15 min for NS delegation to propagate, then attach in Vercel:
   `vercel domains add <sub>.dpdns.org <project> --non-interactive`  (now passes — CF NS serve it).
6. Verify: `curl -I https://<sub>.dpdns.org` → 200 (Vercel auto-provisions TLS).

## Agent capability note (verified this session)
The Hermes session has **NO Cloudflare tool or API token**: no `wrangler`/`cloudflared` CLI on
PATH, no `CLOUDFLARE_*` env var, no CF MCP in Hermes's toolset. (A `cloudflared.exe` exists under
`C:\Users\PREM KUMAR\landing-page\` — that's the tunnel client, a different feature.) Therefore:
- Either the **USER** does Cloudflare steps 1 & 4 in the CF dashboard, or
- They paste a **Cloudflare API token** (Zone → DNS:Edit permission) and the agent drives CF via
  REST API (`GET/POST https://api.cloudflare.com/client/v4/zones/...`).
- The agent always does Vercel step 5 + verification.
- A "Cloudflare MCP" the user has in **Cursor/Claude Desktop** is a *different* assistant's tool —
  not reachable from Hermes. Don't claim to drive it.

## Decision: Vercel-direct vs Cloudflare on a free subdomain
- **Direct DigitalPlat DNS + Vercel CNAME** — least friction (2 clicks) WHEN DigitalPlat DNS is healthy.
- **Cloudflare Subdomain setup + Vercel CNAME** — use when DigitalPlat DNS is unhealthy OR the user
  explicitly wants Cloudflare WAF/caching. Slightly more clicks, fully reliable.
- Both terminate in the **same CNAME → `cname.vercel-dns.com`**; Vercel still auto-issues TLS.
  Cloudflare adds WAF/bot/cache rules Vercel's edge doesn't surface — not needed for a small
  Next.js site, so prefer direct when healthy.

## Source (verified)
DigitalPlat official docs `DigitalPlatDev/FreeDomain` LEARN.md + nameserver/CNAME tutorials:
"DigitalPlat registers domains and delegates them to external authoritative nameservers.
Ordinary DNS records are managed [in the external zone]." → confirms the manual-NS delegation model.
