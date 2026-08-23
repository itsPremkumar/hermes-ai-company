---
name: windows-box-maintenance
description: Diagnose and fix a RAM-starved / disk-full Windows laptop (the user's dev box is ~6 GB RAM, often <400 MB free, 280+ procs). Covers safe disk cleanup (caches/temp/junk), RAM triage (kill non-essential without harming Hermes/video project), and fixing "speakers not working / audio not clear" caused by virtual-audio-device hijacking (Nahimic/AudioRelay/NVIDIA).
---

# Windows Box Maintenance (low-spec laptop)

User's box: Windows 10/11, ~5.86 GB visible RAM (8 GB shared with GPU), often
<400 MB free, 280+ processes. Protect at all costs: Hermes (Hermes.exe +
python.exe hermes_cli.main serve), Automated-Video-Generator, voicebox repo,
Hermes-Full-Autonomous-Company / paperclip-* / clawhub-repos (company infra).

## Pitfall: MSYS/bash quoting on this Windows host
- `/c/one/Sproutern` paths: use `"/c/one/Sproutern"` (forward slash, quoted).
- `taskkill` flags: `taskkill /PID 1234 /F` (single slash). `//PID` gets mangled
  by MSYS and silently fails ("already gone"). `cmd //c "taskkill /PID x /F"` opens
  an interactive shell instead of running — do NOT use that form.
- `du -sh` on a huge tree TIMES OUT (60s). Use a Python `os.scandir` recursive
  size function (see scripts/size_scan.py pattern) or `robocopy /L` (but MSYS
  quoting breaks robocopy). Python script file is most reliable.
- PowerShell `-Command` with `$_` inside heredoc/quotes: escape as `` `$_ ``
  or write a `.ps1` file and run `powershell -ExecutionPolicy Bypass -File x.ps1`.
- Registry `Get-ItemProperty` on Uninstall keys throws "Specified cast is invalid"
  for some values — use `winreg` in Python instead (see audio fix).

## Pitfall: global PYTHONPATH leaks Hermes venv into EVERY python (CRITICAL for ML installs)
The shell injects a global `PYTHONPATH` pointing at Hermes's venv
(`C:\Users\PREM KUMAR\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages`).
Effect: `sys.path` of ANY python (even a `uv`-created venv) prepends Hermes's
site-packages, so `import huggingface_hub` resolves to Hermes's version (1.2.3),
`torch` resolves to Hermes's, model loads fail with version clashes, etc.
- **Fix:** run EVERY python/uv command with `env PYTHONPATH=` (empty) so the
  venv is the only source. Both backend launches AND `uv pip install` must be
  prefixed. Without it, installs "succeed" but the venv is shadowed.
- Verify isolation: `env PYTHONPATH= .venv/Scripts/python.exe -c "import sys;
  print([p for p in sys.path if 'hermes' in p])"` → must print `[]`.

## Pitfall: `python -m venv` is BROKEN here (base python IS the Hermes venv)
`python` on PATH = Hermes's venv python. `python -m venv .venv` creates a
non-isolated venv that still inherits Hermes's `pyvenv.cfg`/`site-packages`
(the PYTHONPATH leak above makes it worse). 
- **Fix:** use `uv venv --python 3.11 .venv` (uv downloads a standalone
  CPython, NOT the Hermes venv). Then install with `env PYTHONPATH= uv pip
  install --python .venv/Scripts/python.exe ...`.
- Check venv isolation: `env PYTHONPATH= .venv/Scripts/python.exe -c
  "import sys; print(sys.prefix)"` → must print your `.venv` path, NOT Hermes's.

## Pitfall: stale backend processes hold the port (silent failure)
A killed-but-not-reaped Voicebox/uvicorn backend keeps port 17493 bound, so new
launches fail with `OSError: [Errno 10048] ... address already in use` and the
NEW process dies — but your `/speak` calls hit the OLD (broken) process.
- **Fix:** before launching any server, free the port:
  `for pid in $(netstat -ano | grep ":17493" | grep LISTENING | awk '{print $5}' | sort -u); do taskkill /F /PID $pid; done`
- Watch for it: the "Traceback" watch-pattern on old backend launches fires
  repeatedly from DEAD processes — those are stale replays, not live failures.
  Always check `netstat` for who holds the port before debugging a "crash".

## Safe disk cleanup (recoverable space, ~70 GB found this session)
Biggest junk on this box was: User Temp (23.8 GB), uv cache (7.3 GB), pip cache
(4.2 GB), Chrome cache, Windows Update SoftwareDistribution\Download, Flutter pub
cache (687 MB), dead repos (sproutern 6.2 GB), stale game registry entry.
- Safe to `rm -rf` (re-download on demand): `%LOCALAPPDATA%\Temp\*`,
  `%APPDATA%\Roaming\pip`, `%LOCALAPPDATA%\uv\cache`,
  `C:\Windows\SoftwareDistribution\Download\*`, Chrome `User Data\Default\Cache`.
- HuggingFace hub (`~/.cache/huggingface/hub`) = SAFE to delete but holds
  Qwen3-TTS (the recommended clone engine) — keep unless desperate.
- Chrome FULL profile (`User Data`) = logs you out of all sites; only clear Cache.
- Android/Flutter dev: `~/.gradle` and `~/.android/avd` grow huge; AVD images are
  1-4 GB each. Keep Android SDK if starting dev (re-download wastes bandwidth).
- Stale "Installed apps" entry (e.g. Euro Truck Sim 2 showing 26.7 GB but folder
  already deleted): delete the registry key under
  `HKLM\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\`
  via Python `winreg.DeleteKey`.

## RAM triage (immediate relief)

### Quick memory diagnostic (run this first)
Use a `.ps1` file to avoid MSYS quoting hell with PowerShell:
```powershell
# Write to a .ps1 file, then run via bash:
# powershell -NoProfile -ExecutionPolicy Bypass -File ramcheck.ps1
$os = Get-CimInstance Win32_OperatingSystem
Write-Host "Total: $([math]::Round($os.TotalVisibleMemorySize/1024, 1)) GB"
Write-Host "Free:  $([math]::Round($os.FreePhysicalMemory/1024, 1)) GB"
Write-Host "Used:  $([math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/1024, 1)) GB"
Get-Process | Sort-Object WorkingSet64 -Descending |
    Select-Object -First 40 Name,
        @{N='MB';E={[math]::Round($_.WorkingSet64/1MB, 1)}},
        Company | Format-Table -AutoSize
```

For free RAM only: `wmic OS get FreePhysicalMemory /Value` → KB value, divide by 1024 for MB.

### WSL VM — the #1 hidden RAM hog (429+ MB)
Even when Docker Desktop is "stopped" or "not running", the WSL
VM (`vmmemWSL`) holds **~429 MB** of RAM. This is the single biggest
reclaimable chunk on a 6GB machine after Hermes itself.

Check: `wsl --list --verbose` (if "Running" → eating RAM)
Kill:  `wsl --shutdown`
Caveat: If Docker Desktop is still installed, a scheduled task or service
may restart WSL. For permanent removal, uninstall Docker Desktop + run
`wsl --unregister <distro>` for each distro.

### Imported WSL distros (e.g. docker-desktop-data)
`docker-desktop` and `docker-desktop-data` are "imported by flag" distros
that `wsl --list --verbose` shows but which do NOT appear in
`wsl --list` (the default list). They still eat ~30 MB even when "Stopped".
Remove them by GUID or by verifying the registry under
`HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss` after WSL shutdown.

### AMD Radeon Software — bloat on NVIDIA machines (273 MB)
If the laptop has an NVIDIA GPU (e.g. GTX 1650) but AMD Radeon Software
is also installed (common with AMD Ryzen + NVIDIA dGPU combos), the AMD
software suite runs 3 processes consuming ~273 MB:
- `AMDRSSrcExt.exe` (~128 MB)
- `AMDRSServ.exe` (~84 MB)
- `RadeonSoftware.exe` (~62 MB)

These are safe to kill/disable if NVIDIA is the primary GPU.

**Full removal (NVIDIA-primary machines only):**
AMD Radeon Software ships as both an AppX (Windows Store) package and a
Win32 service. Remove all layers:

```powershell
# 1. Remove AppX package (the actual software)
Get-AppxPackage -Name "*AMD*Radeon*" | Remove-AppxPackage

# 2. Kill running processes immediately
taskkill /f /im AMDRSSrcExt.exe
taskkill /f /im AMDRSServ.exe
taskkill /f /im RadeonSoftware.exe

# 3. Set AMD services to Manual (NOT Disabled — integrated GPU may need them)
Get-Service "AMD Crash Defender Service" -ErrorAction SilentlyContinue | Set-Service -StartupType Manual
Get-Service "AMD External Events Utility" -ErrorAction SilentlyContinue | Set-Service -StartupType Manual
```

⚠️ **Important:** On AMD Ryzen + NVIDIA dGPU laptops, the integrated AMD GPU
still drives the display panel. Setting services to **Manual** (not Disabled)
lets them start on demand if the driver needs them, without running always.

### Top memory hogs to kill (non-essential)
| Process | Typical RAM | Notes |
|---------|-----------:|-------|
| vmmemWSL | ~429 MB | WSL VM. Kill: `wsl --shutdown` |
| AMDRSSrcExt + AMDRSServ + RadeonSoftware | ~273 MB (3 procs) | AMD GPU control panel — safe if using NVIDIA |
| wps.exe (x2) | ~105 MB | WPS Office — safe to kill |
| wpscenter.exe | ~47 MB | WPS Center — safe |
| wpscloudsvr.exe | ~17 MB | WPS cloud sync |
| promecefpluginhost.exe (x2) | ~79 MB | WPS Chrome Embedded Framework — safe |
| AnyDesk.exe | ~43 MB | Remote desktop — safe if not in use |
| LenovoVantageService | ~46 MB | OEM bloat — safe to disable |
| ms-teamsupdate | ~33 MB | Teams update leftover — safe after Teams uninstalled |
| vmwp | ~31 MB | VMware VM worker — safe if no VMs running |
| PhoneExperienceHost | ~133 MB | Phone Link — safe but system-managed |
| TextInputHost.exe | ~144 MB | Touch keyboard — safe but system-managed |
| SearchHost.exe | ~77 MB | Windows Search — safe but system-managed |
| NVDisplay.Container + nvcontainer | ~56 MB (2 procs) | NVIDIA — keep (driver needs it) |

Kill: `taskkill /F /IM wps.exe /IM wpscenter.exe /IM promecefpluginhost.exe /IM AnyDesk.exe /IM AMDRSSrcExt.exe /IM AMDRSServ.exe`

The dominant cost is often Hermes itself (~1 GB). Cannot free without
stopping Hermes. For heavy video jobs, pause Hermes during the run.

## Bloatware uninstall (reclaim RAM permanently)

After killing processes and disabling startups, the final step is **uninstalling**
non-essential apps entirely. Many consumer apps install "per-user" in
`%LOCALAPPDATA%\\Programs\\` or `%LOCALAPPDATA%\\Kingsoft\\` and leave 50-250 MB
running in background even when idle.

For the complete systematic workflow (step-by-step for every installer type),
see `references/app-removal-workflow.md`.

### Finding uninstallers

The registry is the authoritative source — but `Get-ItemProperty` on Uninstall
keys throws "Specified cast is not valid" on some entries. Use try/catch:

```powershell
$paths = @(
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall"
)
$filters = @("Proton","WPS","Kingsoft","Canva","Figma","Teams","Edge")
foreach ($base in $paths) {
    $keys = Get-ChildItem $base -ErrorAction SilentlyContinue
    foreach ($key in $keys) {
        try {
            $props = Get-ItemProperty $key.PSPath -ErrorAction Stop
            if ($props.DisplayName) {
                foreach ($f in $filters) {
                    if ($props.DisplayName -match $f) { Write-Host "$($props.DisplayName) → $($props.UninstallString)" }
                }
            }
        } catch { }
    }
}
```

Also scan disk for uninstaller EXEs:
```powershell
Get-ChildItem "$env:LOCALAPPDATA\Kingsoft" -Recurse -Filter "unins*" | Select FullName
```

### Approaches by installer type

| Type | Silent flag | Fallback |
|------|-------------|----------|
| MSI (msiexec) | `/quiet /norestart` | — |
| Inno Setup | `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART` | — |
| NSIS | `/S` | — |
| AppX (Store) | `Remove-AppxPackage <PackageFullName>` | — |
| Per-user (AppData) | Try silent, else **delete the directory** | Safe for AppData installs |

### Common bloatware to uninstall

| App | RAM | How to uninstall | Gotchas |
|-----|:---:|------------------|---------|
| **WPS Office** | ~250 MB | `uninst.exe /VERYSILENT` or delete Kingsoft folder | Two versions possible (check `12.2.0.23155` + `12.2.0.23196`) + 3 scheduled tasks |
| **AMD Radeon Software** | ~273 MB (3 procs) | AppX: `Remove-AppxPackage -Name \"*AMD*Radeon*\"` + services: Set `AMDRSServ`,`AMD Crash Defender Service` to Manual | Safe to remove if NVIDIA is the primary GPU; set services to Manual, NOT Disabled |
| **Lenovo Vantage** | ~74 MB (2 procs) | Control Panel → Uninstall | OEM bloat — Windows manages drivers fine |
| **Docker Desktop** | ~535 MB | Control Panel → Uninstall, then `wsl --shutdown` + `wsl --unregister <distro>` | Even "Stopped" spawns WSL VM at ~429 MB |
| **Canva** | ~40 MB | `"Uninstall Canva.exe" /currentuser` | Leaves empty dir — safe to delete |
| **Figma Agent** | ~50 MB | `FigmaAgent\Uninstall.exe` | May hang on silent — taskkill the uninstaller afterwards |
| **Teams** (classic) | ~200 MB | `Update.exe --uninstall` | New Teams is separate AppX |
| **Proton VPN** | ~50 MB | Control Panel | Not in standard Uninstall registry |
| **AnyDesk** | ~43 MB | Control Panel | Easy kill target |
| **Microsoft Edge** | ~300+ MB | AppX + Win32: `Remove-AppxPackage Microsoft.MicrosoftEdge.Stable` + `setup.exe --uninstall --msedge --channel=stable --system-level` + `MicrosoftEdgeUpdate.exe /uninstall` | Deeply integrated — needs both paths |
| **Ollama** | ~200+ MB | Remove from `shell:startup` folder | Background LLM server |
| **Claude Desktop** | ~150 MB | Remove `HKCU:\\Run\\Claude` | Per-user install |
| **MiniMax Code** | ~50+ MB | Remove `HKCU:\\Run\\com.minimax.agent` | AI coding IDE |
| **Phone Link** | ~130 MB | `Get-AppxPackage -Name \"*Phone*\" | Remove-AppxPackage` | Restarts on reboot if not uninstalled |
| **ms-teamsupdate** | ~33 MB | `taskkill /f /im ms-teamsupdate.exe` | Leftover after Teams uninstall |

### WPS cleanup (trickiest offender)

WPS uses multiple persistence mechanisms — all must be stopped:
1. **Processes**: `wps.exe`, `wpscenter.exe`, `wpscloudsvr.exe`, `promecefpluginhost.exe`
2. **Scheduled Tasks** (3 found): `WpsExternal_<username>_startup`, `WpsExternal_<username>_interval`, `WpsUpdateTask_<username>`
3. **Multiple version dirs**: Old version at `12.2.0.23155\`, current at `12.2.0.23196\`
4. **Registry**: check `HKCU:\Software\Microsoft\Windows\CurrentVersion\Run`

```powershell
Stop-Process -Name "wps","wpscenter","wpscloudsvr","promecefpluginhost" -Force
Get-ScheduledTask | Where-Object { $_.TaskName -match 'Wps|wps' } | Disable-ScheduledTask
Remove-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "WPS*" -Force
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Kingsoft"
```

## Memory optimization (permanent fixes for low-RAM machines)

On a ~6 GB RAM machine (common Lenovo/consumer laptop with shared GPU), Windows
and pre-installed bloat can consume 80%+ of RAM before the user opens anything.
These fixes reclaim 1-2 GB permanently.

### 1. Page file — increase from default (CRITICAL stability fix)
Default Windows auto-managed page file is often too small on 6GB machines,
causing "out of memory" errors when RAM fills up.

```
# Set to 8 GB min / 16 GB max (admin PowerShell):
$pf = Get-WmiObject -Class Win32_PageFileSetting
$pf.InitialSize = 8192
$pf.MaximumSize = 16384
$pf.Put()
# REBOOT REQUIRED
```

Verify: `Get-WmiObject Win32_PageFileSetting | Select Name, InitialSize, MaximumSize`

### 2. DisablePagingExecutive — stop locking kernel in RAM
Many OEMs ship with `DisablePagingExecutive=1`, which forces kernel and driver
pages to stay in physical RAM (wastes 200-400 MB). Set to 0 to allow paging:

```
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management' \
    -Name DisablePagingExecutive -Value 0 -Type DWord -Force
# REBOOT REQUIRED
```

### 3. Startup program audit — 20+ apps auto-loading is the #1 cause
Press Ctrl+Shift+Esc → Startup apps tab → disable anything non-essential.
For programmatic cleanup (useful when there are 10+ items to disable):

```powershell
# Remove from current user registry
$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
Remove-ItemProperty -Path $regPath -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $regPath -Name "Teams" -Force -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $regPath -Name "com.squirrel.Teams.Teams" -Force -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $regPath -Name "ProtonVPN" -Force -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $regPath -Name "GoogleChromeAutoLaunch*" -Force -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $regPath -Name "MicrosoftEdgeAutoLaunch*" -Force -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $regPath -Name "CanvaAutoLaunchAvailabilityCheckAgent" -Force -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $regPath -Name "Figma Agent" -Force -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $regPath -Name "com.minimax.agent" -Force -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $regPath -Name "Claude" -Force -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $regPath -Name "Mathworks Service Host" -Force -ErrorAction SilentlyContinue

# Remove from startup folder
Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Ollama.lnk" -Force -ErrorAction SilentlyContinue

# Disable scheduled task startups
Disable-ScheduledTask -TaskName "WpsExternal*" -ErrorAction SilentlyContinue
Disable-ScheduledTask -TaskName "WpsUpdateTask*" -ErrorAction SilentlyContinue
```

On this box the usual offenders are:

| App | RAM saved | Action |
|-----|:---------:|--------|
| Docker Desktop | ~535 MB | Stops WSL VM from starting |
| WPS Office | ~250 MB | 4 processes including CEF |
| Ollama | ~200+ MB | Starts on demand via terminal |
| Claude Desktop | ~150+ MB | Start manually |
| Microsoft Teams (x2) | ~200+ MB | Start via browser |
| Phone Link | ~133 MB | Unused without phone |
| Canva + Figma Agent | ~120+ MB | Web app only |
| ProtonVPN | ~50+ MB | Start on demand |

Startup locations to check:
- Task Manager → Startup tab (UI)
- `shell:startup` (current user)
- `shell:common startup` (all users)
- `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run`
- `HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run`
- Task Scheduler → trigger "At logon" / "At startup"

### 4. Hidden memory hogs that users forget about
- **Docker Desktop / WSL VM**: Even with Docker Desktop "not running", the WSL
  VM (`vmmemWSL`) can hold 535 MB. Run `wsl --shutdown` when Docker is idle.
  Check: `wsl --list --verbose` (if state=Stopped, it's not eating RAM).
- **WPS Office CEF plugin**: WPS embeds a full Chrome Embedded Framework
  (`promecefpluginhost.exe`) for its interface — this is a persistent 80 MB
  even when no document is open.
- **Phone Link / Your Phone**: `PhoneExperienceHost.exe` always runs in
  background syncing photos/notifications — ~130 MB for a feature most don't
  actively use. Can be killed, restarts on reboot. To permanently remove:
  `Get-AppxPackage -Name "*Phone*" | Remove-AppxPackage`.
- **ms-teamsupdate**: After Teams is uninstalled, the `ms-teamsupdate.exe`
  updater can persist (~33 MB). Kill with `taskkill /f /im ms-teamsupdate.exe`.
  Check startup entries for the Teams update trigger.
- **Memory Compression**: Windows may use 70+ MB compressing inactive pages;
  this is normal and beneficial — do NOT kill it.

### 5. Quick Memory Cleaner (Memory_Cleaner.bat on Desktop)
Create a one-click bat script to kill WPS + AnyDesk before opening VS Code/browser:

```batch
@echo off
echo Killing memory hogs before opening VS Code/Chrome...
taskkill /f /im wps.exe >nul 2>&1 && echo Killed WPS Office
taskkill /f /im wpscenter.exe >nul 2>&1 && echo Killed WPS Center
taskkill /f /im wpscloudsvr.exe >nul 2>&1 && echo Killed WPS Cloud Sync
taskkill /f /im promecefpluginhost.exe >nul 2>&1 && echo Killed WPS CEF Plugin
taskkill /f /im AnyDesk.exe >nul 2>&1 && echo Killed AnyDesk
wmic OS get FreePhysicalMemory /Value
pause
```
Place on Desktop with a clear name (e.g. `Memory_Cleaner.bat`).

### 7. Disk space progress tracking
Track before/after uninstall runs to show real progress to the user:
```bash
df -h /c/ | tail -1
# Example: "C:  474G  333G  141G  71% /c" → 141 GB free (up from 120 GB)
```

### 8. Service management pattern
For services that need to be disabled but not fully uninstalled (e.g. AMD
Radeon, Lenovo Vantage), use the Manual + kill pattern:
```powershell
# 1. Stop now
Stop-Service "ServiceName" -Force -ErrorAction SilentlyContinue
# 2. Disable auto-start (or set to Manual for services that may be needed)
Set-Service "ServiceName" -StartupType Manual -ErrorAction SilentlyContinue
# 3. Kill any lingering processes
Get-Process -Name "*ServiceName*" -ErrorAction SilentlyContinue | Stop-Process -Force
```

### 6. Node.js memory tuning for video generation projects
For projects using Remotion / tsx / Node on a 6GB machine, the default V8 heap
limit (depends on available RAM, often 4GB+) causes OOM. Constrain it:

```
# In .env or shell profile:
NODE_OPTIONS=--max-old-space-size=2048
UV_THREADPOOL_SIZE=4

# For batch video generation: reduce parallel wave size
AGENTIC_WAVE_SIZE=1   # Default is often 3 — death on 6GB
```

Check current Node heap limit: `node -e "console.log(v8.getHeapStatistics().heap_size_limit/1024/1024)"`

## Bloatware — locked file force-delete pattern
Some uninstallers leave locked DLLs or EXEs behind (Bonjour `mdnsNSP.dll`, NI
`nipxicms.exe`, Office `MSOARIA.DLL`). The service may be stopped but a child
process still holds the file handle. Use the 3-step force-delete:

```powershell
# 1. Find and kill the hosting process (often a svchost or child process)
taskkill /f /t /im <process-wildcard>.exe
# 2. Take ownership + grant full control
takeown /f "C:\path\to\file" /r /d y 2>$null
icacls "C:\path\to\file" /grant Administrators:F /T /Q 2>$null
# 3. Then delete
Remove-Item -Recurse -Force "C:\path\to\folder"
```

Often the lock is held by a child process of `svchost`. Kill via taskkill with
`/t` (tree kill) to terminate the whole subtree, or search for the locked DLL
in `tasklist /m` and kill the owning PID directly.

## Bloatware — when the uninstaller EXE is missing
Some apps (PostgreSQL, RabbitMQ) have registry entries pointing to an
`uninstall.exe` that no longer exists on disk. The app is partially or fully
removed but leaves behind data directories and registry entries. Fix:
```powershell
# 1. Kill any remaining processes
taskkill /f /im <app-process>.exe 2>$null
# 2. Remove the program directory (check size first)
Remove-Item -Recurse -Force "C:\Program Files\<App Name>"
# 3. Remove data/cache in ProgramData and AppData
Remove-Item -Recurse -Force "$env:PROGRAMDATA\<App>\"
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\<App>\"
# 4. Optionally remove registry uninstall entry
Remove-Item -Recurse -Force "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\<Key>"
```

## Bloatware — scheduled task cleanup for non-standard items
Some persistent software uses only scheduled tasks (no service, no GUI).
Examples found on this box: **JarvisBoot/JarvisSupervise/JarvisWatchdog**,
**NahimicSvc32Run/NahimicSvc64Run/NahimicTask32/NahimicTask64**,
**Lenovo iM Controller TimeBasedEvents** (6 tasks).

```powershell
# List all non-Microsoft tasks:
Get-ScheduledTask | Where-Object { $_.TaskPath -notmatch "Microsoft" -and $_.TaskName -notmatch "Hermes|Paperclip|cua-driver" }
# Remove specific tasks by exact name:
Unregister-ScheduledTask -TaskName "JarvisBoot" -Confirm:$false
Unregister-ScheduledTask -TaskName "JarvisSupervise" -Confirm:$false
Unregister-ScheduledTask -TaskName "JarvisWatchdog" -Confirm:$false
```

## Bloatware — GameInput + Gaming Services (~61 MB)
Xbox gaming services run in background even on dev machines. Disable:
```powershell
@("GameInputSvc","GameInputRedistService","GamingServices","GamingServicesNet") |
    ForEach-Object { Get-Service $_ -ErrorAction SilentlyContinue | Set-Service -StartupType Disabled }
taskkill /f /im gamingservices.exe 2>$null
taskkill /f /im gamingservicesnet.exe 2>$null
# Also remove Xbox AppX packages:
Get-AppxPackage -Name "*Xbox*" | Remove-AppxPackage
```

## Bloatware — UltraViewer
Another lightweight remote-desktop tool. Kill and remove:
```powershell
sc stop UltraViewer_Service 2>$null
taskkill /f /im UltraViewer*.exe 2>$null
Remove-Item -Recurse -Force "C:\Program Files (x86)\UltraViewer"
```

## Reference files
`references/memory-optimization.md` — full PowerShell diagnostic commands, registry
paths, and AVS-specific tuning from a real 6GB Windows session.
`references/app-removal-workflow.md` — systematic removal workflow for 15+ apps.
`references/deep-clean-advanced.md` — locked file force-delete, orphaned scheduled
tasks (Jarvis, Nahimic, Lenovo ImController), GameInput/GamingServices teardown,
AppX bulk removal, and startup-cache-registry wipe techniques from a deep-clean
session.
`templates/Memory_Cleaner.bat` — reusable batch file template.

## Audio: "speakers not working / not clear"
Diagnosis order (hardware is usually fine — drivers show OK, services running):
1. `Get-PnpDevice -Class AudioEndpoint` — confirm Realtek Speakers = OK,
   Present=True, ConfigManagerErrorCode=0.
2. Virtual devices hijack default output. The usual suspects on Lenovo/Realtek
   laptops: **Nahimic** (Easy Surround / mirroring), **AudioRelay Virtual
   Speakers**, **NVIDIA Virtual Audio**. These steal the default device → silence
   even though the driver is "OK".
3. Fix: disable the virtual PLAYBACK sinks (NOT mics):
   `Get-PnpDevice | ?{$_.FriendlyName -eq 'Nahimic mirroring device'} |
    Disable-PnpDevice -Confirm:$false`. Repeat for Easy Surround, AudioRelay
   Virtual Speakers, NVIDIA Virtual Audio.
4. **"Not clear / muddy" after disabling**: Nahimic APO is STILL running
   (processes Nahimic3, NahimicAPO4Volume, NahimicService, Svc32/64). Stop them
   AND disable their **scheduled tasks** (`NahimicSvc32Run`, `NahimicSvc64Run`,
   `NahimicTask32`, `NahimicTask64`) via `Disable-ScheduledTask` — otherwise they
   respawn. Verify with `Get-Process -Name *nahimic*` (must be empty).
5. If still bad: set device format to 24-bit 48000 Hz + turn OFF "Audio
   enhancements" in Sound settings → device properties → Advanced.

## Reference
`references/audio-hijack-fix.md` — exact PowerShell/winreg commands for the
Nahimic audio-hijack fix.
