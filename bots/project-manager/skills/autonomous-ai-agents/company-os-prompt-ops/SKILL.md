---
name: company-os-prompt-ops
description: Maintain the AI Company OS "constitution" — the master operating prompt that governs the Hermes→Paperclip→OpenClaw autonomous company — plus the prompt-library versioning workflow and the dual-GitHub-repo sync (working copy `paperclip-company` ↔ canonical `Hermes-Full-Autonomous-Company`). Use when the user asks to improve/version/update "the prompt", review the operating prompt, archive an old prompt version, or keep the two company repos in sync. Distinct from paperclip-company-ops (which DRIVES a live Paperclip instance) — this skill governs the DOCUMENTS and KNOWLEDGE that define the company, not the running server.
triggers:
  - "improve / update / review the master operating prompt / constitution"
  - "version the prompt, archive old prompt, add vX.0"
  - "keep the two company repos in sync / push prompt to canonical repo"
  - "what is the canonical company architecture (Hermes 1st boss, 3 money-gates)"
  - "refresh prompts/executive-master-operating-prompt"
---

# Company OS — Prompt & Constitution Ops

This skill governs the **defining documents** of the autonomous company: the master
operating prompt (the "constitution"), the versioned prompt library, and the dual-repo
layout that keeps a *working copy* and a *canonical source of truth* in lockstep.

It does NOT drive the running Paperclip server (that is `paperclip-company-ops`). It
maintains the knowledge/OS spec the server and agents inherit.

## 0. The canonical architecture (load-bearing mental model)

Adopted 2026-07-15 and locked. Source of truth:
`docs/hermes-paperclip-openclaw-architecture.md` (exists in BOTH repos).

```
        YOU  (principal — only you cross the 3 revenue gates)
                 │
        HERMES  = 1st BOSS  (self-improving, strategic, COMMANDS both layers below)
              │
              ├─ PAPERCLIP = 2nd BOSS  (operations: org chart, budgets, agents, heartbeat)  :3100
              │       └─ agents (Hermes / Claude / coding CLIs) execute issues
              │
              └─ OPENCLAW = channel  (phone/Telegram front-door + computer-use)  gateway :18789
                      └─ drafts & notifies; Hermes persists the artifact
```

- **Hermes** is the *top* boss that **commands** Paperclip + OpenClaw. They are layers, not rivals.
- **OpenClaw is draft-only** — it refuses to write files; Hermes must persist the artifact.
- **3 money-gates are human-only (non-negotiable):** (1) marketplace KYC, (2) payment
  linkage (UPI `premkumar016555@oksbi`), (3) first publish/approval click. Agents build
  the machine, then STOP at the gate.
- **Verify all external stats via the GitHub API** before trusting them — AI-generated
  "comparison" docs with star/version/date numbers have been found FABRICATED.

Any change to the governing Charter (Section 0 of the prompt) is a **human-reviewed
decision**, never a silent self-edit.

## 1. The master prompt (constitution) — file + versioning convention

The living master prompt is:
`prompts/executive-master-operating-prompt-vX.0.md`

