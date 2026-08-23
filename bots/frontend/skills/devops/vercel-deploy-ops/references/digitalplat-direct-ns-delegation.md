# DigitalPlat dpdns.org → Vercel via direct NS delegation (managed-zone-unhealthy fix)

Parent-owned free subdomain (`sproutren.dpdns.org` under `dpdns.org`, run by DigitalPlat).
DigitalPlat's "Use DigitalPlat DNS" button creates a *managed* zone on their backend. When
that backend is down you get a red banner: **"DigitalPlat DNS cannot create or restore zones
while its nameservers are unhealthy."** The manual **NS form** (NS1–NS8) is a SEPARATE path:
it writes the delegation directly into the parent `dpdns.org` zone (DigitalPlat's own
authoritative infra, which is UP), so it works even while their managed-zone service is dead.

## Why Vercel NS (not a CNAME)
Vercel gives an *apex* domain its own nameservers (`ns1/ns2.vercel-dns.com`) and a *subdomain*
a CNAME (`cname.vercel-dns.com`). But for a subdomain you do NOT own the parent of, the clean
move is to make Vercel the **full DNS authority** by delegating the subdomain's NS to Vercel.
Then Vercel auto-creates the zone, serves the records, AND issues the TLS cert — no second
CNAME step, no Cloudflare account, no 24-7 server.

## Steps (verified 2026-08-04, sproutern.dpdns.org → sproutern-hermes)
1. **Deploy first** (so `vercel domains add` passes ownership later):
   `vercel deploy --prod --yes --name sproutern-hermes --build-env NEXT_PUBLIC_SITE_URL=https://sproutren.dpdns.org`
   → produces `https://sproutern-hermes.vercel.app`.
2. **DigitalPlat → Nameservers tab:** set NS1=`ns1.vercel-dns.com`, NS2=`ns2.vercel-dns.com`
   (NS3–NS8 empty). Click **Update**. Expect green "Update successful. Please wait a while
   for DNS propagation to take effect."
3. **Wait for propagation** (~10–30 min; sometimes up to 1h). Verify:
   `nslookup -type=NS sproutren.dpdns.org` → should list `ns1.vercel-dns.com` / `ns2.vercel-dns.com`.
   While still `Non-existent domain`, the zone isn't live yet.
4. **Vercel dashboard → sproutern-hermes → Settings → Domains → Add** `sproutren.dpdns.org`.
   It will show **"Verification Required"** with a generic "linked to another Vercel account"
   note — that's just the pre-verify gate. It lists TWO records to add **IN VERCEL**, not DigitalPlat:
   - TXT  Name=`_vercel`  Value=`vc-domain-verify=sproutren.dpdns.org,<hex>`
   - A    Name=`@`        Value=`216.198.79.1`
   Add both in the Vercel DNS Records tab, click **Refresh**. (CLI `vercel dns add` is
   `permission_denied` until the NS has propagated and the zone is created — poll first.)
5. Vercel auto-verifies + issues the TLS cert. Confirm:
   `curl -I https://sproutren.dpdns.org` → `200`.

## Auto-attach watcher (reusable)
Background-poll the NS delegation and attach+add records the moment it propagates:
`scripts/watch_dpdns_propagation.sh` (set DOMAIN + HEX before running).

## Gotchas
- Do NOT click "Use DigitalPlat DNS" while it shows the unhealthy error, and do NOT click
  Update with the prefilled `dns1/dns2.digitalplat.org` — that just delegates to the dead zone.
- The TXT/A records go in VERCEL (the domain card's DNS Records tab), NOT DigitalPlat's DNS
  records tab. DigitalPlat's DNS records tab only manages their (broken) managed zone.
- `vercel domains add <domain> <project> --non-interactive` (NO `--yes`; that flag doesn't exist
  on `domains add`). Before NS propagates it returns `domain_not_owned` (403) — expected.
- The Cloudflare Subdomain-setup route (`references/digitalplat-cloudflare-fallback.md`) is a
  valid SECONDARY fallback if you specifically want Cloudflare in front, but direct Vercel NS is
  simpler and needs no new account.
