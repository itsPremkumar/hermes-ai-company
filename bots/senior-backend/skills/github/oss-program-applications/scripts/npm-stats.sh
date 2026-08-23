#!/usr/bin/env bash
# Verified npm download stats for an application pitch.
# Usage: bash npm-stats.sh <package-name>
# Prints: last-month point total + 6-month range with per-month sums and top days.
# Pitfall handled: range API entries are {"day","downloads"} — we SUM downloads,
# never count entries (counting entries yields ~28-31 "downloads" per month and
# contradicts the point API).
set -euo pipefail
PKG="${1:?usage: npm-stats.sh <package-name>}"

echo "=== last-month (point API) ==="
curl -s "https://api.npmjs.org/downloads/point/last-month/${PKG}"
echo; echo

START=$(date -v-6m +%F 2>/dev/null || date -d '6 months ago' +%F 2>/dev/null || echo "$(date +%Y)-01-01")
END=$(date +%F)
echo "=== ${START}..${END} (range API) ==="
curl -s "https://api.npmjs.org/downloads/range/${START}:${END}/${PKG}" | python -c "
import json, sys
from collections import defaultdict
d = json.load(sys.stdin)
days = d['downloads']
print('days in window:', len(days))
print('total downloads:', sum(x['downloads'] for x in days))
m = defaultdict(int)
for x in days:
    if x['downloads'] > 0:
        m[x['day'][:7]] += x['downloads']
print('per-month sums (real downloads):')
for k in sorted(m):
    print(' ', k, m[k])
top = sorted((x for x in days if x['downloads'] > 0), key=lambda x: -x['downloads'])[:5]
print('top days (release-spike signal):', ', '.join(f\"{x['day']}={x['downloads']}\" for x in top))
"
