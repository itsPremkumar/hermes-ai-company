# Advanced Deep-Clean Techniques (6 GB Windows Dev Box)

Captured from a deep-clean session on a Lenovo Windows laptop (6 GB RAM,
NVIDIA dGPU + AMD iGPU) recovering ~26 GB disk and ~1.3 GB RAM from bloat.

## 1. Locked File Force-Delete

Some uninstallers remove the app but leave locked DLLs (Bonjour `mdnsNSP.dll`,
NI `nipxicms.exe`, Office `MSOARIA.DLL`). The hosting process is a child of
`svchost` or a stub that respawns when the service is stopped.

### Step-by-step
```powershell
# Step 1: Kill the service (even if already stopped, sometimes a process lingers)
Stop-Service "ServiceName" -Force -ErrorAction SilentlyContinue

# Step 2: Kill any process that might hold the lock
taskkill /f /t /im "process-name.exe" 2>$null

# Step 3: Take ownership and grant Administrators full control
takeown /f "C:\Program Files\TargetFolder" /r /d y 2>$null
icacls "C:\Program Files\TargetFolder" /grant Administrators:F /T /Q 2>$null

# Step 4: Delete
Remove-Item -Recurse -Force "C:\Program Files\TargetFolder" -ErrorAction Stop
```

### Finding what holds the lock
```powershell
# Option A: tasklist /m lists DLLs loaded per process
tasklist /m mdnsNSP.dll
# → Returns PID, then kill with taskkill /F /PID <PID>

# Option B: Handle.exe (Sysinternals) — not pre-installed
# Option C: Brute force — kill all svchost children via taskkill /f /t
taskkill /f /t /im svchost.exe  # DANGER: kills ALL services, forces reboot
# Better: kill the specific NI/Office/Bonjour service's svchost
```

### Real-world lockers found on this box
| DLL/EXE | Held by | App |
|---------|---------|-----|
| `mdnsNSP.dll` | `svchost.exe` hosting Bonjour Service | Bonjour |
| `nipxicms.exe` | `svchost.exe` hosting PXI service | NI PXI |
| `MSOARIA.DLL` | `OfficeClickToRun.exe` | Office 2021 |
| `nimdnsNSP.dll` | `svchost.exe` hosting nimdnsResponder | NI mDNS |
| `registry.bin` | `nierserver.exe` (NI Error Reporting) | NI |

## 2. Orphaned Scheduled Tasks

Some software persists ONLY via scheduled tasks after the program is removed.
These tasks stay in "Ready" state and may trigger silently.

### Discovery
```powershell
# All non-Microsoft tasks
Get-ScheduledTask | Where-Object { $_.TaskPath -notmatch "Microsoft" } |
    Select TaskName, TaskPath, State, Actions |
    Format-Table -AutoSize -Wrap
```

### Found on this box

| Task | Origin | Action |
|------|--------|--------|
| `JarvisBoot` | Paperclip/Jarvis agent framework | `Unregister-ScheduledTask -Confirm:$false` |
| `JarvisSupervise` | Same framework | `Unregister-ScheduledTask -Confirm:$false` |
| `JarvisWatchdog` | Same framework | `Unregister-ScheduledTask -Confirm:$false` |
| `NahimicSvc32Run` | Nahimic audio | `Unregister-ScheduledTask -Confirm:$false` |
| `NahimicSvc64Run` | Nahimic audio | `Unregister-ScheduledTask -Confirm:$false` |
| `NahimicTask32` | Nahimic audio | `Unregister-ScheduledTask -Confirm:$false` |
| `NahimicTask64` | Nahimic audio | `Unregister-ScheduledTask -Confirm:$false` |
| `20957a40-*` (6 GUIDs) | Lenovo ImController | `Disable-ScheduledTask` (safe) |
| `Clawdbot Gateway` | OpenClaw agent | Keep if using OpenClaw |
| `cua-driver-serve` | Hermes CUDA driver | Keep (needed for Hermes) |
| `Hermes_Gateway` | Hermes | Keep |
| `PaperclipServer`, `PaperclipWatchdog` | Paperclip | Keep if using |

