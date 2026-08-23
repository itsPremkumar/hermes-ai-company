# Custom domain attach — free subdomain (dpdns.org / DigitalPlat) chicken-and-egg

## The problem
`vercel domains add <subdomain> <project>` returns:
```
{ "status":"error", "reason":"domain_not_owned",
  "message":"Not authorized to use <sub>.dpdns.org (403) domains add is for
  domains you already own or control via DNS..." }
```
Vercel verifies ownership by checking that the subdomain's DNS ALREADY points at Vercel
(or a verification TXT exists). For a **free subdomain whose zone doesn't exist yet**
(`nslookup` → `Non-existent domain`), the zone has no records, so Vercel can't confirm
control and refuses to claim it. You cannot attach the domain before the DNS exists.

## Correct order (deploy FIRST, attach domain SECOND)
1. **Deploy the app** (works fine with no custom domain):
   `vercel deploy --prod --yes --name <project> --build-env NEXT_PUBLIC_SITE_URL=https://<sub>.dpdns.org`
   → produces `https://<project>.vercel.app` immediately.
2. **Create the DNS zone** at the subdomain provider (DigitalPlat dashboard →
   "Use DigitalPlat DNS" button). This creates the zone + delegates to
   `dns1.digitalplat.org` / `dns2.digitalplat.org`.
3. **Add the CNAME** in the provider's DNS-records tab:
   | Field | Value |
   |-------|-------|
   | Type  | `CNAME` |
   | Name  | `<sub>` (provider appends `.dpdns.org`) |
   | Value | `cname.vercel-dns.com` |
   | TTL   | `3600` (or Auto) |
4. **Wait ~5 min** for propagation, then re-run the attach — now it passes ownership:
   `vercel domains add <sub>.dpdns.org <project> --non-interactive`
5. **Verify**: `nslookup <sub>.dpdns.org` (expect CNAME → cname.vercel-dns.com) and
   `curl -I https://<sub>.dpdns.org` (expect 200; Vercel auto-provisions TLS).

## CLI flag gotchas
- `vercel domains add` has **NO `--yes`** flag → `unknown or unexpected option: --yes`.
  Use `--non-interactive` (default when an agent is detected) and pass the project as a
  positional arg: `vercel domains add <domain> <project> --non-interactive`.
- `vercel deploy --prod` DOES accept `--yes` — the two commands differ. Don't reuse the flag.
- `vercel domains inspect <domain>` → "You don't have access" until the domain is attached
  to a project. Ignore that error pre-attach; `nslookup` is the real ownership signal.

## Why deploy before attach (not the reverse)
A production `vercel deploy --prod` of a large Next.js app (sproutern: 200+ tools, 180+
games, ~200 .ts files) takes **~8 min** end-to-end on Vercel's build servers (yarn install
~99s + `next build` ~2.6min + route generation). The build runs remotely, so the user's
local RAM is irrelevant. Run it **background** and wait for the completion notification.
The custom domain is cosmetic on top of the deploy — get the app live first, then wire DNS.

## dpdns.org / DigitalPlat specifics
- `*.dpdns.org` is a **free** subdomain service (DigitalPlat). You don't own a registrar
  account; you get managed DNS in the dashboard at `dashboard.digitalplat.org/domains/<sub>.dpdns.org`.
- Tabs: Nameservers (recommends "Use DigitalPlat DNS"), DNS records, Renew, WHOIS Privacy, Delete.
- Clicking "Use DigitalPlat DNS" auto-creates the zone — no manual NS entry needed.
- A single CNAME to `cname.vercel-dns.com` is sufficient for a Vercel-hosted subdomain
  (no A-record IP juggling).
