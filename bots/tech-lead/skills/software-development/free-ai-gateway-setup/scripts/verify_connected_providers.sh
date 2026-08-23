#!/usr/bin/env bash
# verify_connected_providers.sh — sweep every OmniRoute connection's /test endpoint.
# Usage:  bash verify_connected_providers.sh
# Requires: OMNIROUTE up at http://localhost:20128, and INITIAL_PASSWORD in ~/.omniroute/.env
set -u
BASE="${OMNIROUTE_BASE_URL:-http://localhost:20128}"
ENVFILE="$HOME/.omniroute/.env"
PW="$(grep -E '^INITIAL_PASSWORD=' "$ENVFILE" 2>/dev/null | head -1 | cut -d= -f2-)"

[ -z "$PW" ] && { echo "ERROR: INITIAL_PASSWORD not found in $ENVFILE"; exit 1; }

# 1) login, capture auth_token cookie
TOKEN="$(curl -s -D - -o /dev/null -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" -d "{\"password\":\"$PW\"}" \
  | grep -i set-cookie | sed 's/.*auth_token=/auth_token=/;s/;.*//')"
[ -z "$TOKEN" ] && { echo "ERROR: login failed"; exit 1; }

echo "=== Connected providers ($(date -u +%FT%TZ)) ==="
IDS="$(curl -s "$BASE/api/providers" -H "Cookie: $TOKEN" \
  | python -c "import sys,json; d=json.load(sys.stdin); [print(c['id'],c['provider'],'active='+str(c['isActive'])) for c in d.get('connections',[])]")"
echo "$IDS"

echo; echo "=== /test results ==="
echo "$IDS" | while read -r id prov _; do
  [ -z "$id" ] && continue
  RES="$(curl -s -X POST "$BASE/api/providers/$id/test" -H "Cookie: $TOKEN" -m 40)"
  VALID="$(echo "$RES" | python -c "import sys,json;print(json.load(sys.stdin).get('valid'))" 2>/dev/null)"
  MSG="$(echo "$RES" | python -c "import sys,json;d=json.load(sys.stdin);print(d.get('error') or d.get('diagnosis',{}).get('message',''))" 2>/dev/null)"
  printf '%-14s valid=%-6s %s\n' "$prov" "$VALID" "$MSG"
done
