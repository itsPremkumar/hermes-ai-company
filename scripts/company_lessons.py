#!/usr/bin/env python3
"""company_lessons.py — persistent cross-build lessons ledger (AVO-style memory).

Records structured lessons after every completed/failed build so future builds
inherit the company's scar tissue instead of re-learning it.

Commands:
  record <card_id> <status: done|failed> "<what_worked;what_failed>" 
  read [n]                     print last n lessons (default 10)
  stats                        counts by status
"""
import json, os, sqlite3, sys, time

HERMES = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes")
DB = os.path.join(HERMES, "kanban", "boards", "it-company-ops", "kanban.db")
LEDGER = os.path.join(HERMES, "profiles", "agent-builder", "memories", "lessons.jsonl")

def card(card_id):
    c = sqlite3.connect(DB, timeout=15)
    c.row_factory = sqlite3.Row
    row = c.execute("select id,title,assignee,status from tasks where id=?", (card_id,)).fetchone()
    c.close()
    return dict(row) if row else {}

def cmd_record(card_id, status, notes):
    cd = card(card_id)
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "card": card_id,
        "project": (cd.get("title") or "").replace("Build:", "").strip()[:40],
        "assignee": cd.get("assignee"),
        "status": status,
        "worked": [],
        "failed": [],
    }
    for part in notes.split(";"):
        part = part.strip()
        if not part:
            continue
        (entry["worked"] if part.lower().startswith("+") else entry["failed"]).append(part.lstrip("+-").strip())
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"lesson recorded: {entry['project']} [{status}] "
          f"+{len(entry['worked'])}/-{len(entry['failed'])}")
    return 0

def cmd_read(n=10):
    if not os.path.isfile(LEDGER):
        print("(no lessons yet)"); return 0
    lines = open(LEDGER, encoding="utf-8").read().splitlines()[-int(n):]
    for l in lines:
        e = json.loads(l)
        w = "; ".join(e.get("worked", []))
        f = "; ".join(e.get("failed", []))
        print(f"[{e['status']:6}] {e['project'][:30]:32} +{w[:40]:42} -{f[:40]}")
    return 0

def cmd_stats():
    if not os.path.isfile(LEDGER):
        print("0 lessons"); return 0
    lines = [json.loads(l) for l in open(LEDGER, encoding="utf-8") if l.strip()]
    done = sum(1 for e in lines if e["status"] == "done")
    fail = sum(1 for e in lines if e["status"] == "failed")
    print(f"{len(lines)} lessons | done: {done} | failed: {fail}")
    return 0

if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "record":
        sys.exit(cmd_record(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else ""))
    if len(sys.argv) >= 2 and sys.argv[1] == "read":
        sys.exit(cmd_read(sys.argv[2] if len(sys.argv) > 2 else 10))
    if len(sys.argv) >= 2 and sys.argv[1] == "stats":
        sys.exit(cmd_stats())
    print(__doc__); sys.exit(1)
