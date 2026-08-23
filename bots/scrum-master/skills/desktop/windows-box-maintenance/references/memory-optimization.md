# Memory Optimization Reference (6GB Windows Laptop)

Captured from a real session on a Lenovo Windows 10 laptop with 5.86 GB visible RAM
(~8 GB shared with GPU), often <800 MB free, 280+ processes. All commands verified.

## Full Diagnostic Script

Create a `.ps1` file and run with:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File diag.ps1
```

```powershell
# === SYSTEM MEMORY FULL DIAGNOSTIC ===
$os = Get-CimInstance Win32_OperatingSystem
Write-Host "Total RAM: $([math]::Round($os.TotalVisibleMemorySize/1KB,1)) GB"
Write-Host "Free RAM: $([math]::Round($os.FreePhysicalMemory/1KB,1)) GB"
Write-Host "Free %: $([math]::Round($os.FreePhysicalMemory/$os.TotalVisibleMemorySize*100,1))%"

# === PAGE FILE ===
Get-CimInstance Win32_PageFileUsage | Select-Object Name, @{N='CurrentSizeMB';E={$_.CurrentPageFileSizeInMB}}
Get-CimInstance Win32_PageFileSetting | Select-Object Name, InitialSize, MaximumSize

# === PAGE FILE CONFIG (admin) ===
Get-CimInstance Win32_PageFileSetting
# To change:
# $pf = Get-WmiObject -Class Win32_PageFileSetting
# $pf.InitialSize = 8192
# $pf.MaximumSize = 16384
# $pf.Put()
# REBOOT REQUIRED

# === TOP MEMORY PROCESSES ===
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 30 Name, @{N='MB';E={[math]::Round($_.WorkingSet64/1MB,1)}}, @{N='CPU(s)';E={[math]::Round($_.TotalProcessorTime.TotalSeconds,1)}} | Format-Table -AutoSize

# === WINDOWS MEMORY MANAGEMENT REGISTRY ===
$key = "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
Write-Host "DisablePagingExecutive: $(Get-ItemProperty -Path $key -Name DisablePagingExecutive -ErrorAction SilentlyContinue | Select-Object -ExpandProperty DisablePagingExecutive)"
Write-Host "LargeSystemCache: $(Get-ItemProperty -Path $key -Name LargeSystemCache -ErrorAction SilentlyContinue | Select-Object -ExpandProperty LargeSystemCache)"

# To fix (admin):
# Set-ItemProperty -Path $key -Name DisablePagingExecutive -Value 0 -Type DWord -Force
```

## Page File Sizing Guide

| RAM | Recommended Page File | Notes |
|-----|---------------------|-------|
| 4 GB | 6-8 GB min, 12 GB max | Minimum viable |
| **6 GB** | **8 GB min, 16 GB max** | Common prebuilt laptop |
| 8 GB | 10-12 GB min, 20 GB max | Sweet spot |
| 16 GB | 8-16 GB system managed | Can scale down |

## DisablePagingExecutive Details

- `1` = Kernel/drivers locked in physical RAM (OEM default on some Lenovos)
- `0` = Kernel pages allowed (recommended for low-RAM systems)
- Effect: frees 200-400 MB RAM
- Trade-off: marginal performance cost if memory pressure triggers kernel paging
  (negligible on SSDs, measurable on HDDs)

## Startup Program Locations

| Location | Path |
|----------|------|
| Task Manager UI | Ctrl+Shift+Esc → Startup tab |
| Current user startup folder | `shell:startup` (resolves to `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`) |
| All users startup folder | `shell:common startup` |
| Registry (machine) | `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run` |
| Registry (user) | `HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run` |
| Task Scheduler | `taskschd.msc` → look for triggers "At logon" / "At startup" |

## Bloatware Uninstall (verified commands from real session)

All commands verified on Windows 10, Lenovo laptop, 5.86 GB RAM.

### Bulk uninstall script pattern

```powershell
function Run-Uninstall { param($Desc, $Cmd)
    Write-Host "--- $Desc ---"
    $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c $Cmd" -NoNewWindow -Wait -PassThru
    if ($proc.ExitCode -eq 0) { Write-Host "Success" } else { Write-Host "Exit: $($proc.ExitCode)" }
}

