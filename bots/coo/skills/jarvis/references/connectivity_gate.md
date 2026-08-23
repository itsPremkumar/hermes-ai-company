# Internet connectivity gate (offline -> park -> resume)

## Why
Jarvis must survive the network dropping. Without an explicit gate, a worker
that needs the internet just fails its `verification`, gets requeued, burns
`max_attempts`, then flips to FAILED — wasting cycles and losing the task
position. The fix: detect offline early and PAUSE internet-dependent work.

## Monitor probe (cheap, no DNS/HTTP)
```python
def online(self, host="8.8.8.8", timeout=3.0) -> bool:
    import socket
    try:
        socket.setdefaulttimeout(timeout)
        sock = socket.create_connection((host, 53), timeout=timeout)
        sock.close()
        return True
    except OSError:
        return False

def health(self) -> dict:
    h = {...}  # ram/cpu
    h["online"] = self.online()
    return h
```

## run_cycle gate (after the RAM/CPU resource guard)
```python
online = monitor.health().get("online", True)
report.online = online
if not online:
    ready = dispatcher.ready_task()
    if ready is not None and not _needs_network(ready):
        report.dispatched = dispatcher.dispatch(ready)   # local-only work runs
        report.next_action = f"Offline: dispatched LOCAL worker for: {ready.sub_goal}"
        _reset_stuck(state)
        return report
    report.next_action = "Offline: internet-dependent work paused; will resume on reconnect."
    report.idle = True
    report.stuck_cycles = _bump_stuck(state)
    log_event(event="cycle", status="offline_parked", cycle=cycle, detail=report.next_action)
    return report
```

## Network toolset set (park these when offline)
```python
_NET_TOOLSETS = {"web","browser","github","research","maps","youtube",
                 "email","notion","airtable","mcp"}

def _needs_network(task) -> bool:
    return any(t in _NET_TOOLSETS for t in (getattr(task,"toolsets",None) or []))
```

## Behavior verified live
- Offline -> `idle=True`, `dispatched=None`, log `offline_parked`, no worker spawned.
- Reconnect -> next cycle `online=True` -> normal dispatch resumes automatically.
- `JarvisWatchdog` (liveness) is local-only, so it keeps reporting healthy offline.
- The loop NEVER raises on disconnect.

## Test
`test_run_cycle_offline_parks_internet_tasks` injects `_OfflineMonitor` (health
returns `online=False`) and asserts idle + paused + no dispatch.

## Flaky probe false-negative (caught live, cycles #262/#264)
The single `online()` probe is NOT robust. In a live run the dashboard probe
returned `Net: 🟢` (online=True) while `run_cycle`'s *separate, fresh* probe
returned False a moment later, so the cycle printed `NEXT ACTION: Offline:
internet-dependent work paused` and parked the tasks — even though the network
was genuinely up (a direct `socket.create_connection(("8.8.8.8",53))` from the
shell succeeded 3/3 times). A single transient timeout on 8.8.8.8:53 is enough
to flip the decision.

WHY IT MATTERS: `offline_parked` calls `_bump_stuck(state)` — spurious parks
INFLATE the stuck counter and can MANUFACTURE a false ESCALATION (the operator
gets paged for "N cycles with no progress" when the only problem was a flaky
probe). In the incident, cycles 262 and 264 parked offline spuriously and helped
drive the stuck counter to 67 -> real ESCALATION, masking the actual blocker
(exhausted attempts on the landing-page task).

SYMPTOM: dashboard says `Net: 🟢` / `Spawn? : yes` but `NEXT ACTION` is
`Offline: internet-dependent work paused`. That contradiction = the probe flaked.

DIAGNOSE: run a direct probe from the shell:
    python -c "import socket; socket.create_connection(('8.8.8.8',53),timeout=3); print('ONLINE')"
If it prints ONLINE, the park was a false negative — re-run `run` (the planner
dedups on OPEN|DOING, so a re-run is safe, not a double-dispatch) to get a clean
online reading; dispatch then resumes.

FIX (if you own the code): make `online()` retry with jitter, or only treat the
host as offline after N consecutive failed probes; consider a second host
(e.g. 1.1.1.1) so one flaky resolver can't decide. Also consider NOT bumping the
stuck counter on `offline_parked` (or only after a sustained outage), so
connectivity blips can't drive escalation.
