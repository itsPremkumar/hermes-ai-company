# Paperclip mutations from this Windows/MSYS host — robust Python recipe

`curl` is fragile on this host for mutations:
- `curl -b cj.txt` never reads the MSYS-path Netscape jar → 401 Unauthorized.
- `curl -d @/tmp/file.json` fails ("option -d: error encountered when reading a file")
  because native Windows curl can't open the MSYS `/tmp` path.
- Native Windows `python` can't read `/c/one/...` MSYS paths (use `C:/one/...`).

The reliable pattern: do EVERYTHING in one `python` process — read the token, build the
payload inline (no file), POST via `urllib`, with the three required headers. **Verified this
session:** created issue PRE-86 via POST → HTTP 201; invoked heartbeat via POST → HTTP 202.

```python
import json, urllib.request, urllib.error

CJ      = r"C:/one/paperclip-company/cj.txt"
COMPANY = "3056c999-62ba-4321-ae69-799a61286bad"
AGENT   = "9eed5712-96c2-4f3c-9fea-1cef0e6b7f2f"
BASE    = "http://localhost:3100"
ORIGIN  = "http://localhost:3100"

def token():
    for line in open(CJ):
        if "session_token" in line:
            return line.split("\t")[-1].strip()   # Netscape jar: last tab field
    raise RuntimeError("session_token not found in " + CJ)

def call(method, path, payload=None):
    """One-shot request. No temp files, no MSYS-path issues.
    Verified: POST create -> 201, POST heartbeat -> 202."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Cookie": "paperclip-default.session_token=" + token(),
        "Content-Type": "application/json",
        "Origin": ORIGIN,          # REQUIRED for all mutations (403 without it)
        "Referer": ORIGIN + "/",   # harmless, mirrors browser; include for safety
    }
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        r = urllib.request.urlopen(req)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:800]

# ---- Create issue (verified: HTTP 201, body["identifier"] e.g. PRE-86) ----
st, body = call("POST", f"/api/companies/{COMPANY}/issues", {
    "title": "Revenue dashboard M4 — month-4 projection, burn analysis + reconciliation",
    "description": "Next iteration of the monthly revenue-tracking cadence...",
    "status": "in_progress",
    "priority": "medium",
    "assigneeAgentId": AGENT,
    "parentId": "<PARENT_ISSUE_UUID>",   # parent's id (UUID), NOT its identifier (PRE-nn)
})
print(st, body.get("identifier"), body.get("id"))

# ---- Invoke heartbeat (verified: HTTP 202, status "queued") ----
st, body = call("POST", f"/api/agents/{AGENT}/heartbeat/invoke", {})
print(st, body.get("id"), body.get("status"))
# body["id"] is the run id; verify via GET /api/heartbeat-runs/{id}
# or the run-log file data/paperclip/instances/default/data/run-logs/{COMPANY}/{AGENT}/{id}.ndjson

# ---- PATCH issue (analogous; mirrors the skill's verified curl PATCH) ----
# st, body = call("PATCH", f"/api/issues/<ISSUE_UUID>",
#     {"assigneeAgentId": AGENT, "status": "in_progress"})

# ---- GET (no body; Origin header is harmless on GET) ----
# st, body = call("GET", f"/api/companies/{COMPANY}/issues")
# if isinstance(body, list): print("issues:", len(body))
```

Notes:
- `parentId` must be the parent issue's **`id`** (UUID), not its `identifier` string.
- A `POST` landing in `status:"todo"` with an assignee does NOT auto-start a run (unlike a
  PATCH that flips to `in_progress`); invoke a heartbeat (or set `status:"in_progress"` on
  create) for immediate execution.
- Always inspect the response body, never trust the status code alone (a rejected cookie
  returns HTTP 200 with `{"error":"Unauthorized"}`).
