# Jarvis Escalation Triage — `ESCALATION: too many idle cycles` with NO dispatch

When `run` prints ESCALATION and **no DISPATCH block**, the cycle reached step 5
(`dispatcher.can_dispatch()` / `ready_task()`) but dispatched nothing, then bumped
the stuck counter past `stuck_cycles_before_escalation`. There are exactly THREE
distinct causes. Tell them apart BEFORE acting — the wrong fix burns retries or
strands state.

## Fast diagnosis
Run the bundled probe (prints everything in one shot):
```
PYTHONPATH=C:\Users\PREM KUMAR\prems-jarvis-hermes python <skill_dir>/scripts/jarvis_diag.py <jarvis_state.db>
```
Or manually:
```
python -m jarvis.cli --db <db> tasks
python -m jarvis.cli --db <db> log | grep -i report
```

## Cause 1 — Wedged DOING (stale)
- **Signature:** `tasks` shows a row in `doing` with an old `updated_at`; `log` has
  `event=recover` (if within `stale_doing_minutes`) or none (worker vanished).
- **Why:** worker dispatched but never reported; planner dedups on (OPEN|DOING)
  sub_goal text, so the wedged DOING blocks both re-dispatch and completion.
- **Fix:** `_recover_stale_doing()` already auto-resets DOING→OPEN after 90 min. If
  it isn't firing, lower `stale_doing_minutes` or call it. See `stale_doing_recovery.md`.

## Cause 2 — Orphaned reports (stale task IDs)
- **Signature:** `log | grep report` IDs (e.g. `ing1`, `t_40f04d84…`) do NOT match
  the live `tasks` IDs; deliverables exist on disk (spec.md, page.html) but live
  rows stay OPEN; dedup sees every sub_goal already covered so nothing new dispatches.
- **Why:** workers reported `done` under task IDs from a PREVIOUS planning round
  (planner re-planned and minted new IDs). Live rows never flip to DONE.
- **Fix:** RECONCILE — `report <live_task_id> done "<summary>"` for each verified
  deliverable (confirm the verification clause first — e.g. deploy page.html so the
  HTTP-200 check can pass). Then the next tick drives the genuinely-open task.
  See `escalation_orphaned_reports.md`.

## Cause 3 — Exhausted attempts (OPEN but undispatchable)  ← most common in practice
- **Signature:** `tasks` shows OPEN rows, `Spawn? : yes` (resource + net guard clear),
  yet NO dispatch; `jarvis_diag.py` shows `att=N/N` (attempts == max_attempts) on OPEN
  tasks and `ready_task() -> None`.
- **Why:** the task was dispatched `max_attempts` times and FAILED VERIFICATION each
  time (classic: landing page built locally but NEVER deployed, so the
  "deployed URL returns HTTP 200" gate can't pass). `ingest_worker_report` leaves it
  OPEN with `attempts == max_attempts`. `ready_task()` filters
  `t.attempts < t.max_attempts`, so it is skipped forever → no dispatch →
  permanent escalation.
- **FIX (operator-side — never just reset attempts):**
  1. Find the REAL blocker — almost always a missing external capability the
     verification assumes: a deployment target + credentials, an API key, a live
     URL. The bot cannot satisfy the clause without it.
  2. Remove the blocker (provide the deploy target / credential), THEN let the
     worker retry. To allow a retry you must clear the exhausted counter: reset the
     task's `attempts` to 0 via a tiny DB update, or raise `Defaults.max_attempts` in
     `jarvis/core/defaults.py`. But ONLY after the blocker is gone, or you re-burn
     retries on the same failing gate.
  3. Alternative if the verification clause was wrong (e.g. you'd accept a local file
     instead of a deployed URL): relax the clause in the task's `verification` field,
     then it passes on the next tick.
- **Do NOT:** blindly `report <id> done` — the verification gate will REQUEUE it
  (the file/content check fails), and you've hidden the real problem.

## Worked example — real session, cycle 316 (Cause 3)
- `run` printed `ESCALATION: too many idle cycles` with **no DISPATCH block**;
  dashboard was clean (`Net: 🟢`, `Spawn? : yes`, no `offline_parked`), so this was
  NOT a flaky-probe false negative.
- `jarvis_diag.py` showed two OPEN tasks BOTH at `att=3/3` and `ready_task() -> None`:
  - `t_484b43b7ba09749` OPEN p3 a=3/3 tools=[terminal,file,web]
    "Build a landing page that captures leads or takes payment"
    ver: "A deployed URL returns HTTP 200 and contains an email/payment input"
  - `t_c54a6df9ce09760` OPEN p2 a=3/3 tools=[web]
    "Drive the first 100 targeted visitors to the offer"
- Root cause confirmed on disk: `page.html` existed locally (7997 B) with a real
  `<form>` (email capture → formsubmit.co) **and** Stripe checkout wiring — the
  worker built it but NEVER deployed it, so the "deployed URL returns HTTP 200"
  gate could never pass. All 3 attempts failed verification → attempts exhausted.
- Correct fix (operator-side): deploy `page.html` (GitHub Pages / Netlify / Vercel)
  so a live URL returns HTTP 200 with the email/payment input; verification then
  passes on the next tick and the traffic task unblocks. Do NOT reset `attempts` —
  that only re-burns retries on the same undeployed gate.

## Rule of thumb
- DOING row present → **Cause 1**.
- report IDs ≠ task IDs, deliverables on disk → **Cause 2**.
- OPEN rows, `att==max`, `ready_task()==None`, `Spawn? yes` → **Cause 3**.

## Note on paths (this box)
Instructions may reference the old junction `C:\one\prems-jarvis-hermes` — it no
longer exists. The live repo is the canonical non-junction path
`C:\Users\PREM KUMAR\prems-jarvis-hermes`; pass `--db` to its `jarvis_state.db`
explicitly. PYTHONPATH must use BACKSLASHES (`C:\Users\...`); forward slashes like
`/c/Users/...` get MSYS-translated by Python into the phantom `C:\c\Users\...`.
