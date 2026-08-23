# Wiring a free subdomain (dpdns.org, eu.org, etc.) to a host

You don't own the parent zone of a free subdomain (e.g. `sproutren.dpdns.org` under
`dpdns.org`). That changes how you connect it to Vercel/Cloudflare vs a domain you fully own.

## Core rule
**DNS records live where the nameservers point.** The parent `dpdns.org` zone delegates the
subdomain to whatever NS you set at the registrar (DigitalPlat). Records are then edited at the
delegated host (Vercel or Cloudflare) — NEVER at DigitalPlat's "DNS records" tab (that tab is
locked behind their managed-DNS card and isn't authoritative once you delegate away).

## Option A — Delegate NS straight to Vercel (cleanest, no Cloudflare)
1. Registrar (DigitalPlat) Nameservers tab → set `ns1.vercel-dns.com`, `ns2.vercel-dns.com`,
   clear NS3–NS8 → Update.
2. Vercel → Project → Settings → Domains → add `sproutren.dpdns.org`.
   - Vercel shows "Verification Required" + a TXT `_vercel` + A `@` → `216.198.79.1` to add.
   - If it says "linked to another Vercel account", that's the standard pre-verification gate;
     the TXT record is the remedy. Records become editable only AFTER the NS propagates and
     Vercel creates the zone.
3. Wait for propagation, then add the TXT + A in Vercel's DNS tab (or via `vercel dns add`
   once the zone exists). Vercel auto-issues TLS.

## Option B — Cloudflare Subdomain Setup (use when you want Cloudflare, or registrar DNS is broken)
1. Cloudflare → Add a domain → enter `sproutren.dpdns.org` (full subdomain, NOT just `dpdns.org`).
   Cloudflare detects it's a subdomain and offers **Subdomain setup** (partial zone). Pick Free.
2. Cloudflare assigns 2 NS, e.g. `jean.ns.cloudflare.com` / `leonard.ns.cloudflare.com`. COPY them.
3. Registrar Nameservers tab → set ONLY those 2 Cloudflare NS (delete any Vercel/other lines —
   a domain MUST have exactly one authoritative NS set; mixing Cloudflare + Vercel NS is invalid
   and the parent will refuse to publish). → Update.
4. Cloudflare → DNS → Records → Add: CNAME `sproutren` → `cname.vercel-dns.com`
   (Proxy orange or gray, both work).
5. Vercel still needs the domain added + ownership TXT (now added in Cloudflare DNS, since
   Cloudflare is authoritative). Vercel reads the CNAME → `cname.vercel-dns.com` and issues TLS.

## CRITICAL verification step (do this BEFORE investing time)
After the registrar "Update successful", confirm the parent actually published the delegation:
```
nslookup -type=NS sproutren.dpdns.org          # expect the delegated NS
nslookup -type=NS sproutren.dpdns.org ns1.dpdns.org   # direct query to parent auth NS
```
If it returns `Non-existent domain` / `Query refused` from the parent's own NS, the delegation
was NOT published — the registrar's "Update successful" UI message is misleading.

## DigitalPlat (dpdns.org) specific caveat — VERIFIED failure mode
DigitalPlat's DNS service can be in an "unhealthy" state (dashboard error:
"DigitalPlat DNS cannot create or restore zones while its nameservers are unhealthy"). In that
state, the "Use DigitalPlat DNS" button is dead AND custom-NS delegations for subdomains do NOT
publish to the parent `dpdns.org` zone — confirmed over a 60-min / 40-attempt poll where every
`nslookup -type=NS` stayed `Non-existent domain` and direct queries to `ns1/ns2.dpdns.org` returned
"Query refused". Neither Vercel nor Cloudflare can verify ownership until the parent delegates.
The "Recommended" badge in the dashboard = DigitalPlat's OWN managed DNS (the broken one), NOT
Cloudflare — DigitalPlat's docs use Cloudflare only as a neutral screenshot example and do not
endorse it. Their "Ask Digi AI" widget is the support channel to escalate a stuck delegation.

## Division of work when an agent can't reach Cloudflare
Hermes cannot drive Cloudflare from this session (no `wrangler`/Cloudflare token/MCP tool here,
though the Cloudflare MCP server DOES exist per the main skill). You can either:
- do the Cloudflare dashboard clicks yourself and let the agent finish the Vercel side, or
- paste a Cloudflare API token (Zone:DNS edit + Zone:Read) so the agent calls Cloudflare's REST API.

## Why not "normal" Cloudflare (full zone) on a subdomain?
Full Cloudflare requires Cloudflare to be the DNS authority for the whole zone, which needs the
parent delegation changed to Cloudflare — impossible when you don't own the parent. Subdomain
Setup (partial zone, NS delegation of just the subdomain) is the correct mechanism.
