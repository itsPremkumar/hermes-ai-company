---
name: jarvis
description: >
  Build and operate a persistent goal-decomposition orchestrator ("Jarvis") that
  runs inside Hermes. The orchestrator (a long-running cron agent) checks a
  standing goal, decomposes the remaining gap into sub-goals, and spawns
  throwaway worker agents via the delegate_task tool — it never does the work
  itself. Covers the durable-state + verification-gate + resource-guard +
  escalation pattern, and the hard trap that delegate_task is an AGENT tool, not
  a Python API (so the core is a pure-Python decision engine; worker spawning
  happens in the Hermes cron agent that reads the Dispatch brief). Load whenever
  the user says "jarvis", "orchestrator", "run the CEO agent", "check the goal",
  or wants continuous autonomous progress toward an income/business goal.
---

# Jarvis — Persistent Goal-Decomposition Orchestrator (Hermes)

You build an autonomous *orchestrator*, not a do-everything agent. Jarvis loops
forever: evaluate goal → decompose gap → dispatch ≤N workers → verify → persist →
repeat. Workers are throwaway specialists spawned via `delegate_task`; they die
after reporting. State is durable (SQLite) so the loop survives crashes/reboots.

## The pattern (reusable — copy this for any autonomous agent system)
```
Jarvis (cron, every N min)          <- the ONLY long-running process
   |
   v  run_cycle()  (pure Python, stdlib only, no network)
   evaluate goal -> accomplished?
   decompose remaining gap -> next sub-goal (dedup-aware)
   dispatch <=1 worker (respect concurrency cap)
   |
   v  Hermes agent reads the Dispatch brief and calls delegate_task
   Worker (throwaway) executes, returns report
   |
   v  next tick: report ingested -> verification gate (file/HTTP/LLM)
   accept (DONE) | requeue (retry) | FAILED (attempts exhausted)
   |
   v  persist to SQLite, sleep, loop
```
Key invariants:
- **Orchestrator ≠ doer.** One giant agent overflows context and can't parallelize.
- **Workers ephemeral; state permanent.** Everything durable lives in the DB.
- **Verification gate.** DONE only when the `verification` check passes. No vibes.
- **Resource guard.** Block spawning when RAM/CPU too tight (low-RAM boxes OOM).
- **Escalation.** After K idle cycles, STOP and message the operator — don't burn tokens.

