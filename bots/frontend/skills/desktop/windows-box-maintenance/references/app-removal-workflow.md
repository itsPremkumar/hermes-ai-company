# Systematic App Removal Workflow (6 GB Windows Dev Box)

This file captures the concrete session where we removed 15+ apps from a
Lenovo laptop (6 GB RAM) recovering ~21 GB disk and significant RAM.

## Pre-removal audit

Before removing anything, assess the app's value vs cost:

| Question | If yes |
|----------|--------|
| Is it a dev tool? (VS Code, Git, JDK, Python, Docker, CUDA) | KEEP |
| Is it a runtime/library? (VC++ redist, .NET SDK, Node.js, Erlang) | KEEP |
| Is it OEM bloat? (Lenovo Vantage, Legion Arena, Lenovo Now) | REMOVE |
| Is it a non-dev productivity app? (Office, Canva, WPS) | REMOVE (use Google Docs / web) |
| Is it a duplicate? (WinRAR x86 + x64, Thonny + WebStorm) | REMOVE old/smaller |
| Is it a game/gaming service? (Steam, Need for Speed, GeForce Experience) | REMOVE |
| Is it an old version of something current? (MATLAB R2021a when R2023b exists) | REMOVE old |
| Is it a legacy/deprecated dependency? (Silverlight, Bonjour, Visual J#) | REMOVE |

## App discovery script

Write a .ps1 file to avoid MSYS quoting hell:

```powershell
$paths = @(
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall"
)
$targets = @("PostgreSQL","RabbitMQ","MATLAB","Office","SQL Server","VMware","WinRAR")
foreach ($base in $paths) {
    $keys = Get-ChildItem $base -ErrorAction SilentlyContinue
    foreach ($key in $keys) {
        try {
            $props = Get-ItemProperty $key.PSPath -ErrorAction Stop
            if ($props.DisplayName) {
                foreach ($t in $targets) {
                    if ($props.DisplayName -match $t) {
                        Write-Host "$($props.DisplayName)"
                        Write-Host "  Uninstall: $($props.UninstallString)"
                        Write-Host "  Key: $($key.PSChildName)"
                        Write-Host "---"
                    }
                }
            }
        } catch { }
    }
}
```

## Uninstall strategy by installer type

### 1. Try silent first (write to a .ps1 file, NOT inline)
```powershell
function Run-Uninstall {
    param($Name, $Exe, $ArgsArr = @())
    Write-Host "`n--- $Name ---"
    if ($ArgsArr.Count -gt 0) {
        $p = Start-Process -FilePath $Exe -ArgumentList $ArgsArr -Wait -PassThru
    } else {
        $p = Start-Process -FilePath $Exe -Wait -PassThru
    }
    Write-Host "  Exit: $($p.ExitCode)"
    Start-Sleep 2
}
```

### 2. Silent flags by installer family

| Installer | Flags | Example |
|-----------|-------|---------|
| MSI | `/quiet /norestart` | `msiexec /x {GUID} /quiet /norestart` |
| Inno Setup | `/VERYSILENT /SUPPRESSMSGBOXES` | `unins000.exe /VERYSILENT /SUPPRESSMSGBOXES` |
| NSIS | `/S` | `uninstall.exe /S` |
| InstallShield | `-s -f1<path>\setup.iss` | Complex — prefer Windows Settings |
| Click-to-Run (Office) | `scenario=install scenariosubtype=ARP productstoremove=...` | See below |
| Per-user (AppData) | Try silent; if it fails just delete the folder | Safe for AppData/* |
| WMI/Package | `Get-Package -Name "*" \|Uninstall-Package -Force` | Slow but works for some MSI apps |

### 3. Office 2021 specific uninstall
```powershell
Start-Process -FilePath "C:\Program Files\Common Files\Microsoft Shared\ClickToRun\OfficeClickToRun.exe" `
    -ArgumentList "scenario=install","scenariosubtype=ARP","sourcetype=None",`
                  "productstoremove=HomeStudent2021Retail.16_en-us_x-none",`
                  "culture=en-us","version.16=16.0" -Wait
```

### 4. SQL Server 2014 — multi-component
SQL Server has ~10 interdependent MSI components + the main engine.
The SetupARP.exe is the centralized uninstaller:
```
"c:\Program Files\Microsoft SQL Server\120\Setup Bootstrap\SQLServer2014\x64\SetupARP.exe" /ACTION=UNINSTALL
```
But it **requires UI interaction** — silent mode often hangs.
Individual MSI components (RsFx, Setup Support, ScriptDom) can be removed
via msiexec:
```
msiexec /x {655A4169-5BB6-44B0-A9BA-4CBE23A412AA} /quiet /norestart
```

### 5. VMware Workstation — MSI GUID
```
msiexec /x {00BF49FA-E6A3-4227-A18E-4A9036594E9D} /quiet /norestart
```
Exit code 1639 = bad parameter syntax (check GUID brackets and spacing).