Rules (from the prompt's own §7 self-improvement loop):
- **Never delete** an old version — move it to `prompts/archive/` with a note on WHY it
  was superseded.
- Bump the **major** version when the architecture/charter changes; minor for wording.
- Each new version's header must state: what it supersedes, the date, and the key deltas
  (use the template in `templates/prompt-version-header.md`).
- The prompt is itself a prompt: improve it like any other artifact, cite sources, prefer
  officially-published guidance over "leaked system prompt" content (frequently fabricated).

### How to produce a new version (verified 2026-07-15)
1. Read the CURRENT top version (e.g. v3.0) AND any newer architecture/decision docs in
   `docs/` to find what drifted (v3.0 predated the 2026-07-15 architecture → that's the
   delta that justified v4.0).
2. Write `executive-master-operating-prompt-vNEXT.0.md` with a header documenting the delta.
3. Archive the previous version: `cp` it into `prompts/archive/vPREV-executive-master-operating-prompt.md`
   and add a `README-note.md` line explaining the supersession.
4. Commit + push to BOTH repos (see §3).

## 2. The dual-repo layout

| Role | Repo | Local working copy |
|---|---|---|
| **Working copy** (where you edit) | `github.com/itsPremkumar/paperclip-company` | `/c/one/paperclip-company` |
| **Canonical source of truth** | `github.com/itsPremkumar/Hermes-Full-Autonomous-Company` | (no local clone needed; push via API) |

The prompt's Charter names `Hermes-Full-Autonomous-Company` as the single source of truth,
so the master prompt MUST live there too — not just in `paperclip-company`. Keep both in
sync. The working copy's `git remote` is `paperclip-company`; the canonical repo is
updated through the GitHub **Contents API** (PUT) because there's no local clone of it.

**CRITICAL: both repos' default branch is `master`, NOT `main`.** A `raw.githubusercontent`
or API path using `main` returns **404**. Always use `master`.

## 3. Syncing a prompt file to the canonical repo via the Contents API

Pattern (verified 2026-07-15). Gotchas are many — read §4 first.

```bash
cd /c/one/paperclip-company
# 1) GitHub token from git credential helper (cached GCM creds; gh is NOT installed)
TOKEN=$(printf 'protocol=https\nhost=github.com\n' | git credential fill 2>/dev/null | grep -i "^password=" | sed 's/password=//')
REPO="itsPremkumar/Hermes-Full-Autonomous-Company"

# 2) base64 the local file (base64 -w0 = one line, MSYS git-bash has it)
B64=$(base64 -w0 prompts/executive-master-operating-prompt-v4.0.md)

# 3) build JSON with the Hermes venv python (see §4 re: python3 missing)
PY="/c/Users/PREM KUMAR/AppData/Local/hermes/hermes-agent/venv/Scripts/python"
PAYLOAD=$(PYTHONIOENCODING=utf-8 "$PY" -c "import json,sys; print(json.dumps({'message':'prompts: add v4.0 ...','content':sys.argv[1]}))" "$B64")

# 4) PUT (creates or updates). Include sha only if updating an existing file.
curl -sL -X PUT "https://api.github.com/repos/$REPO/contents/prompts/executive-master-operating-prompt-v4.0.md" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "$PAYLOAD" \
  | grep -o '"path": "prompts/[^"]*"'
```

The working copy is pushed normally: `git add prompts/... && git commit && git push origin master`.

## 4. GitHub Contents API gotchas (verified 2026-07-15 — easy to get wrong)

- **`python3` is absent** on this git-bash/Windows host, but a Python interpreter ships in
  the Hermes venv: `/c/Users/PREM KUMAR/AppData/Local/hermes/hermes-agent/venv/Scripts/python`.
  Use it for any JSON building / base64 round-trip. `execute_code` is BLOCKED for
  subprocess calls, so do NOT use it to drive git/curl — use `terminal` + the venv python.
- **The Contents API GET returns STALE/EMPTY after a PUT.** After writing a file you may
  still see `"size": 0` from `GET /contents/...` and an empty `raw.githubusercontent.com`
  fetch for several seconds/minutes (CDN cache keyed by path). **Do NOT trust the GET to
  confirm success.** Instead verify via the **git blob**: the PUT response returns a
  `content.sha`; fetch `GET /repos/{owner}/{repo}/git/blobs/{sha}` and `base64 -d` the
  `content` field to confirm the real bytes landed. (Verified: a 16,110-byte v2.0 archive
  showed `size: 0` on GET for minutes, but the blob held the correct text.)
- **To UPDATE an existing file, you must include its current `sha`** in the PUT body, else
  you get `409 {"message":"SHA does not match"}`. Fetch the sha first:
  `grep '"sha"' <(curl -sL ".../contents/path") | head -1`.
- **Don't rely on `curl -b` cookie jars** here (MSYS path issue) — but this is the GitHub
  *API*, so you use `Authorization: Bearer $TOKEN` (the GCM token), not the Paperclip
  cookie. The Paperclip cookie (§paperclip-company-ops) is a different system entirely.
- **`base64 -w0`** keeps the content on one line so it embeds cleanly in the JSON `-d`
  payload. Without `-w0`, newlines break the JSON.
- **Token scope:** the cached GCM token had `repo`/contents write scope (worked for PUT). If
  you get `401`, the token may be stale — re-run `git credential fill` (it re-reads the
  helper cache; no interactive prompt needed on this box).

## 5. Verification checklist after a prompt update
- [ ] New `vN.0` file written with delta header (use template).
- [ ] Previous version copied into `prompts/archive/` + note added.
- [ ] Working copy committed + `git push origin master` succeeded.
- [ ] Canonical repo file PUT succeeded (verify via **blob**, not GET).
- [ ] If archiving in canonical repo too, PUT the archived copy AND verify via blob.
- [ ] Tell the user WHERE the prompt now lives (local path + both repo URLs + branch=master).

## 6. When the user asks "are you fully working based on this prompt?"
Be HONEST about the gap between *documented* and *live*:
- The prompt can claim "verified, running today" — but verify the actual servers:
  Paperclip `:3100` and OpenClaw `:18789` may be DOWN (no process, port returns nothing).
- A well-written prompt does NOT mean the autonomous runtime is executing. Report the
  distinction: "system is built + documented; live runtime is currently stopped."

Detail + worked session trace (v3.0→v4.0, dual-repo push, blob verification):
`references/sync-gotchas.md`.
Canonical architecture spec (authoritative): `docs/hermes-paperclip-openclaw-architecture.md`
(in both repos) — mirror its facts into any prompt update.
