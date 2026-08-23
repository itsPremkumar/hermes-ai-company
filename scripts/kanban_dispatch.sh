#!/usr/bin/env bash
# Kanban single-flow dispatcher v2 - THE ONLY thing allowed to release work.
#
# Hard-won rules on this 6GB Windows box:
#   - The gateway auto-dispatches ANY ready/todo card it sees (ignores config
#     caps). Therefore cards must LIVE in 'blocked' (never touched) and we
#     release exactly ONE into 'ready' per tick.
#   - Never release a second card while one is still running.
#   - Silent unless something fails.

DB="$LOCALAPPDATA/hermes/kanban/boards/it-company-ops/kanban.db"

read_db() {
  python - "$DB" "$1" <<'PYEOF'
import sqlite3, sys
conn = sqlite3.connect(sys.argv[1], timeout=10)
q = sys.argv[2]
if q == "running":
    print(conn.execute("select count(*) from tasks where status='running'").fetchone()[0])
elif q == "ready":
    print(conn.execute("select count(*) from tasks where status IN ('ready','todo')").fetchone()[0])
elif q == "next":
    r = conn.execute("select id from tasks where status='blocked' order by priority desc, created_at asc limit 1").fetchone()
    print(r[0] if r else "")
PYEOF
}

RUNNING=$(read_db running)
[ "$RUNNING" -ge 1 ] && exit 0            # a build is in flight - stay quiet

READY=$(read_db ready)
if [ "$READY" -eq 0 ]; then
  NEXT=$(read_db next)
  [ -z "$NEXT" ] && exit 0                # queue empty - company finished its backlog
  PROMOTED=$(hermes kanban promote "$NEXT" "hourly line: single-card release" --force 2>&1)
  case "$PROMOTED" in
    *ready*) : ;;
    *) echo "KANBAN PROMOTE FAILED: $PROMOTED"; exit 0 ;;
  esac
fi

OUT=$(hermes kanban dispatch --max 1 --json 2>&1) || { echo "KANBAN DISPATCH FAILED: $(echo "$OUT" | tail -3)"; exit 0; }
echo "$OUT" | grep -iE '"error"|spawn_failed' | head -3
exit 0