### 6. National Instruments — ~80+ MSI components
Use the centralized NI Uninstaller:
```
"C:\Program Files (x86)\National Instruments\Shared\NIUninstaller\uninst.exe" --force-locked --force-essential
```
Or NI Package Manager:
```
"C:\Program Files\National Instruments\NI Package Manager\NIPackageManager.exe" remove ni-package-manager --force-locked --force-essential
```

### 7. OneDrive
```
"C:\Program Files\Microsoft OneDrive\25.075.0420.0002\OneDriveSetup.exe" /uninstall /allusers
```

### 8. Edge (deeply integrated — requires 3 actions)
```
Remove-AppxPackage Microsoft.MicrosoftEdge.Stable
setup.exe --uninstall --msedge --channel=stable --system-level --verbose-logging
MicrosoftEdgeUpdate.exe /uninstall
```
Exit code 93 = E_FAIL (operation not permitted without admin). Run elevated.

### 9. Docker Desktop + WSL
Even "stopped" Docker spawns `vmmemWSL` (~429 MB). Kill with `wsl --shutdown`.
For permanent removal: uninstall Docker Desktop + `wsl --unregister <distro>`.

### 10. AMD Radeon Software (AppX + services — NVIDIA-primary machines)
On AMD Ryzen + NVIDIA dGPU laptops, AMD Radeon Software is bloat. Remove:
```powershell
# Remove the AppX package
Get-AppxPackage -Name "*AMD*Radeon*" | Remove-AppxPackage
# Kill running processes
taskkill /f /im AMDRSSrcExt.exe 2>nul
taskkill /f /im AMDRSServ.exe 2>nul
taskkill /f /im RadeonSoftware.exe 2>nul
# Set services to Manual (NOT Disabled — integrated GPU may need them)
Get-Service "AMD Crash Defender Service" -ErrorAction SilentlyContinue | Set-Service -StartupType Manual
Get-Service "AMD External Events Utility" -ErrorAction SilentlyContinue | Set-Service -StartupType Manual
```

### 11. Phone Link (AppX)
```powershell
Get-AppxPackage -Name "*Phone*" | Remove-AppxPackage
```
Saves ~130 MB. No reboot needed.

### 12. ms-teamsupdate (leftover after Teams uninstall)
```powershell
taskkill /f /im ms-teamsupdate.exe
# Also remove from registry if present:
Remove-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "Teams*" -Force -ErrorAction SilentlyContinue
```

### 13. Service management for disabled-but-not-uninstalled apps
When an app's uninstaller isn't available or you only want to stop it from
running (not full uninstall), use the 3-step pattern:
```powershell
# 1. Stop the service now
Stop-Service "ServiceName" -Force -ErrorAction SilentlyContinue
# 2. Prevent auto-start at boot (Manual = starts on demand; Disabled = never)
Set-Service "ServiceName" -StartupType Manual -ErrorAction SilentlyContinue
# 3. Kill any lingering processes
Get-Process -Name "*ServiceName*" -ErrorAction SilentlyContinue | Stop-Process -Force

# To find what services a process belongs to:
Get-CimInstance Win32_Service -Filter "Name LIKE '%keyword%'" | Select Name,State,StartMode
```

### 14. Startup items from Task Scheduler
Some apps (WPS, AMD, Lenovo) create scheduled tasks for persistence:
```powershell
# List non-Microsoft scheduled tasks
Get-ScheduledTask | Where-Object { $_.TaskPath -notmatch "Microsoft" } | Select TaskName,TaskPath,State
# Disable by name pattern
Get-ScheduledTask | Where-Object TaskName -match "Wps|AMD|Lenovo" | Disable-ScheduledTask
```

## When uninstaller binary is missing (common with per-user installs)

Some uninstallers are already deleted when the app was partially removed.
In that case:
1. Kill all processes from that app
2. Delete the program directory
3. Remove registry entries (optional but cleaner)
4. Delete %APPDATA% and %LOCALAPPDATA% cache folders for that app

## Kill stuck uninstallers between attempts
```powershell
taskkill /f /im uninstall.exe
taskkill /f /im msiexec.exe
taskkill /f /im setup.exe
```

## Verification pattern
```bash
check() {
  if [ -d "$1" ]; then echo "⚠️  $2 - STILL PRESENT ($(du -sh "$1"))"
  else echo "✅ $2 - REMOVED"
  fi
}
check "/c/Program Files/MATLAB" "MATLAB"
check "/c/Program Files/Microsoft Office/root" "Office 2021"
# ... etc
```

## Disk space tracking
Track before/after with `df -h /c/ | tail -1` to show the user real progress.
On ~120 GB free baseline, removing MATLAB + Office + SQL + VMware + PostgreSQL
recovered ~21 GB in one session.
