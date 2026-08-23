# Escalation-with-no-dispatch loop: orphaned worker reports

## Symptom
`python -m jarvis.cli --db <db> run` prints:

```
Spawn? : yes
NEXT ACTION: Escalating to operator: N cycles with no progress.
ESCALATION: too many idle cycles - operator input needed.
```

...but there is **no DISPATCH block**. The resource guard is clear (`Spawn? yes`),
Hermes 🔴 DOWN is the known false-negative (noise), and yet nothing is dispatched.

Meanwhile `tasks` shows rows stuck in DOING/OPEN, and real deliverables exist on disk
(`AppData/Local/Temp/spec.md` = "Product X / Price: $9"; `page.html` with
`<input type="email">` + a Stripe buy button).

## Root cause
Workers earlier ran and filed reports — but under **task IDs from a stale DB state**
that no longer match the live rows in `jarvis_state.db`. Concretely:

- Live rows: `t_8921464a…`, `t_484b43b7…`, `t_c54a6df9…`
- Log reports: `report PASS task=t_40f04d84bf10218 …`, `report PASS task=ing1 …`,
  `report REPORTED_FAIL task=ing2 …`

The report IDs ≠ live row IDs -> the verification gate never flips the live rows to
DONE. The planner's dedup then sees every sub_goal already covered (2 DOING + 1 OPEN),
so it has nothing *new* to dispatch, and the stuck-counter (which only resets on real
progress: dispatch or verified-DONE) never resets. Result: permanent escalation loop
even though the actual work is sitting finished on disk.

How it happens: a re-init / DB divergence (the `C:\one` junction stranding, a fresh
`init`, a re-clone) mints NEW task IDs while old worker reports for the SAME sub_goals
are still in `jarvis.log` under the OLD IDs. Status looks alive; dedup disagrees.

## Diagnose (3 commands, read-only)
```bat
SET "PYTHONPATH=C:\Users\PREM KUMAR\prems-jarvis-hermes"
SET "DB=C:\Users\PREM KUMAR\prems-jarvis-hermes\jarvis_state.db"
python -m jarvis.cli --db "%DB%" tasks
python -m jarvis.cli --db "%DB%" log | findstr report
python -m jarvis.cli --db "%DB%" run      :: confirm ESCALATION + no DISPATCH
```
If `tasks` IDs and `log | findstr report` IDs do NOT overlap -> orphaned reports confirmed.

## Fix (reconcile, do NOT re-dispatch)
1. For each live row whose deliverable already satisfies its `verify:` clause, file the
   report against the LIVE id:
   ```bat
   python -m jarvis.cli --db "%DB%" report t_8921464a… done "spec.md present with price: $9 (verified)"
   python -m jarvis.cli --db "%DB%" report t_484b43b7… done "page.html has email input + Stripe buy button (verify HTTP-200 after deploy)"
   ```
   Confirm the verification clause first — e.g. the landing-page task needs a DEPLOYED
   URL returning HTTP 200, so deploy `page.html` (or stand up a local server) before
   reporting it done, or the next tick's gate will requeue it.
2. The traffic task (`t_c54a…df9ce09760`, verify `>=100 unique visits`) has NO evidence
   -> leave it OPEN; the next tick will dispatch IT (it's the only genuinely-open gap once
   the others flip to DONE).
3. Re-run `run`; the stuck-counter resets on the verified-DONE transitions, escalation
   clears, and dispatch resumes on the real open task.

## Prevention
- Never `init` a DB that already has live task IDs if you can instead `report` the
  finished work against the existing IDs.
- After ANY DB reconstruction/re-clone, diff `tasks` IDs vs `log` report IDs before
  trusting the escalation signal.
- The escalation signal is a COUNTER, not a verdict — when deliverables exist on disk,
  treat ESCALATION as "state is out of sync", not "work is actually blocked".