## CRITICAL: delegate_task is an AGENT tool, not a Python API
There is no `jarvis.spawn_worker()` SDK call. The runnable core is a **pure-Python
decision engine** (state + planner + dispatcher + verifier + monitor + cycle).
`run_cycle()` returns a `Dispatch` (the worker's self-contained brief) when a
worker is needed. A *Hermes cron agent* (Jarvis itself) reads that brief and calls
the `delegate_task` tool. This separation is what makes the core testable offline
and keeps the worker-spawn boundary explicit. Do NOT try to `import` delegate_task.

## Worker brief (the Dispatch contract)
```
task_id      : stable id (also the key for feeding the report back)
sub_goal     : the worker's single objective
verification : concrete, checkable "done" definition (file exists / HTTP 200 / marker)
context      : links, prior work, repo paths, the main goal for alignment
toolsets     : only what the worker needs (e.g. ["terminal","file","web"])
```
Feed the result back next tick as: `<task_id>|done|summary` or `<task_id>|failed|reason`.

## Reference implementation (CURRENT live path)
**Use a NON-junction path.** The working copy was corrupted by the Windows
junction `C:\one` → `C:\c\one`: it silently lost `.git` AND `jarvis/__init__.py`,
so `import jarvis` failed and `pytest` found 0 tests while `ls` still showed files.
The fix was to **re-clone from GitHub to a plain, junction-free path** and treat
that as canonical: `C:\Users\PREM KUMAR\prems-jarvis-hermes`.

To find the real path authoritatively when confused:
```python
python -c "import jarvis.cli, os; print(os.path.abspath(jarvis.cli.__file__))"
```
CLI (ALWAYS set PYTHONPATH first — `python -m` alone fails, see pitfalls):
`PYTHONPATH=C:\Users\PREM KUMAR\prems-jarvis-hermes python -m jarvis.cli {init,status,dashboard,run,report,tasks,log,selftest}`
Tests: `PYTHONPATH=C:\Users\PREM KUMAR\prems-jarvis-hermes python -m pytest -q` +
`python -m jarvis.cli selftest` (both must be green).
Repo on GitHub: `itsPremkumar/prems-jarvis-hermes`. If the local copy EVER looks
corrupted (missing `.git` / `jarvis/__init__.py`), **re-clone — do NOT debug the
junction copy.** This is the single most common way to lose a session's work here.

## Internet connectivity gate (resilience pattern)
Jarvis must survive the network dropping. Add a cheap **TCP probe** (no DNS/HTTP)
to the Monitor: `socket.create_connection(("8.8.8.8", 53), timeout=3)` → `online`.
In `run_cycle`, AFTER the resource guard, if `not online`:
- Only dispatch tasks whose `toolsets` are LOCAL (NOT web/browser/github/research/
  email/notion/airtable/mcp/youtube/maps).
- Park internet-dependent ready tasks: `idle=True`, `next_action="Offline:
  internet-dependent work paused; will resume on reconnect."`, log `offline_parked`.
- Do NOT fail workers (no retry spam, no progress loss). On the next cycle where
  `online=True`, dispatch resumes automatically.
Hermes itself needs the net to think/spawn workers, so offline = Jarvis keeps
state + ticks and waits. `JarvisWatchdog` (liveness) is local-only, so it still
works fully offline. The loop NEVER crashes on disconnect.

## Supervisor / self-healing layer (Jarvis is the BOSS of Hermes)
The earlier architecture had Jarvis as a passive guest inside Hermes. The
correct topology for 24/7: **Jarvis supervises Hermes, not the reverse.** But the
recovery chain terminates at the OS, because Hermes is the host and Jarvis runs
INSIDE it (as a cron guest). So:
- Jarvis CANNOT restart a dead Hermes. Only an **OS-level trigger** (Windows Task
  Scheduler on boot/logon) can relaunch the Hermes desktop app. This is by design.
- Therefore: run the orchestrator loop from BOTH a Hermes cron AND an
  OS-scheduled task (`supervise.py`), so the cycle survives Hermes being closed.
  Workers (which need `delegate_task`) only execute when Hermes is actually up.
- `jarvis/core/hermes_launcher.py` is Jarvis's tool to detect + launch Hermes
  (`ensure_hermes()` runs at the top of `run_cycle`, step 0a). It only LAUNCHES
  when no Hermes process exists — never aggressively kills a working session.
- Reboot survival = `jarvis install` registers 3 Task Scheduler tasks at THIS
  repo's canonical (non-junction) path: `JarvisBoot` (onlogon), `JarvisSupervise`
  (every 5 min, OS-level boss loop), `JarvisWatchdog` (every 10 min, external
  liveness — survives Hermes). Queue resumes from `jarvis_state.db` automatically.

### Self-healing primitives (jarvis/core/recovery.py)
- `retry(fn, max_attempts=0, base_delay, backoff=2, jitter=True)` — exponential
  backoff; `max_attempts<=0` = INFINITE retry (safe for critical infra); raises
  `PermanentError` to short-circuit, `TransientError` to keep retrying.
- `CircuitBreaker(threshold, cooldown)` — opens after N failures, half-opens after
  cooldown, closes on success. Use in front of any flaky external dependency.

### Crash guard (req 7/14)
`cli.py` installs `sys.excepthook` (logs unhandled exceptions to `jarvis.log`),
`signal.SIGINT`/`SIGTERM` handlers, and `atexit` — all log a graceful-shutdown
event. State is always preserved in SQLite, so a crash just means the next cycle
(or next scheduled task) continues. Unhandled exceptions NEVER terminate the
service permanently.

### Honest limits (do NOT fake these)
- True per-PROCESS isolation (req 11) would mean N OS processes on a 6 GB box →
  OOM. So Jarvis is ONE bounded process with failure-isolation *inside* the cycle.
- No software survives permanent hardware/power failure. That's the charter's
  own admission, not a gap to paper over.

## Pitfalls (all hit while building this for real — see references/)
- **Windows JUNCTION corrupts the repo (lost `.git` + `jarvis/__init__.py`).**
  The path `C:\one` is a junction to `C:\c\one`. Operating the project there led to
  a silently broken working copy (pytest found 0 tests, `import jarvis` failed,
  while `ls` still listed files). NEVER keep the live project under a junction.
  Clone to a plain path like `C:\Users\PREM KUMAR\prems-jarvis-hermes` and treat
  that as canonical. If the local copy looks corrupted, re-clone from GitHub —
  do NOT debug the junction copy. → references/msys_path_trap.md
- **`State.get_task()` returns a FRESH object each call.** Mutating one instance
  then re-fetching a different instance for `update_task` silently loses the
  mutation. Hold ONE reference: `t = db.get_task(id); t.x = ...; db.update_task(t)`.
- **Windows `os.path.exists` LIES on space-truncated paths (real bug, cost a cycle).**
  A verifier that splits a path at the first space (`tail.split()[0]`) turns
  `C:\Users\PREM KUMAR\...\spec.md` into `C:\Users\PREM`, and `os.path.exists(
  'C:/Users/PREM')` returns **True** on Windows — so the gate PASSES on a phantom
  file. NEVER split a path at whitespace. Instead, for `file exists at <path>
  with <clause>`, split path from the content clause at the FIRST keyword
  (`with`/`containing`/`contains`); a quoted path is also supported. See
  references/verifier_windows_gotchas.md.
- **Content-clause verification is real (OR/AND).** `file exists at spec.md with
  a price or offer` → verifier reads the FILE and applies boolean logic: `or`=any,
  `and`=all, `/`=any, stripping filler words (a/an/the). Test:
  test_verify_content_clause. A worker claiming `done` without the content still
  gets REQUEUED, not DONE.
- **Stray `./nul` file breaks `git commit` (MSYS `cmd //c`).** Using
  `cmd //c "..." >nul 2>&1` can drop a literal `nul` file in cwd; git then fails
  with "short read while indexing nul / failed to insert into database". Fix:
  `rm -f ./nul` before `git add`; prefer `> /dev/null 2>&1` or no redirect.
- **`schtasks` with spaces in the path MUST use list-args, not `shell=True`.**
  The user path `C:\Users\PREM KUMAR\...` contains a space. Building the command
  as a string and running `subprocess.run(cmd, shell=True)` makes Windows split
  `python.exe C:\Users\PREM` at the space → `ERROR: Invalid argument/option -
  'KUMAR\...'`. FIX: call `subprocess.run(["schtasks","/create","/tn",name,
  "/tr", fully_quoted_cmd, "/f", "/sc","minute","/mo","5","/rl","HIGHEST"],
  capture_output=True)` with NO shell. `spec["cmd"]` should already be a fully
  quoted string `"<py>" "<script>" "<db>"`. See references/supervisor_windows_service.md.
- **`install` must register tasks at the canonical NON-junction path.** Earlier
  the scheduled tasks pointed at `C:\one\prems-jarvis-hermes` (the corrupted
  junction copy) and silently died on reboot ("The system cannot find the file
  specified"). `jarvis/install.py` resolves `REPO = dirname(dirname(__file__))` at
  install time, so it always registers the real path. If a task ever errors,
  re-run `python -m jarvis.cli install` from the canonical path.
- **Resource guard MUST NOT hard-block on a low-RAM box — a hard-block was the actual breakage, not "correct".** The original 400 MB floor (`min_free_ram_mb=400`) is unreachable on the 6 GB box (free RAM normally ~100-300 MB), so `monitor.can_spawn()` was ALWAYS False → no worker ever dispatched → tasks stuck in `doing` forever → endless `ESCALATION: N cycles with no progress`. THE FIX (shipped, commit 98e01ca): floor lowered to `64`, CPU ceiling to `95`, and `can_spawn()` now WARN-and-PROCEED unless critically starved (`free < max(16, floor//4)` or `cpu > 98`). If you EVER see `Spawn? NO` with >100 MB free, the floor is mis-tuned — FIX IT, do NOT treat it as "correct". Unit tests still inject a permissive `Monitor(min_free_ram_mb=0, max_cpu_percent=100)` for determinism; never assert "dispatched" against live RAM.
- **`pytest` crashes before running a single test (langsmith plugin).** On this box `langsmith` 0.7.4's `pytest11` plugin (`langsmith_plugin`) imports `pydantic`, but the env has `pydantic 2.12.5` vs `pydantic-core 2.46.4` → `SystemError: pydantic-core version ... incompatible` on pytest startup, so `python -m pytest` dies before collecting (looks like "no tests"). The repo fix is `pytest.ini` with `addopts = -p no:langsmith_plugin`; ALWAYS run `python -m pytest -q` from the repo root so the ini is found → 35 passed. One-shot manual workaround: `python -m pytest -q -p no:langsmith_plugin tests/`. See `references/pytest_langsmith_trap.md`.
- **Tasks wedged in `doing` with no timeout = permanent stall.** A worker dispatched but never reported leaves its task in `doing` forever. The planner dedups on `(OPEN|DOING)` sub_goal text, so a wedged `doing` task blocks BOTH re-dispatch AND completion → infinite escalation. THE FIX (shipped, commit 98e01ca): `cycle._recover_stale_doing()` resets any `doing` task not updated within `Defaults.stale_doing_minutes` (90) back to `open`, releasing the dedup so it re-dispatches next tick. Diagnose with `jarvis.cli tasks` (look for `doing` rows with old `updated_at`); confirm via `jarvis.log` `event=recover`. DISTINCT from `escalation_orphaned_reports.md` (worker REPORTS under STALE task IDs). See `references/stale_doing_recovery.md`.
- **`Hermes : 🔴 DOWN` in the dashboard is a FALSE NEGATIVE when you are running as a
  Hermes cron.** The supervisor's process probe doesn't recognize its own cron host,
  so it reports Hermes down even while the tick is literally executing inside Hermes.
  It does NOT block dispatch (the cycle runs and the guard can still clear). Treat it
  as noise unless a separate OS-level check confirms Hermes is truly dead.
- **Stuck-counter must reset only on REAL progress** (dispatch or verified), NOT
  on task *creation* — creating a task isn't progress, or escalation never fires.
- **Large write_file calls time out.** Break file writes into <~8K-token chunks.
- **`python -m jarvis.cli` fails with "No module named jarvis.cli" unless PYTHONPATH is set.** The Hermes interpreter's `sys.path[0]` is the Hermes *agent* dir, NOT the project root, so `cd`-ing into the project and running `python -m jarvis.cli` does NOT find the package. Always `export PYTHONPATH=C:\Users\PREM KUMAR\prems-jarvis-hermes` (the canonical, non-junction path) before ANY `python -m jarvis.cli ...` or `python -m pytest` call. `cd` alone is insufficient.
- **MSYS shell tools and Python disagree on `/c/one`.** `ls`/`find`/`cat` (MSYS) treat `/c/one` as `C:\\one` (a junction that corrupted the repo — see above). Python treats `/c/one` as `C:\\c\\one` (also a junction copy). Both are unreliable for this project. Always use the canonical non-junction path `C:\\Users\\PREM KUMAR\\prems-jarvis-hermes` (or the `python -c "import jarvis.cli,os; print(os.path.abspath(jarvis.cli.__file__))"` probe) as the source of truth.
- **Default `--db` lands ON THE JUNCTION when the shell's cwd is under `C:\one`.** The cron/Hermes shell often starts in `/c/one/paperclip-company/...`. Running `python -m jarvis.cli init`/`run` WITHOUT an explicit `--db` resolves the default relative `jarvis_state.db` into that junction dir (e.g. `C:\one\paperclip-company\jarvis_state.db`), silently stranding state away from the canonical DB and violating the "never use the junction" rule. ALWAYS pass `--db "C:\Users\PREM KUMAR\prems-jarvis-hermes\jarvis_state.db"` explicitly on EVERY invocation. After `init`/`run`, READ the `State DB ready at ...` / `jarvis_state.db` line the CLI prints: if it shows a `C:\one\...` path you just created a JUNK DB — `rm -f` it and re-run with the explicit `--db` against the canonical path. Splitting state across two DBs is exactly how a session loses its tasks/goal.
- **Running a tick (operational):** each `run` cycle dispatches AT MOST ONE worker and resets the stuck-counter on dispatch (real progress). A separate Jarvis cron may also tick — the cycle counter can jump by >1 between your calls; the planner's dedup (it skips any sub_goal already OPEN/DOING) makes this SAFE, so never manually re-dispatch an in-flight task. Spawn only the task named in the DISPATCH block via `delegate_task`, then stop — the next scheduled tick ingests the worker's `<task_id>|done|summary` report. See `references/cron_tick_procedure.md`.
- **`--db` is a PARENT arg and MUST precede the subcommand.** `python -m jarvis.cli --db "C:\Users\PREM KUMAR\prems-jarvis-hermes\jarvis_state.db" status` works. `python -m jarvis.cli status --db "..."` FAILS with `error: unrecognized arguments: --db ...` AND runs ZERO logic — you get the usage banner, not your command, so it looks like the DB is empty/unknown. Always put `--db` immediately after `jarvis.cli` and BEFORE the verb.
- **ESCALATION with no DISPATCH but deliverables present = orphaned worker reports.** If `run` prints `ESCALATION: too many idle cycles` and NO dispatch block, yet `tasks` shows rows stuck in DOING/OPEN AND real files exist (e.g. `spec.md` = "Product X / Price: $9", `page.html` with `<input type=email>` + a Stripe buy button), the cause is almost always: earlier workers filed `<task_id>|done|summary` reports under task IDs from a STALE DB state that no longer match the live rows. Dedup then sees every sub_goal already covered (nothing new dispatches) while the live rows never flip to DONE, so the stuck-counter never resets → permanent escalation loop. DIAGNOSE: cross-check `python -m jarvis.cli --db <db> tasks` IDs against `python -m jarvis.cli --db <db> log | grep report` IDs. If they differ, RECONCILE: `report <live_task_id> done "<summary>"` for each verified deliverable (confirm the verification clause first — e.g. deploy `page.html` so the HTTP-200 check can pass), then the next tick drives the genuinely-open task (traffic). See `references/escalation_orphaned_reports.md`.
 - **OPEN tasks with `attempts >= max_attempts` = SILENT escalation deadlock (3rd cause, distinct from orphaned reports).** If `run` escalates with NO dispatch, `Spawn? : yes`, and `tasks` shows OPEN rows, do NOT assume orphaned reports — check attempt counters. A task dispatched `max_attempts` times that *failed verification each time* (classic: landing page built locally but NEVER deployed, so the "deployed URL returns HTTP 200" gate can't pass) is left OPEN with `attempts == max_attempts`. `dispatcher.ready_task()` filters `t.attempts < t.max_attempts`, so it is skipped forever → nothing dispatches → stuck counter climbs → PERMANENT ESCALATION. DIAGNOSE FAST with `python scripts/jarvis_diag.py <db>` (prints each task's status/priority/attempts/max/toolsets + the live `ready_task()` result). Fix is OPERATOR-side: remove the real blocker (e.g. provide a deploy target so the verification clause can pass) — do NOT just reset `attempts`/`max_attempts`, which re-burns retries on the same failing gate. Full decision tree: `references/escalation_triage.md`.

 - **The connectivity probe is FLaky — a single timeout manufactures a FALSE ESCALATION.** `monitor.online()` does ONE `socket.create_connection(("8.8.8.8",53),timeout=3)`; if that one probe transiently times out, `run_cycle` parks tasks as "Offline" even though the network is up, and `offline_parked` calls `_bump_stuck` — so spurious parks inflate the stuck counter and can page the operator for "N cycles with no progress" with NO real outage. SYMPTOM: dashboard shows `Net: 🟢` / `Spawn? : yes` but `NEXT ACTION` says `Offline: internet-dependent work paused` — that contradiction means the probe flaked. DIAGNOSE with a direct shell probe; if it's ONLINE, re-run `run` (planner dedups on OPEN|DOING, so safe) to get a clean reading. If you own the code: retry-with-jitter in `online()`, or only treat offline after N consecutive failures, and don't bump the stuck counter on a single parked cycle. Full detail + fix: `references/connectivity_gate.md` (Flaky probe false-negative).

 ## references/ (session-specific detail)
- `references/msys_path_trap.md` — the `/c/one` ↔ `C:\\c\\one` MSYS symlink gotcha
  and the exact workaround that cost a debugging cycle.
- `references/orchestrator_pattern.md` — expanded architecture, Dispatch contract,
  and the verification/escalation state machine.
- `references/cron_tick_procedure.md` — exact commands to run one Jarvis tick on this
  box (PYTHONPATH + correct path), plus how to feed a worker report back.
- `references/escalation_orphaned_reports.md` — diagnosing the escalation-with-no-dispatch
  loop caused by worker REPORTS filed under stale task IDs (dedup blocks re-dispatch,
  stuck-counter never resets).
- `references/stale_doing_recovery.md` — diagnosing tasks wedged forever in `doing`
  (worker dispatched but never reported) and the `stale_doing_minutes` recovery that
  resets them to `open`. New this session.
- `references/pytest_langsmith_trap.md` — `pytest` crashes on import via the `langsmith`
  plugin (pydantic/pydantic-core mismatch); fix is `pytest.ini` `addopts = -p no:langsmith_plugin`.
  New this session.
- `references/verifier_windows_gotchas.md` — `os.path.exists` phantom-path bug,
  content-clause (OR/AND) verification, and the stray `./nul` git blocker.
- `references/connectivity_gate.md` — offline -> park internet tasks -> auto-resume
  (TCP probe + `_needs_network` toolset set + `offline_parked` log).
- `references/supervisor_windows_service.md` — Jarvis supervises Hermes (OS is the
  real recovery point); `install` registers 3 schtasks; the `schtasks` space-in-path
  quoting bug + list-args fix. New this session.
- `references/escalation_triage.md` — decision tree for `ESCALATION` with NO dispatch:
  the THREE distinct causes (wedged DOING / orphaned reports / exhausted attempts),
  exactly how to tell them apart, and the correct fix for each. New this session.

## scripts/ (re-runnable diagnostics — invoke directly, do not hand-type)
- `scripts/jarvis_diag.py` — instant escalation triage: dumps every task's
  status/priority/attempts/max_attempts/toolsets from `jarvis_state.db` and prints
  the live `Dispatcher.ready_task()` result, so you see in one shot whether the
  blocker is wedged DOING, exhausted attempts, or a report-ID mismatch. Run:
  `PYTHONPATH=<canonical> python <skill_dir>/scripts/jarvis_diag.py <jarvis_state.db>`.
  REGRESSION GUARD: the module docstring is raw (`r"""`) and the usage example uses
  forward slashes — a `C:\Users\...` path inside a plain (non-raw) string raises
  `unicodeescape` at import time, so keep it raw / forward-slashed when editing.

## templates/ (starter files to copy + modify)
- `templates/minimal_orchestrator.py` — a known-good minimal cycle skeleton
  (state + decompose + dispatch + verify) you can reproduce with modifications.

## Verify before declaring done
For any orchestrator you build: run the test suite AND a structural selftest, drive
at least one full cycle, and confirm the dedupe + verification gate + resource guard
all fire. Unverified "it should work" is a failure for this user.
