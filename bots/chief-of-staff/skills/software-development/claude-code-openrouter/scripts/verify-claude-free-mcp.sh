#!/usr/bin/env bash
# verify-claude-free-mcp.sh
# Ad-hoc verification that a `claude` binary (real or shim) serves MCP
# on a free model via OpenRouter. Sends initialize + tools/list.
set -u
PY="${PYTHON:-python}"
WRAPPER="${1:?usage: verify-claude-free-mcp.sh <wrapper-path> [model]}"
MODEL="${2:-tencent/hy3:free}"
OUT=$(mktemp) || exit 1
trap 'rm -f "$OUT"' EXIT

printf '%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"v","version":"0"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
| CLIFF_TIMEOUT=25 timeout 25 bash "$WRAPPER" mcp serve > "$OUT" 2>/dev/null

SZ=$(wc -c < "$OUT" 2>/dev/null || echo 0)
[ "$SZ" -lt 100 ] && echo "FAIL: output $SZ bytes" && exit 1

"$PY" -c "
import json
with open('$OUT') as f: lines=[l.strip() for l in f if l.strip()]
r=[json.loads(l) for l in lines]
i=[x for x in r if x.get('id')==1]; t=[x for x in r if x.get('id')==2]
s=i[0]['result']['serverInfo'] if i else {}
tools=[x['name'] for x in t[0]['result']['tools']] if t else []
req={'Write','Read','Edit','Bash','Glob','Grep','Agent','WebFetch'}
ok=s.get('name')=='claude/tengu' and s.get('version')=='2.1.183' and req.issubset(tools)
print(('PASS' if ok else 'FAIL')+' server='+s.get('name','?')+' v'+s.get('version','?')+' tools='+str(len(tools)))
exit(0 if ok else 1)
" 2>&1 || exit 1
