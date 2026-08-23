#!/usr/bin/env python3
"""
Ad-hoc liveness probe for a local Paperclip server (Windows dev box).

Confirms, against the live runtime:
  1. server health endpoint returns status:ok
  2. API auth works via fresh sign-in (token pulled from the Set-Cookie
     response header, NOT the body `token` field which is only the session id)
  3. the issue board is reachable with the session cookie
  4. the Hermes Engineer agent exists and reports a status
  5. the agent's run-log directory has at least one .ndjson (proves runs happen)

Run from the Hermes venv python:
    python "C:/Users/PREM KUMAR/AppData/Local/hermes/skills/devops/paperclip-self-host/scripts/verify-paperclip-live.py"
Exit 0 = all checks passed. This is AD-HOC verification, not a test suite.
Override CID / AID / BASE by editing the constants below if the company changes.
"""
import json, os, sys, urllib.request, urllib.error

BASE = "http://localhost:3100"
CID = "3056c999-62ba-4321-ae69-799a61286bad"
AID = "9eed5712-96c2-4f3c-9fea-1cef0e6b7f2f"
RUNLOG = r"C:\one\paperclip-company\data\paperclip\instances\default\data\run-logs\%s\%s" % (CID, AID)


def http(method, path, cookie=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Origin": BASE, "Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode(), None, r.headers
    except urllib.error.HTTPError as e:
        return e.read().decode(errors="replace"), e.code, e.headers
    except Exception as e:
        return None, str(e), None


def main():
    results = []
    body, err, _ = http("GET", "/api/health")
    try:
        ok = json.loads(body).get("status") == "ok"
    except Exception:
        ok = False
    results.append(("health", ok, (body or "")[:80]))

    # sign-in -> real token is in Set-Cookie, decode %2B/%3D
    body, code, hdrs = http("POST", "/api/auth/sign-in/email",
                            body={"email": "prem@local.dev", "password": "LocalDevPass123!"})
    sc = hdrs.get("Set-Cookie") if hdrs else None
    cookie = None
    if sc:
        raw = sc.split("session_token=", 1)[1].split(";", 1)[0]
        cookie = "paperclip-default.session_token=" + raw.replace("%2B", "+").replace("%3D", "=")
    results.append(("sign-in+Set-Cookie", bool(cookie), "cookie set" if cookie else "no Set-Cookie"))

    if cookie:
        body, code, _ = http("GET", f"/api/companies/{CID}/issues", cookie=cookie)
        try:
            n = len(json.loads(body)) if isinstance(json.loads(body), list) else 0
        except Exception:
            n = 0
        results.append(("issues(auth)", code == 200 and n > 0, f"count={n} http={code}"))
    else:
        results.append(("issues(auth)", False, "no cookie"))

    if cookie:
        body, code, _ = http("GET", f"/api/companies/{CID}/agents", cookie=cookie)
        try:
            ag = json.loads(body)
            ag = ag if isinstance(ag, list) else ag.get("agents", ag.get("data", []))
            eng = next((a for a in ag if a.get("id") == AID), None)
            results.append(("agent-status", bool(eng),
                            f"Hermes Engineer status={eng.get('status') if eng else 'MISSING'}"))
        except Exception as e:
            results.append(("agent-status", False, str(e)[:80]))
    else:
        results.append(("agent-status", False, "no cookie"))

    try:
        files = os.listdir(RUNLOG) if os.path.isdir(RUNLOG) else []
        nd = [f for f in files if f.endswith(".ndjson")]
        results.append(("run-logs", len(nd) > 0, f"{len(nd)} run logs present"))
    except Exception as e:
        results.append(("run-logs", False, str(e)[:80]))

    print("=== AD-HOC Paperclip liveness probe (not a suite) ===")
    allok = True
    for name, ok, detail in results:
        if not ok:
            allok = False
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
