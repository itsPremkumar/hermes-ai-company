# Supervisor + Windows service layer (Jarvis = boss of Hermes, survives reboot)

## The layering trap (most important lesson)
The "Agent OS" diagrams that put Jarvis ABOVE Hermes and have Jarvis restart
Hermes are INVERTED on this box. Reality:
```
Windows (Task Scheduler / startup)  ->  launches Hermes desktop app
Hermes (cron engine)                ->  runs Jarvis every 30m  ->  spawns workers
Jarvis (guest)                      ->  plans / dispatches / verifies / persists
```
If Hermes closes, the cron dies with it. **Jarvis cannot revive Hermes** — only
an OS trigger can. So the recovery chain MUST terminate at the OS, not at Jarvis.
Do NOT build a "watchdog that restarts Hermes from inside Hermes" — it can't run
when Hermes is down. The external `JarvisWatchdog` only *detects* the gap; the
`JarvisBoot`/`JarvisSupervise` Task Scheduler tasks are what actually resume work.

## Hermes location (discovered via wmic)
Desktop app: `C:\Users\PREM KUMAR\AppData\Local\hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe`
CLI fallback: `C:\Users\PREM KUMAR\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe`

## `jarvis/core/hermes_launcher.py`
- `hermes_running()` — `tasklist /FI "IMAGENAME eq Hermes.exe"` (subprocess, 10s timeout).
- `launch_hermes()` — `Popen([exe], creationflags=DETACHED_PROCESS|0x08000000)`;
  polls up to 10s; returns True if a process appears. Never kills a live session.
- `ensure_hermes()` — called at `run_cycle` step 0a; returns
  `{running, launched, action}`. Dashboard shows "Hermes: UP/DOWN/LAUNCHED".

## `install` command (reboot survival)
`python -m jarvis.cli install` runs `jarvis/install.py`, which registers 3 tasks:
- `JarvisBoot`      `/sc onlogon`            -> `supervise.py <db>`
- `JarvisSupervise` `/sc minute /mo 5`       -> `supervise.py <db>`  (OS boss loop)
- `JarvisWatchdog`  `/sc minute /mo 10`      -> `watchdog.py --db <db> --max-age-min 40`
All run as current user, `/rl HIGHEST`, `/f` overwrite. `uninstall` deletes them.

### THE schtasks quoting bug (cost a real cycle)
The path `C:\Users\PREM KUMAR\...` has a SPACE. Building the schtasks command as
a string and running `subprocess.run(cmd, shell=True)` makes Windows split at the
space:
```
ERROR: Invalid argument/option - 'KUMAR\AppData\Local\...'
```
FIX — build as a LIST, no shell:
```python
cmd = ["schtasks", "/create", "/tn", name, "/tr", spec["cmd"], "/f"]
cmd += spec["trig"].split()          # ["/sc","minute","/mo","5"]
cmd += ["/rl", "HIGHEST"]
subprocess.run(cmd, capture_output=True, text=True, timeout=30)
```
where `spec["cmd"]` is ALREADY fully quoted:
`"C:\Users\PREM KUMAR\AppData\...\python.exe" "C:\Users\PREM KUMAR\prems-jarvis-hermes\supervise.py" "C:\Users\PREM KUMAR\prems-jarvis-hermes\jarvis_state.db"`

## `supervise.py` (the OS boss loop)
Runs OUTSIDE Hermes every 5 min. Steps: run one `run_cycle`; render dashboard; if
a worker was dispatched AND `hermes_running()`, print `SPAWN_WORKER:<json brief>`
for the Hermes cron/agent to spawn via `delegate_task`. This is the "Jarvis
commands Hermes to do the work" hand-off. Verified live: tasks show Status=Ready
and `supervise.py` runs a full cycle from the canonical path.

## Verify reboot survival
1. `python -m jarvis.cli init`
2. `python -m jarvis.cli install`
3. `schtasks /query /tn JarvisSupervise /fo LIST` -> Status: Ready
4. `python supervise.py jarvis_state.db` -> dashboard prints, no crash
5. State persists across the scheduled runs; queue resumes automatically.
