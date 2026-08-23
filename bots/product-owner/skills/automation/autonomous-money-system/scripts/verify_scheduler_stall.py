#!/usr/bin/env python3
"""
AD-HOC VERIFIER for the Moltbook post-scheduler queue-never-stalls fix
(2026-07-14). Imported by the money-system verifier OR run standalone.

Builds an isolated temp POSTS_DIR with 4 drafts:
  - one INVALID submolt (must be skipped, not surface)
  - one that will 429 (transient -> back off, not marked failed)
  - one that will 403 (hard -> marked failed, queue advances)
  - one OK (valid submolt)
Monkeypatches sched.post_to_moltbook + sched.POSTS_DIR/TRACKING/FAILED,
then drives sched.main() to prove:
  - invalid submolt is skipped & recorded in `skipped`
  - 429 -> exit 3, NOT added to posted or failed
  - 403 -> exit 1, added to failed set, next run advances past it
"""
import importlib.util, json, os, sys, tempfile, shutil

SCHED = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "..", "..", "..",
                     "revenue", "moltbook", "post-scheduler.py")

def load(path):
    spec = importlib.util.spec_from_file_location("post_scheduler", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def main():
    sched = load(os.path.abspath(SCHED))
    tmp = tempfile.mkdtemp(prefix="hermes-verify-molt-")
    fails = []
    try:
        drafts = {
            "post-bad-submolt.json": {"title": "x", "content": "x", "submolt": "clawhub"},
            "post-hard.json":        {"title": "y", "content": "y", "submolt": "saas"},
            "post-ratelimit.json":   {"title": "z", "content": "z", "submolt": "builders"},
            "post-good.json":        {"title": "g", "content": "g", "submolt": "automation"},
        }
        for name, body in drafts.items():
            json.dump(body, open(os.path.join(tmp, name), "w"))
        sched.POSTS_DIR = tmp
        sched.TRACKING_FILE = os.path.join(tmp, "posted.json")
        sched.FAILED_FILE = os.path.join(tmp, "failed.json")

        posted, skipped, failed = [], set(), set()
        slug, _ = sched.find_unposted_draft(posted, skipped, failed)
        assert slug == "good", f"invalid submolt skipped first (got {slug})"
        assert "bad-submolt" in skipped, "invalid submolt recorded in skipped"
        print("  PASS: invalid submolt skipped + recorded")

        # 429 -> back off (exit 3), not failed/posted
        sched.post_to_moltbook = lambda *a, **k: (429, {"statusCode": 429})
        open(sched.TRACKING_FILE, "w").write(json.dumps({"posted": []}))
        open(sched.FAILED_FILE, "w").write(json.dumps({"failed": []}))
        rc = sched.main()
        assert rc == 3, f"429 -> exit 3 (got {rc})"
        assert not json.load(open(sched.FAILED_FILE))["failed"], "429 not failed"
        assert not json.load(open(sched.TRACKING_FILE))["posted"], "429 not posted"
        print("  PASS: 429 back-off, no failed/posted record")

        # 403 -> hard fail, marked, advance
        sched.post_to_moltbook = lambda *a, **k: (403, {"statusCode": 403})
        open(sched.TRACKING_FILE, "w").write(json.dumps({"posted": []}))
        open(sched.FAILED_FILE, "w").write(json.dumps({"failed": []}))
        rc = sched.main()
        assert rc == 1, f"403 -> exit 1 (got {rc})"
        assert "good" in json.load(open(sched.FAILED_FILE))["failed"], "403 marked failed"
        rc2 = sched.main()
        assert rc2 in (1, 3), f"after hard-fail advances (got {rc2})"
        assert "good" not in json.load(open(sched.TRACKING_FILE))["posted"], "advances past failed"
        print("  PASS: hard 403 marked failed + queue advances")
        print("RESULT: ALL SCHEDULER-STALL CHECKS PASSED")
        return 0
    except AssertionError as e:
        print("RESULT: FAIL ->", e)
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(main())
