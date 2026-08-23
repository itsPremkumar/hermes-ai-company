#!/bin/bash
# Watches a parent-owned subdomain (e.g. *.dpdns.org) for NS delegation to Vercel, then
# auto-attaches it in Vercel + adds the verification TXT and A records. Used when DigitalPlat's
# managed DNS is unhealthy and you delegated the subdomain's NS directly to ns1/ns2.vercel-dns.com.
#
# SET THESE BEFORE RUNNING:
DOMAIN="sproutren.dpdns.org"          # the subdomain being delegated
PROJECT="sproutern-hermes"            # Vercel project name
HEX="2d13e1c32db09aa7be39"            # from Vercel's "Verification Required" TXT value
REPO_DIR="/tmp/spr-check"             # dir with the cloned repo (for `vercel` cwd/scope)
MAX_ATTEMPTS=40                       # ~40 * 90s = 60 min timeout

cd "$REPO_DIR" 2>/dev/null || cd "$(mktemp -d)"

echo "Watching $DOMAIN for Vercel NS delegation (ns1/ns2.vercel-dns.com)..."
for i in $(seq 1 "$MAX_ATTEMPTS"); do
  NS=$(nslookup -type=NS "$DOMAIN" 2>/dev/null | grep -i "vercel-dns" | head -1)
  if [ -n "$NS" ]; then
    echo "PROPAGATED at attempt $i: $NS"
    echo "=== attaching domain in Vercel ==="
    vercel domains add "$DOMAIN" "$PROJECT" --non-interactive 2>&1 | head -20
    echo "=== adding verification TXT + A record (Vercel DNS zone) ==="
    vercel dns add "$DOMAIN" _vercel TXT "vc-domain-verify=$DOMAIN,$HEX" --non-interactive 2>&1 | head -5
    vercel dns add "$DOMAIN" @ A 216.198.79.1 --non-interactive 2>&1 | head -5
    echo "=== waiting for TLS, then HTTPS check ==="
    sleep 30
    curl -I "https://$DOMAIN" 2>&1 | head -5
    echo "DONE"
    exit 0
  fi
  echo "attempt $i: not yet propagated, waiting 90s..."
  sleep 90
done
echo "TIMEOUT: NS not propagated after ~60 min. Check DigitalPlat's NS form / re-click Update."
exit 1