Run-Uninstall "Teams" "`"$env:LOCALAPPDATA\Microsoft\Teams\Update.exe`" --uninstall"
Run-Uninstall "Canva" "`"$env:LOCALAPPDATA\Programs\Canva\Uninstall Canva.exe`" /currentuser"
Run-Uninstall "Figma" "`"$env:LOCALAPPDATA\FigmaAgent\Uninstall.exe`""
Run-Uninstall "WPS" "`"$env:LOCALAPPDATA\Kingsoft\WPS Office\12.2.0.23196\utility\uninst.exe`" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART"
```

### Per-user app removal fallback (when uninstaller won't run silent)

```powershell
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Kingsoft"
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Programs\Canva"
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\FigmaAgent"
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Microsoft\Teams"
```

### Edge removal (requires both AppX + Win32)

```powershell
# AppX per-user
Get-AppxPackage -Name *MicrosoftEdge* | Remove-AppxPackage
# Provisioned (system-wide)
Get-AppxProvisionedPackage -Online | Where-Object { $_.DisplayName -match 'Microsoft.Edge' } | Remove-AppxProvisionedPackage -Online
# Win32 setup
"C:\Program Files (x86)\Microsoft\Edge\Application\150.0.4078.105\Installer\setup.exe" --uninstall --msedge --channel=stable --system-level
# EdgeUpdate daemon
"C:\Program Files (x86)\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe" /uninstall
```

### AMD Radeon Software (AppX + services)

```powershell
# Remove the Store App (saves ~273 MB on NVIDIA-primary machines)
Get-AppxPackage -Name "*AMD*Radeon*" | Remove-AppxPackage
# Kill processes immediately
taskkill /f /im AMDRSSrcExt.exe
taskkill /f /im AMDRSServ.exe
taskkill /f /im RadeonSoftware.exe
# Set services to Manual (NOT Disabled — integrated GPU may need them)
Get-Service "AMD Crash Defender Service" -ErrorAction SilentlyContinue | Set-Service -StartupType Manual
Get-Service "AMD External Events Utility" -ErrorAction SilentlyContinue | Set-Service -StartupType Manual
```

### Phone Link (Your Phone)

```powershell
Get-AppxPackage -Name "*Phone*" | Remove-AppxPackage
# Saves ~130 MB
```

### ms-teamsupdate (Teams updater leftover)

```powershell
taskkill /f /im ms-teamsupdate.exe 2>nul
Remove-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "Teams*" -Force -ErrorAction SilentlyContinue
# Saves ~33 MB
```

### WPS full cleanup (multi-mechanism)

```powershell
Stop-Process -Name "wps","wpscenter","wpscloudsvr","promecefpluginhost" -Force
Get-ScheduledTask | Where-Object { $_.TaskName -match 'Wps|wps' } | Disable-ScheduledTask
Remove-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "WPS*" -Force
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Kingsoft"
Remove-Item -Recurse -Force "C:\Program Files (x86)\Kingsoft"
```

### Finding uninstallers via registry (error-resistant)

```powershell
$paths = @("HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall","HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall","HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall")
$filters = @("Proton","WPS","Kingsoft","Canva","Figma","Teams","Edge")
foreach ($base in $paths) {
    $keys = Get-ChildItem $base -ErrorAction SilentlyContinue
    foreach ($key in $keys) {
        try { $props = Get-ItemProperty $key.PSPath -ErrorAction Stop
            if ($props.DisplayName) { foreach ($f in $filters) { if ($props.DisplayName -match $f) { Write-Host "$($props.DisplayName) → $($props.UninstallString)" } } }
        } catch { }
    }
}
```

### Startup cleanup programmatic (registry + scheduled tasks + startup folder)

```powershell
# Remove from user registry
$Run = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
@("Docker Desktop","CanvaAutoLaunchAvailabilityCheckAgent","Figma Agent","com.minimax.agent","Claude","Teams","com.squirrel.Teams.Teams","ProtonVPN","Mathworks Service Host") | ForEach-Object {
    Remove-ItemProperty -Path $Run -Name $_ -Force -ErrorAction SilentlyContinue
}
# Remove startup shortcuts
Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Ollama.lnk" -Force -ErrorAction SilentlyContinue
# Disable scheduled tasks
Disable-ScheduledTask -TaskName "WpsExternal*" -ErrorAction SilentlyContinue
Disable-ScheduledTask -TaskName "WpsUpdateTask*" -ErrorAction SilentlyContinue
```

## Quick Kill Commands (WPS + AnyDesk)

```batch
taskkill /f /im wps.exe
taskkill /f /im wpscenter.exe
taskkill /f /im wpscloudsvr.exe
taskkill /f /im promecefpluginhost.exe
taskkill /f /im AnyDesk.exe
```

## Node.js Memory Tuning

```bash
# Set in shell or .env before running Node/tsx:
export NODE_OPTIONS="--max-old-space-size=2048"
export UV_THREADPOOL_SIZE=4

# For Automated Video Generator (batch system):
export AGENTIC_WAVE_SIZE=1

# Check current heap limit:
node -e "console.log(v8.getHeapStatistics().heap_size_limit/1024/1024)"
```

## WSL Memory Cleanup

```bash
# Check WSL status
wsl --list --verbose

# Shut down ALL WSL VMs (frees vmmemWSL ~535 MB)
wsl --shutdown

# Kill specific WSL distro
wsl --terminate <distro-name>
```

## Free Memory Check (quick)

```bash
# In bash
wmic OS get FreePhysicalMemory /Value
# Returns KB — divide by 1024 for MB

# In PowerShell
$os = Get-CimInstance Win32_OperatingSystem
$freeMB = [math]::Round($os.FreePhysicalMemory/1KB, 0)
Write-Host "Free: $freeMB MB"
```
