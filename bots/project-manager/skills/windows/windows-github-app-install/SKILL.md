---
name: windows-github-app-install
description: Silently install + verify a GitHub-release .exe from bash.
---

# windows-github-app-install

Install a Windows desktop application from a GitHub Release (or any known installer URL) the *right* way from the agent's MSYS/bash terminal: download, verify integrity, silent-install headless, confirm the binary actually lands and launches, then clean up. Every step below was verified end-to-end (the Orca install — see references/worked-example-orca.md).

This skill is **MSYS/bash-centric** (the Windows terminal runs git-bash). All commands assume that shell. Paths use `/c/Users/...` form, which works in MSYS.

## Workflow (verified end-to-end)

### 1. Get the latest release asset
For GitHub releases, use the redirecting `latest/download` URL — no API parsing needed:
```bash
cd "/c/Users/$USER/Downloads"
curl -fL -o <app>-setup.exe "https://github.com/<owner>/<repo>/releases/latest/download/<asset>.exe"
```
- `-f` fails on HTTP errors; `-L` follows redirects (GitHub 302-redirects `latest/download` to a CDN — without `-L` you get a tiny redirect HTML, not the binary).
- Get the exact asset name from the repo's `/releases/latest` page (e.g. `orca-windows-setup.exe`).

### 2. Verify integrity BEFORE installing
Never run an unverified installer.
```bash
sha256sum <app>-setup.exe
file <app>-setup.exe            # expect "... Nullsoft Installer self-extracting archive"
stat -c '%s bytes' <app>-setup.exe
```
- `file` confirming "Nullsoft Installer" proves it's a real installer, not a corrupted/HTML error page.
- If the project publishes checksums (release `SHA256SUMS` / notes), compare against those.

### 3. Silent install
Nullsoft (`/S`) and Inno Setup (`/SILENT` or `/VERYSILENT`) both support headless install:
```bash
./<app>-setup.exe /S
echo "installer parent exit:$?"
```
- Run large installs in the **background** (`terminal(background=true, notify_on_complete=true)`); poll the filesystem for the binary rather than waiting on stdout.
- Nullsoft `/S` parent exits 0 **before** the real extraction finishes in a child process — verify via the install dir, not the parent's exit code.

### 4. Locate the install (Nullsoft per-user default)
Nullsoft per-user installs land in:
```
C:\Users\<user>\AppData\Local\Programs\<app>\
```
with a Start Menu shortcut at:
```
C:\Users\<user>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\<App>.lnk
```
Use a **targeted `ls`** of the expected dir — do NOT run a broad `find` across `AppData\Local` (see Pitfalls).

### 5. Verify the binary launches (without a lingering GUI)
```bash
ls -lh "/c/Users/$USER/AppData/Local/Programs/<app>/<App>.exe"
ls "/c/Users/$USER/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/" | grep -i <app>
```
Quick liveness test — spawn with a hard timeout, then kill:
```bash
timeout 8 "/c/Users/$USER/AppData/Local/Programs/<app>/<App>.exe" & sleep 3; taskkill //IM <App>.exe //F
```
See Pitfalls on why `--version` lies for Electron apps.

### 6. Cleanup
Kill any lingering process — MSYS needs **double slash** on taskkill flags:
```bash
taskkill //IM <App>.exe //F
```
Optionally remove the installer from Downloads once verified.

## Pitfalls (learned the hard way)
- **`taskkill` needs double slashes in MSYS/bash**: `taskkill //IM name.exe //F`, NOT `taskkill /IM name.exe /F` (single slash is parsed differently and fails).
- **Broad `find` over `AppData` times out.** A `find /c/Users/.../AppData/Local -iname orca.exe` exceeded 60s and was killed. Use `ls` of the known install dir instead.
- **Electron apps ignore `--version`/`--help` and just launch the GUI.** `Orca.exe --version` actually booted the full app (and printed a harmless `spawn codex ENOENT` because Orca probes for a Codex binary that isn't installed). Don't use `--version` as a liveness check for Electron/Chromium apps — use file presence + process spawn + Start Menu link.
- **Nullsoft `/S` parent exits before install finishes.** Verify via the filesystem (binary appears) a few seconds later, not the parent return code.
- **Heavy Electron apps eat RAM.** A single Electron app can be 200MB+ on disk and pull significant RAM at runtime. On RAM-constrained hosts, launch only when needed and kill afterward. (One user keeps ~800MB free — treat 700MB+ Electron installs as "use on demand," not "leave running.")
- **`curl` to GitHub releases must use `-L`.** The `latest/download` URL 302-redirects; without `-L` you download a tiny redirect HTML, not the binary.

## References
- `references/worked-example-orca.md` — full real transcript of installing Orca (stablyai/orca): exact URLs, SHA256, install path, verification, cleanup. Copy-paste template.
- `scripts/install_github_release.sh` — reusable download→verify→silent-install helper for Nullsoft/Inno GitHub-release apps.
