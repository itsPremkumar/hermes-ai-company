# Windows operations gotchas (learned the hard way this session)

## Kill a process listening on a port (git-bash / MSYS)
`taskkill` with `//` DOUBLE slash is mangled by MSYS -> "Invalid argument".
Use SINGLE slash:
```
taskkill /PID 13976 /F
# or via cmd:
cmd //c "taskkill /PID 13976 /F"
```
Loop by listening port:
```
for p in $(netstat -ano 2>/dev/null | grep ':17498' | grep LISTENING | awk '{print $5}'); do taskkill /PID "$p" /F; done
```

## Zombie supervisor keeps respawning the child
A supervisor (run_server.py) restarts its child on exit. Killing only the child
PID lets it respawn with OLD code -> you test stale behavior. Find the
supervisor and kill it too:
```
wmic process where "CommandLine like '%run_server%' or CommandLine like '%free_llm_router.server%'" get ProcessId
# then taskkill each PID
```

## Startup autostart (no console pop on login)
1. `autostart.bat` launches `run_server.py` (supervisor, 24/7).
2. `make_startup_shortcut.vbs` creates `free-llm-router.lnk` in:
   `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`
   with `WindowStyle = 7` (minimized).
3. **VBS bug**: `WScript.Echo link.Path` throws
   "Object doesn't support this property or method: 'path'".
   The `.lnk` is still created fine. Use `link.FullName` if you must print,
   or just don't echo. Verify with:
   `ls "$APPDATA/Microsoft/Windows/Start Menu/Programs/Startup" | grep -i free-llm-router`

## Python to use
`C:\Users\PREM KUMAR\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`
(aiohttp already installed there). Set `PYTHONIOENCODING=utf-8` in the .bat.

## Health endpoint is slow
`GET /health` live-probes all providers (~30s). Curl timeout must be >=60s or
you'll misread it as down. Chat calls are 5-40s.
