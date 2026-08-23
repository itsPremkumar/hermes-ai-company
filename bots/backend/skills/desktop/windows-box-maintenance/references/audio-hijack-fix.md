# Audio Hijack Fix — Nahimic / virtual-device stealing default output
# Built 2026-07-18 after fixing "speakers silent then muddy" on a Lenovo/Realtek
# laptop. Symptom: drivers OK, services running, but no/unclear sound.

## Step 1 — confirm hardware healthy
```powershell
Get-PnpDevice -Class AudioEndpoint | ?{ $_.FriendlyName -match 'Speaker|Realtek|Nahimic|Virtual|NVIDIA' } | Select-Object FriendlyName,Status
# Realtek Speakers should be Status=OK. Virtual sinks present = suspect.
```

## Step 2 — disable virtual PLAYBACK sinks (keep mics)
```powershell
$names = @('Nahimic mirroring device','Nahimic Easy Surround device')
foreach ($n in $names) {
  $dev = Get-PnpDevice | ?{ $_.FriendlyName -eq $n }
  if ($dev) { Disable-PnpDevice -InputObject $dev -Confirm:$false }
}
# Also by InstanceId:
Disable-PnpDevice -InstanceId 'SWD\MMDEVAPI\{0.0.0.00000000}.{3724BEB7-F4C5-4A88-A38E-89C392227014}' -Confirm:$false  # AudioRelay Virtual Speakers
Disable-PnpDevice -InstanceId 'ROOT\UNNAMED_DEVICE\0000' -Confirm:$false  # NVIDIA Virtual Audio
```

## Step 3 — if "muddy/not clear" AFTER step 2: Nahimic APO still running
Nahimic processes: Nahimic3, NahimicAPO4Volume, nahimicNotifSys, NahimicService,
NahimicSvc32, NahimicSvc64. Stop them, then disable their SCHEDULED TASKS
(otherwise they respawn):
```powershell
@('Nahimic3','NahimicAPO4Volume','nahimicNotifSys','NahimicService','NahimicSvc32','NahimicSvc64') | %{
  Get-Process -Name $_ -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
}
Disable-ScheduledTask -TaskName 'NahimicSvc32Run' -EA SilentlyContinue
Disable-ScheduledTask -TaskName 'NahimicSvc64Run' -EA SilentlyContinue
Disable-ScheduledTask -TaskName 'NahimicTask32'  -EA SilentlyContinue
Disable-ScheduledTask -TaskName 'NahimicTask64'  -EA SilentlyContinue
Set-Service -Name NahimicService -StartupType Disabled -EA SilentlyContinue
```
Verify clean: `Get-Process -Name *nahimic*` → must be empty.

## Step 4 — stale game/app registry entry (phantom size in Settings)
```python
import winreg
keys = [(winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall")]
for hkey, sub in keys:
    with winreg.OpenKey(hkey, sub) as k:
        for i in range(winreg.QueryInfoKey(k)[0]):
            name = winreg.EnumKey(k, i)
            try:
                with winreg.OpenKey(k, name) as sk:
                    disp = winreg.QueryValueEx(sk, "DisplayName")[0]
                if "euro truck" in disp.lower():
                    winreg.DeleteKey(k, name); print("DELETED", name)
            except Exception: pass
```
