#!/usr/bin/env python3
"""
REUSABLE AD-HOC VERIFIER for the money system.

Run:  python scripts/verify_money_system.py
      (set MONEY_DIR=/path/to/money if not run from the money/ dir)
      (set GH_TOKEN=... to also verify GitHub liveness)

Write it to a temp path, run it, delete it — ad-hoc, NOT a suite.
This script is the canonical self-check after any change to the money system.

CURRENT REALITY (2026-07-14+): 15 pipelines, 62 packages.
Targets below assert 15/62; if the system regrows, bump EXPECTED_*.
"""
import json, os, glob, subprocess, sys

HERE = os.environ.get("MONEY_DIR") or os.path.dirname(os.path.abspath(__file__))
TOKEN = os.environ.get("GH_TOKEN", "")

EXPECTED_PIPELINES = 15
EXPECTED_PACKAGES = 62

def raw(u):
    import urllib.request
    req = urllib.request.Request(u, headers={"Authorization": f"token {TOKEN}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8")

def main():
    results = []
    def chk(l, ok, d=""):
        results.append((l, "PASS" if ok else "FAIL", d))
        if not ok:
            print("FAIL:", l, d)

    # 1) Every pipelineN_*.py has a working self-test
    n = 1
    while glob.glob(os.path.join(HERE, f"pipeline{n}_*.py")):
        f = glob.glob(os.path.join(HERE, f"pipeline{n}_*.py"))[0]
        r = subprocess.run(["python", f, "self-test"], capture_output=True,
                           text=True, cwd=HERE)
        chk(f"p{n} self-test", r.returncode == 0, r.stdout.strip()[:60])
        n += 1
    chk(f"{EXPECTED_PIPELINES} pipelines present", n - 1 == EXPECTED_PIPELINES,
        f"found {n - 1}")

    # 2) run_all self-test asserts the exact 15/62 counts
    r = subprocess.run(["python", os.path.join(HERE, "run_all.py"), "self-test"],
                       capture_output=True, text=True, cwd=HERE)
    ok_self = (r.returncode == 0 and f"{EXPECTED_PIPELINES} pipelines" in r.stdout
               and f"{EXPECTED_PACKAGES} packages" in r.stdout)
    chk(f"run_all self-test ({EXPECTED_PIPELINES}/{EXPECTED_PACKAGES})", ok_self,
        r.stdout.strip()[:60])

    # 3) 62 packages on disk
    packs = (glob.glob(os.path.join(HERE, "*_packs", "*.json"))
             + glob.glob(os.path.join(HERE, "gigs", "*.json")))
    chk(f"{EXPECTED_PACKAGES} packages on disk", len(packs) == EXPECTED_PACKAGES,
        f"{len(packs)}")

    # 4) No TODO placeholders in any n8n workflow
    bad = sum(1 for f in packs if "todo" in json.dumps(
        json.load(open(f, encoding="utf-8")).get("n8n_workflow") or {}).lower())
    chk("no TODO in workflows", bad == 0, f"{bad}")

    # 5) 62 listings, covering all 15 pack dirs (no dir-drift)
    lsts = glob.glob(os.path.join(HERE, "listings", "*", "*.md"))
    chk(f"{EXPECTED_PACKAGES} listings", len(lsts) == EXPECTED_PACKAGES, f"{len(lsts)}")
    dirs = sorted(set(os.path.basename(os.path.dirname(p)) for p in lsts))
    chk(f"{EXPECTED_PIPELINES} listing dirs", len(dirs) == EXPECTED_PIPELINES,
        f"{len(dirs)}")

    # 6) Dashboard reflects 15/62
    dash = open(os.path.join(HERE, "INCOME_DASHBOARD.md"), encoding="utf-8").read()
    chk("dashboard 15/62",
        f"{EXPECTED_PIPELINES} pipelines" in dash
        and f"{EXPECTED_PACKAGES} ready-to-sell" in dash)

    # 7) Optional GitHub liveness
    if TOKEN:
        for f in ["money/run_all.py", "money/INCOME_DASHBOARD.md",
                  "money/generate_listings.py", "money/generate_moltbook_drafts.py"]:
            try:
                t = raw(f"https://raw.githubusercontent.com/itsPremkumar/"
                        f"Hermes-Full-Autonomous-Company/master/{f}")
                chk(f"GH live {f}", len(t) > 200)
            except Exception as e:
                chk(f"GH live {f}", False, str(e))

    all_ok = all(s == "PASS" for _, s, _ in results)
    passed = sum(1 for _, s, _ in results if s == "PASS")
    print(f"{'ALL CHECKS PASSED' if all_ok else 'SOME FAILED'} ({passed}/{len(results)})")
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
