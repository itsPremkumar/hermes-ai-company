# Running one Jarvis tick on this box (operational procedure)

Captured from a real cron tick. The two traps below cost a debugging cycle each
and are NOT covered by the generic MSYS note: (a) the real project lives at
`C:\c\one\...` not `C:\one\...`; (b) `python -m jarvis.cli` needs `PYTHONPATH`.

## 1. Locate the real path (authoritative)
```bash
cd /c/c/one/prems-jarvis-hermes
python -c "import jarvis.cli, os; print(os.path.abspath(jarvis.cli.__file__))"
# -> C:\c\one\prems-jarvis-hermes\jarvis\cli.py   (if wrong, you're in the phantom)
```
If the probe returns `C:\one\...` you are in the STALE PHANTOM — stop and use `/c/c/one/...`.

## 2. Set PYTHONPATH once per shell
```bash
export PYTHONPATH=/c/c/one/prems-jarvis-hermes
cd /c/c/one/prems-jarvis-hermes
```
Without this, `python -m jarvis.cli status` errors with `No module named jarvis.cli`
because the Hermes interpreter's `sys.path[0]` is the agent dir, not the project root.

## 3. Read state
```bash
python -m jarvis.cli status       # goal + open/done/failed + cycle
python -m jarvis.cli dashboard    # always-visible dashboard (incl. RAM/CPU + Spawn?)
python -m jarvis.cli tasks        # list every task + its verification string
```

## 4. Run exactly one cycle
```bash
python -m jarvis.cli run
```
`run` prints the dashboard, a `NEXT ACTION` line, and — if a worker is needed — a
`DISPATCH` block with `task_id / sub_goal / verification / toolsets / context`.
- If `Spawn? : NO (guard)` appears, the RAM/CPU guard is tripping (correct
  behavior, e.g. <400 MB free). Do NOT force-dispatch. Re-run next tick.
- A DISPATCH means a worker must be spawned via the `delegate_task` AGENT tool
  (NOT from Python). Use `sub_goal` as the goal, and `verification + goal +
  context` as context, with the listed `toolsets`. Prefer `role='leaf'`.

## 5. Feed the worker report back (next tick)
When the worker finishes, the next scheduled `run` (or an explicit `report`) ingests it:
```bash
# form: <task_id>|done|summary   or   <task_id>|failed|reason
python -m jarvis.cli report t_484b43b7ba03602 done "Deployed https://x.example -> 200 + email input"
```
The verification gate then flips the task to `done` (PASS) or back to `open` (RETRY),
or `failed` if `attempts` is exhausted.

## 6. Caveats observed in production
- Another Jarvis cron may tick concurrently: the cycle counter can jump by >1
  between your calls. The planner dedups on sub_goal (OPEN/DOING), so two ticks
  never recreate the same in-flight task. Safe — do not manually re-dispatch.
- Respect the worker cap (default 3). Per tick, spawn ONLY the one task in the
  DISPATCH block; leave `[open]` tasks for a future tick / free slot.
- Tests: `python -m pytest -q` and `python -m jarvis.cli selftest` must both be green.