```powershell
# Remove Jarvis (confirmed unwanted)
@("JarvisBoot","JarvisSupervise","JarvisWatchdog") | ForEach-Object {
    Unregister-ScheduledTask -TaskName $_ -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed: $_"
}
```

## 3. GameInput + Gaming Services (~61 MB)

Xbox gaming infrastructure on a dev machine wastes 61 MB. Full teardown:

```powershell
# Disable services
@("GameInputSvc","GameInputRedistService","GamingServices","GamingServicesNet") |
    ForEach-Object { 
        Get-Service $_ -ErrorAction SilentlyContinue | 
            Stop-Service -Force -ErrorAction SilentlyContinue
        Get-Service $_ -ErrorAction SilentlyContinue | 
            Set-Service -StartupType Disabled -ErrorAction SilentlyContinue
    }

# Kill running processes
taskkill /f /im gamingservices.exe 2>$null
taskkill /f /im gamingservicesnet.exe 2>$null
taskkill /f /im GameInputSvc.exe 2>$null

# Remove Xbox AppX packages
@("*Xbox*","*Microsoft.Gaming*","*Microsoft.Xbox*") | ForEach-Object {
    Get-AppxPackage -Name $_ -ErrorAction SilentlyContinue | Remove-AppxPackage -ErrorAction SilentlyContinue
}
```

## 4. AppX Bulk Removal Pattern

Several unwanted Store apps survive normal uninstall but can be removed via
`Remove-AppxPackage`. Common candidates:

| AppX Pattern | Typical RAM | Notes |
|-------------|:-----------:|-------|
| `*AMD*Radeon*` | ~273 MB | Only if NVIDIA dGPU present |
| `*Xbox*` or `*Gaming*` | ~61 MB | Safe to remove on dev machines |
| `*Phone*` or `*YourPhone*` | ~130 MB | Phone Link |
| `*Microsoft.MicrosoftEdge.Stable*` | ~300 MB | Edge — needs separate Win32 removal too |

```powershell
# Remove all in one shot
@("*AMD*Radeon*","*Xbox*","*Gaming*","*Phone*","*YourPhone*") | ForEach-Object {
    Get-AppxPackage -Name $_ -ErrorAction SilentlyContinue | Remove-AppxPackage -ErrorAction SilentlyContinue
}
```

## 5. NI (National Instruments) — Complete Wipe

NI installs 80+ MSI components with no master uninstaller. Most need individual
removal. The fastest cleanup on an unwanted install is:

```powershell
# Phase 1: Disable all NI services
@("nipxism","nidevldu","nierserver","nimdnsResponder","nisvcloc",
  "niauth_daemon","nidmsrv","niDiscSvc","nimxs","nipxicms",
  "lkClassAds","lkTimeSync","lktsrv","niroco","nisds") |
    ForEach-Object { 
        Stop-Service $_ -Force -ErrorAction SilentlyContinue
        Set-Service $_ -StartupType Disabled -ErrorAction SilentlyContinue
    }

# Phase 2: Kill all NI processes
Get-Process | Where-Object { $_.Name -match "ni|lk|nipxi" -and $_.Company -match "National Instruments" } | 
    Stop-Process -Force -ErrorAction SilentlyContinue

# Phase 3: Delete all directories
@("C:\Program Files\National Instruments",
  "C:\Program Files (x86)\National Instruments",
  "$env:LOCALAPPDATA\National Instruments",
  "$env:PROGRAMDATA\National Instruments") | 
    ForEach-Object { Remove-Item -Recurse -Force $_ -ErrorAction SilentlyContinue }

# Phase 4: Remove registry keys
@("HKLM:\Software\National Instruments",
  "HKLM:\Software\WOW6432Node\National Instruments",
  "HKCU:\Software\National Instruments") |
    ForEach-Object { Remove-Item -Recurse -Force $_ -ErrorAction SilentlyContinue }
```

## 6. Lenovo Full Cleanup (beyond Vantage)

Even after uninstalling Lenovo Vantage and Lenovo Now, these persist:

