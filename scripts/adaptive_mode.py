#!/usr/bin/env python3
"""Adaptive goal/loop mode selector for the Hermes AI Company.

Decides HOW a task should run based on its requirements:
  mode=goal      -> self-iterating card (judge decides done) for complex/open-ended work
  mode=plain     -> single-pass worker for small/mechanical tasks
  loop           -> /loop-style recurring monitoring handled by cron routines

Usage:
  python adaptive_mode.py analyze "Build: research-radar"   # prints recommended flags
  python adaptive_mode.py create "Build: X" --assignee fullstack-dev [--goal-auto]
"""
import json, os, re, subprocess, sys

HERMES = os.path.expandvars(r"%LOCALAPPDATA%\hermes")
QA = os.path.join(HERMES, "scripts", "qa_harness.py")

# --- heuristics -----------------------------------------------------------
GOAL_SIGNALS = [
    r"\bbuild\b", r"\bcreate\b", r"\bimplement\b", r"\bmigrate\b",
    r"\bfix\b.*\bfail", r"\bend-to-end\b", r"\bfull\b", r"\bcomplete\b",
    r"\brefactor\b", r"\bintegrate\b", r"\bresearch\b.*\breport\b",
]
PLAIN_SIGNALS = [
    r"\brename\b", r"\bupdate\s+(readme|docs?)\b", r"\bbump\b", r"\btypo\b",
    r"\btouch\b", r"\blist\b", r"\bcheck\b.*\bstatus\b", r"\bping\b",
]

def classify(title_and_body: str):
    t = title_and_body.lower()
    goal_hits = sum(1 for p in GOAL_SIGNALS if re.search(p, t))
    plain_hits = sum(1 for p in PLAIN_SIGNALS if re.search(p, t))
    words = len(t.split())
    # decision matrix
    if plain_hits >= 1 and goal_hits == 0:
        return "plain", {"reason": "mechanical/small task", "signal_goal": goal_hits, "signal_plain": plain_hits}
    if goal_hits >= 2 or (goal_hits >= 1 and words > 25):
        return "goal", {"reason": "complex build/implement work", "signal_goal": goal_hits, "signal_plain": plain_hits,
                        "suggested_budget": 200 if words > 60 else 120}
    return "goal", {"reason": "default-safe: ambiguous tasks iterate rather than half-finish",
                    "signal_goal": goal_hits, "signal_plain": plain_hits, "suggested_budget": 120}

def gates_for(assignee: str):
    """Quality gates by bot role — deterministic done-conditions."""
    g = []
    if assignee in ("fullstack-dev", "backend", "frontend", "tech-lead"):
        g.append(f'python "{QA}" "<workspace>"')
    return g

def cmd_analyze(text):
    mode, meta = classify(text)
    out = {"recommended_mode": mode, **meta}
    print(json.dumps(out, indent=1))
    return 0

def cmd_create(argv):
    # usage: create <assignee> --dry-run? -- <free text title+body>
    # (robust to shell quote stripping: everything after -- is the task text)
    if "--" in argv:
        cut = argv.index("--")
        head, text = argv[:cut], " ".join(argv[cut+1:])
    else:
        head, text = argv[:1], " ".join(argv[1:])
    assignee = head[0] if head and not head[0].startswith("-") else "fullstack-dev"
    dry = "--dry-run" in head or "--dry-run" in argv
    if not text.strip():
        print('usage: adaptive_mode.py create fullstack-dev -- "Title. Body..."'); return 1
    mode, meta = classify(text)
    use_goal = (mode == "goal") or ("--goal-auto" in head)
    budget = meta.get("suggested_budget", 120)

    cmd = ["hermes", "kanban", "create", text.split(". ")[0][:80], "--body", text,
           "--assignee", assignee]
    if use_goal:
        cmd += ["--goal", "--goal-max-turns", str(budget)]
    print("MODE:", mode.upper(), "| goal:", use_goal, "| reason:", meta["reason"])
    print("CMD:", " ".join(cmd[:6]), "...", f"(--goal --goal-max-turns {budget})" if use_goal else "")
    if dry:
        print("(dry-run — nothing created)"); return 0
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    print((r.stdout or "").strip().splitlines()[-1] if (r.stdout or r.stderr) else "?")
    # record gate suggestion on the card comment for qa-lead visibility
    gates = gates_for(assignee)
    if gates and use_goal:
        print("GATES to add via /goal gate add inside the worker session:")
        for g in gates: print("   ", g.replace("<workspace>", "worktree path"))
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    if sys.argv[1] == "analyze":
        sys.exit(cmd_analyze(" ".join(sys.argv[2:])))
    if sys.argv[1] == "create":
        sys.exit(cmd_create(sys.argv[2:]))  # args after 'create' pass through
    print(__doc__); sys.exit(1)
