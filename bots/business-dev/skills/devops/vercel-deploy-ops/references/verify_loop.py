#!/usr/bin/env python3
"""
verify_loop.py — reusable verification for the Sproutern daily-improvement loop.

Run from the sproutern repo root. Confirms the loop scripts compile, the shell
orchestrator is syntactically valid, decide.py produces an action, and the
content writer still rejects thin posts. NOT a green test suite — behavioral
checks only (the project has no jest/eslint/tsc runnable on the relay).

Usage:  python scripts/verify_loop.py
Exit 0 = all passed.
"""
import os, py_compile, subprocess, sys, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOOP = os.path.join(ROOT, "scripts", "website-improve-loop")
res = []
def chk(label, ok, d=""):
    res.append(ok); print(("PASS" if ok else "FAIL"), "-", label, ("| " + d) if d else "")

py_scripts = ["measure.py", "decide.py", "improve.py", "verify.py"]
for s in py_scripts:
    p = os.path.join(LOOP, s)
    try:
        py_compile.compile(p, doraise=True); chk("compile " + s, True)
    except Exception as e:
        chk("compile " + s, False, str(e)[:80])

# sh syntax (relay has sh, NOT /bin/bash)
sh = os.path.join(LOOP, "loop.sh")
r = subprocess.run(["sh", "-n", sh], capture_output=True, text=True)
chk("sh -n loop.sh", r.returncode == 0, r.stderr[:80])

# decide end-to-end: bad LCP -> 'speed'
snap = {"measured_at": "x", "plan": "hobby",
        "signals": {"pageviews_30d": 4653, "lcp_ms_7d": 1925.0, "recent_5xx": ""}}
json.dump(snap, open(os.path.join(LOOP, "metrics_snapshot.json"), "w"))
try:
    r = subprocess.run([sys.executable, os.path.join(LOOP, "decide.py")],
                       capture_output=True, text=True, timeout=60)
    ok = r.returncode == 0 and os.path.exists(os.path.join(LOOP, "next_action.json"))
    chk("decide.py runs + writes next_action.json", ok, r.stdout.strip()[:40])
    if ok:
        a = json.load(open(os.path.join(LOOP, "next_action.json")))
        chk("LCP>1200 -> 'speed'", a["action"] == "speed", f"action={a['action']}")
finally:
    for f in ("metrics_snapshot.json", "next_action.json"):
        try: os.remove(os.path.join(LOOP, f))
        except: pass

# content writer rejects thin (regression guard)
thin = os.path.join(ROOT, "scripts", "_probe_thin.md")
open(thin, "w", encoding="utf-8").write("# T\n\n" + "word. " * 100)
rw = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "daily_content_writer.py"),
    "--slug", "zz-probe", "--title", "P", "--category", "X",
    "--keywords", "a", "--body-file", thin], capture_output=True, text=True, timeout=60)
chk("content writer rejects thin (<800w)", rw.returncode == 2, f"rc={rw.returncode}")
os.remove(thin)
bp = os.path.join(ROOT, "src", "content", "blog", "zz-probe.md")
if os.path.exists(bp): os.remove(bp)

# key artifacts exist
for p in ["src/config/monetization.ts", "src/components/monetization/AffiliateStrip.tsx",
          "DAILY_LOOP.md", "IMPROVEMENT_LOG.md", "daily-hermes-automation/README.md"]:
    chk("exists " + p, os.path.exists(os.path.join(ROOT, p)))

passed = sum(1 for x in res if x)
print(f"\nVERIFY: {passed}/{len(res)} passed")
sys.exit(0 if passed == len(res) else 1)
