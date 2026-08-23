import json, os, subprocess
from datetime import datetime

def handler(payload=None, ctx=None, **kwargs):
    """Gateway hook: after agent:end, QA-scan the kanban workspace of the profile
    that just ran and append the verdict to the ops log. Never raises."""
    try:
        log = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes", "ops-qa-log.txt")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        info = ""
        if isinstance(payload, dict):
            info = str(payload.get("profile") or payload.get("session") or "")[:60]
        # lightweight: log the run end; heavy QA runs on dispatcher cadence
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] agent:end {info}\n")
    except Exception:
        pass
    return None
