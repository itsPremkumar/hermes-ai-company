# avo-lab stall watchdog (cron no_agent job; silent unless stalled)
import datetime
import json
import os

LAB = "C:/one/avo-lab"
LINEAGE = os.path.join(LAB, "lineage.jsonl")
STALE_HOURS = 12
REJECT_STREAK = 3


def main():
    if not os.path.exists(LINEAGE):
        print("ALERT avo-lab: lineage.jsonl missing - evolution state not initialized.")
        return
    rows = []
    with open(LINEAGE, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    if not rows:
        print("ALERT avo-lab: lineage.jsonl empty - no variation steps recorded.")
        return
    last = rows[-1]
    ts = datetime.datetime.fromisoformat(last["ts"])
    age_h = (datetime.datetime.now(datetime.timezone.utc) - ts).total_seconds() / 3600
    if age_h > STALE_HOURS:
        print(f"ALERT avo-lab: stalled - last activity {age_h:.1f}h ago "
              f"({last.get('version')}). Check cron job avo-lab-evolution-tick.")
        return
    tail = rows[-REJECT_STREAK:]
    if len(tail) == REJECT_STREAK and all(not r.get("committed") for r in tail):
        print(f"ALERT avo-lab: unproductive cycle - {REJECT_STREAK} consecutive "
              "rejected attempts. Supervisor redirection needed.")


main()
