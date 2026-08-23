# Worked example: installing Orca (stablyai/orca)

Real, end-to-end verified install (all steps actually ran). Use as a copy-paste template.

## Repo facts (verified)
- Repo: https://github.com/stablyai/orca
- License: MIT
- Latest Windows asset name: `orca-windows-setup.exe`
- Installer type: Nullsoft (per-user) self-extracting archive
- Install dir: `C:\Users\<user>\AppData\Local\Programs\orca\`
- Binary: `Orca.exe` (~216–225 MB)
- Start Menu: `AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Orca.lnk`

## Exact commands run
```bash
# 1. download (180 MB; ~2 min on 1.5 MB/s link)
cd "/c/Users/PREM KUMAR/Downloads"
curl -fL -o orca-windows-setup.exe \
  "https://github.com/stablyai/orca/releases/latest/download/orca-windows-setup.exe"

# 2. verify
sha256sum orca-windows-setup.exe
#   ad601ded19a0ec261c41e3cd557e2856406416b9a15453cb8c5907c6f066bac9
file orca-windows-setup.exe
#   ... Nullsoft Installer self-extracting archive, 5 sections
stat -c '%s bytes' orca-windows-setup.exe
#   188581112 bytes

# 3. silent install (background; Nullsoft parent exits 0 before extraction done)
./orca-windows-setup.exe /S

# 4. wait ~25s, then verify landing
ls "/c/Users/PREM KUMAR/AppData/Local/Programs/orca"
#   Orca.exe, Uninstall Orca.exe, resources/, locales/, *.dll, *.pak ...

# 5. launch verification (Electron ignores --version; it boots the GUI)
#    spawn with timeout, then kill. Harmless log: "spawn codex ENOENT"
timeout 8 "/c/Users/PREM KUMAR/AppData/Local/Programs/orca/Orca.exe" & sleep 3
taskkill //IM Orca.exe //F

# 6. start-menu link present
ls "/c/Users/PREM KUMAR/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/" | grep -i orca
#   Orca.lnk

# cleanup leftover process if any
taskkill //IM Orca.exe //F
```

## Result
- ~711 MB on disk at install dir.
- App launches; Start Menu shortcut created.
- On a RAM-constrained host, treat as on-demand (don't leave running idle).

## Notes for the agent
- The `latest/download` URL 302-redirects — `-L` is mandatory.
- Electron apps do NOT honor `--version`; using it as a liveness check just opens the GUI.
- `taskkill` under MSYS needs double slashes: `//IM`, `//F`.