| Leftover | Location | Action |
|----------|----------|--------|
| FnHotkeyUtility.exe (~15 MB) | Running | `taskkill /f /im FnHotkey*.exe` |
| FnHotkeyCapsLKNumLK (~11 MB) | Running | Kill via taskkill |
| UDClientService (~16 MB) | Running | Stop-Service + Disabled |
| LenovoUtilityService (~9 MB) | Running | Stop-Service + Disabled |
| ImControllerService | Running | Disable |
| 6 ImController scheduled tasks | `\Lenovo\ImController\TimeBasedEvents\` | Disable via Disable-ScheduledTask |
| ProgramData\Lenovo\Udc\* | Disk | Remove-Item (may be locked; use takeown + icacls) |

```powershell
# Disable remaining Lenovo services
@("LenovoVantageService","LenovoFnAndFunctionKeys","LenovoUtilityService",
  "UDClientService","ImControllerService") |
    ForEach-Object {
        Stop-Service $_ -Force -ErrorAction SilentlyContinue
        Set-Service $_ -StartupType Disabled -ErrorAction SilentlyContinue
    }

# Kill processes
taskkill /f /im FnHotkey*.exe 2>$null
taskkill /f /im Lenovo*.exe 2>$null
taskkill /f /im UDClient*.exe 2>$null

# Disable the ImController scheduled tasks
Get-ScheduledTask -TaskPath "\Lenovo\ImController\" -ErrorAction SilentlyContinue |
    Disable-ScheduledTask -ErrorAction SilentlyContinue
Get-ScheduledTask -TaskPath "\Lenovo\UDC\" -ErrorAction SilentlyContinue |
    Disable-ScheduledTask -ErrorAction SilentlyContinue

# Delete leftover files (may need takeown for ProgramData\Lenovo)
Remove-Item -Recurse -Force "C:\Program Files (x86)\Lenovo" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Lenovo" -ErrorAction SilentlyContinue
```

## 7. Startup Cleanup (all methods)

Windows has 4 independent startup mechanisms. All must be checked:

```powershell
# 1. User Registry Run keys
$runPaths = @(
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run",
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"
)
foreach ($path in $runPaths) {
    Get-ItemProperty $path -ErrorAction SilentlyContinue |
        Select-Object -ExcludeProperty PSPath,PSParentPath,PSChildName,PSDrive,PSProvider |
        ForEach-Object { $_.PSObject.Properties | Select Name, Value }
}

# 2. Startup folder (current user)
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\*"

# 3. Startup folder (all users)
Get-ChildItem "$env:PROGRAMDATA\Microsoft\Windows\Start Menu\Programs\Startup\*"

# 4. Task Scheduler (logon triggers)
Get-ScheduledTask | Where-Object { $_.TaskPath -notmatch "Microsoft" } |
    Where-Object { $_.Triggers.LogonType -ne $null }
```

Items removed from startup in this session:
- Arduino Cloud Agent (startup folder .lnk)
- free-llm-router (startup folder .lnk)
- BraveSoftware Update (registry)
- NIRegistrationWizard (registry)
- NI Error Reporting (registry)
- SOLIDWORKS Background Downloader (registry)
- OneDriveSetup (registry, multiple entries)

## 8. Verification After Deep Clean

```powershell
# Final RAM check
$os = Get-CimInstance Win32_OperatingSystem
Write-Host "Free: $([math]::Round($os.FreePhysicalMemory/1024,1)) GB / $([math]::Round($os.TotalVisibleMemorySize/1024,1)) GB"

# Check for remaining unwanted processes
$unwanted = @("nipxism","nierserver","nidevldu","nimdns","niroco","lkClassAds",
              "lktsrv","nimxs","niDisc","nisds","FnHotkey","LenovoVantage",
              "UDClient","GameInput","Gaming","AnyDesk","UltraViewer",
              "Bonjour","SebWindows","Nahimic","Jarvis","ms-teamsupdate",
              "RadeonSoftware","AMDRSServ")
foreach ($p in $unwanted) {
    if (Get-Process -Name $p -ErrorAction SilentlyContinue) {
        Write-Warning "Still running: $p"
    }
}

# Disk space recovered
$drive = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
Write-Host "Disk: $([math]::Round($drive.FreeSpace/1GB,0)) GB free"
```

Typical result from this session: **RAM 0.8 GB → 2.06 GB free**,
**Disk 120 GB → 146 GB free** (~26 GB recovered).
