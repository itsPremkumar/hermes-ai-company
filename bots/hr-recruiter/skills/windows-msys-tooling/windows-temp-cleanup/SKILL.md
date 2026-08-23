---
name: windows-temp-cleanup
description: 3-phase Windows disk cleanup for git-bash/MSYS - Phase 1 is system temp/pip/npm caches; Phase 2 is browser/app caches, huggingface models, GPU shaders; Phase 3 is unused software audit. Measure-first, ASK before deleting user data or uninstalling software.
---

# Windows Temp / Cache Cleanup (safe, MSYS)

Goal: free disk space on a Windows box WITHOUT deleting user data, project
source, or final deliverables. The cardinal rule: **measure → classify →
delete only known-safe patterns → verify nothing important moved.**

## Trigger
Load when:
- User says "disk is full", "clean temp/cache", "delete junk", "storage filling up".
- You need to free space before a build/render that would otherwise fail.
- Auditing where an app (e.g. a video pipeline) leaks intermediate files.

## CRITICAL CONSTRAINTS (never violate)
- NEVER delete `Downloads/`, Desktop, Documents, project `output/` (final
  deliverables), or any `src/` / git-tracked files without explicit ask.
- NEVER type passwords or touch the user's accounts.
- Prefer deleting *named temp patterns* over blanket `rm -rf /tmp/*` (which can
  break a running process holding handles in there).
- The agent's own running processes may have live temp files — deleting active
  handles can crash them. Prefer pipeline-scratch patterns that are inert.

## Step 1 — Measure (always first)
```bash
df -h /c                                  # disk before
du -sh /tmp 2>/dev/null                   # MSYS temp (= AppData/Local/Temp junction)
du -sh /c/Users/PREM\ KUMAR/AppData/Roaming/npm-cache
du -sh /c/Users/PREM\ KUMAR/AppData/Local/pip
du -sh /c/Users/PREM\ KUMAR/Downloads
du -sh /c/Windows/Temp
du -sh /c/Windows/SoftwareDistribution/Download   # Win Update cache (often small)
```
Bounded scans (avoid 120s timeouts on huge trees):
```bash
timeout 30 du -sh /tmp/* 2>/dev/null | sort -rh | head -20
```
PowerShell is faster for deep NTFS sizes:
```bash
powershell.exe -NoProfile -Command "(Get-ChildItem 'C:\Windows\SoftwareDistribution\Download' -Recurse -EA SilentlyContinue | Measure-Object -Property Length -Sum).Sum /1GB"
```

## Step 2 — Classify candidate folders
| Target | Safe? | Note |
|--------|-------|------|
| `%TEMP%` / `/tmp` named pipeline-scratch (e.g. `vf-est-*`, `remotion-*`, `capside-*`, `cs_frame_job_*`, `agentic-*`, `avg-*`, `ac-*`, `_ops-test-*`, `pytest-of-*`) | ✅ | Intermediate only; regenerated on next run |
| `pip cache purge` | ✅ | `python -m pip cache purge`; regenerates on demand |
| `npm cache` | ✅ | `npm cache clean --force` |
| `Windows\Temp\*` | ✅ | System temp |
| `DiagOutputDir`, `opencode`, `WER` `swap.vhdx` GUID dirs | ✅ | Diagnostic dumps |
| `Downloads/` | ⚠️ | ASK first — user files |
| `AppData\Local\Temp` mount inflation | ⚠️ | see Pitfall below |

## Step 3 — Bulk delete named patterns (example)
```bash
cd /tmp
rm -rf vf-est-* agentic-render-* agentic-tts-* avg-batch-* capside-* \
      _ops-test-* ops-test-* react-motion-render* pytest-of-* ac-* \
      cs_frame_job_*.png photo_cache qa_frames .arduinoIDE-unsaved* \
      puppeteer_dev_chrome_profile-* playwright-* miniflare-*
rm -rf /c/Windows/Temp/*
python -m pip cache purge
```
Then **verify**: re-run `df -h /c` and confirm `du -sh /tmp` dropped, and confirm
the project output dir is unchanged (`du -sh <project>/output`).

## Pitfall — `/tmp` headline size is inflated (MSYS mount artifact)
`du -sh /tmp` can report e.g. 8.2G when every listed subdir sums to ~1.5G.
`/tmp` is a junction to `AppData\Local\Temp` and a hidden/empty subdir inflates
the total. Don't trust the headline — use `du -h --max-depth=1 /tmp`, sum the
real entries, delete those, then re-measure. The residue is usually a junction
accounting artifact, not recoverable space.

## Pitfall — pipeline temp-leak audit (find code that writes outside workspace)
When cleaning a project's junk, trace where intermediate files escape to system
TEMP so they stop re-accumulating. Grep the source for the leak points:
```bash
rg -n "os\.tmpdir|process\.env\.TMP|mkdtemp" src --glob '!*.test.ts'
```
A correct design keeps final output in `output/` and all assets/temp in
`workspace/` (resolveProjectPath('workspace', ...)). Any `os.tmpdir()` in
*production* (non-test) code is a leak → patch it to write into
`resolveProjectPath('workspace','tmp', ...)`. Test-code `mkdtemp` leaks only
matter when the test suite runs locally; route them to `workspace/tmp/tests/`.

## Pitfall — `du`/long scans time out at 120s
Huge AppData trees (npm cache, SoftwareDistribution) can exceed the 120s
terminal timeout. Use `timeout 30 du -sh <path>/*`, bound with `head`, or fall
back to PowerShell `Get-ChildItem | Measure-Object` which is faster on NTFS.

## Verification (prove you didn't delete deliverables)
- `df -h /c` before vs after (report GB freed).
- `du -sh <project>/output` unchanged.
- `git -C <project> status --short | grep deleted` → must be empty (no source deleted).

---

## Phase 2 — Application Cache Cleanup (when user wants more space)

After clearing system temp, the user may say "I need more space" or ask for a
list of other cache/temp items. Measure these additional targets:

```bash
# Browser caches (Brave, Chrome, Edge)
du -sh "/c/Users/$USER/AppData/Local/BraveSoftware/Brave-Browser/User Data/Default/Cache"
du -sh "/c/Users/$USER/AppData/Local/BraveSoftware/Brave-Browser/User Data/Default/Code Cache"
du -sh "/c/Users/$USER/AppData/Local/BraveSoftware/Brave-Browser/User Data/Default/Service Worker"
du -sh "/c/Users/$USER/AppData/Local/BraveSoftware/Brave-Browser/User Data/Default/Media Cache"
du -sh "/c/Users/$USER/AppData/Local/Google/Chrome/User Data/Default/Cache"
du -sh "/c/Users/$USER/AppData/Local/Microsoft/Edge/User Data/Default/Cache"

# VS Code workspace storage
du -sh /c/Users/$USER/AppData/Roaming/Code/User/workspaceStorage

# Electron app updater cached installers (already-downloaded .exe left behind)
ls -lh /c/Users/$USER/AppData/Local/@mmx-agentelectron-updater/installer.exe
ls -lh /c/Users/$USER/AppData/Local/@opencode-aidesktop-updater/installer.exe
ls -lh /c/Users/$USER/AppData/Local/@zcodedesktop-updater/installer.exe

# IDE caches (Antigravity, etc.)
timeout 15 du -sh /c/Users/$USER/AppData/Roaming/Antigravity/* 2>/dev/null | sort -rh | head -10

# GPU shader caches
timeout 10 du -sh /c/Users/$USER/AppData/Local/AMD/* 2>/dev/null | sort -rh | head -10

# HuggingFace model cache (often the single biggest item)
du -sh /c/Users/$USER/.cache/huggingface/hub 2>/dev/null

# User-level cache dir
timeout 15 du -sh /c/Users/$USER/.cache/* 2>/dev/null | sort -rh | head -10

# Old large Downloads
timeout 15 du -sh /c/Users/$USER/Downloads/* 2>/dev/null | sort -rh | head -15
```

### Delete known-safe application caches

```bash
# Browser cache dirs (Brave shown; repeat for Chrome/Edge)
rm -rf "/c/Users/$USER/AppData/Local/BraveSoftware/Brave-Browser/User Data/Default/Cache"
rm -rf "/c/Users/$USER/AppData/Local/BraveSoftware/Brave-Browser/User Data/Default/Code Cache"
rm -rf "/c/Users/$USER/AppData/Local/BraveSoftware/Brave-Browser/User Data/Default/Service Worker"
rm -rf "/c/Users/$USER/AppData/Local/BraveSoftware/Brave-Browser/User Data/Default/Media Cache"
rm -rf "/c/Users/$USER/AppData/Local/BraveSoftware/Brave-Browser/User Data/Default/IndexedDB"
rm -rf "/c/Users/$USER/AppData/Local/BraveSoftware/Brave-Browser/User Data/Default/GPUCache"

# VS Code workspace storage
rm -rf /c/Users/$USER/AppData/Roaming/Code/User/workspaceStorage

# Electron updater cached installers (delete the .exe, keep metadata)
rm -f /c/Users/$USER/AppData/Local/@mmx-agentelectron-updater/installer.exe
rm -f /c/Users/$USER/AppData/Local/@opencode-aidesktop-updater/installer.exe
rm -f /c/Users/$USER/AppData/Local/@zcodedesktop-updater/installer.exe
rm -rf /c/Users/$USER/AppData/Local/@opencode-aidesktop-updater/pending
rm -rf /c/Users/$USER/AppData/Local/@zcodedesktop-updater/pending

# IDE caches (Antigravity example)
rm -rf /c/Users/$USER/AppData/Roaming/Antigravity/Cache
rm -rf /c/Users/$USER/AppData/Roaming/Antigravity/CachedData
rm -rf /c/Users/$USER/AppData/Roaming/Antigravity/Crashpad
rm -rf /c/Users/$USER/AppData/Roaming/Antigravity/CachedExtensionVSIXs
rm -rf /c/Users/$USER/AppData/Roaming/Antigravity/GPUCache

# HuggingFace model cache (7-10 GB typical — all re-downloadable)
rm -rf /c/Users/$USER/.cache/huggingface/hub

# GPU shader caches
rm -rf /c/Users/$USER/AppData/Local/AMD/DxCache
rm -rf /c/Users/$USER/AppData/Local/AMD/OglCache
rm -rf /c/Users/$USER/AppData/Local/AMD/OglpCache
rm -rf /c/Users/$USER/AppData/Local/AMD/VkCache
rm -rf /c/Users/$USER/AppData/Local/AMD/GLCache
rm -rf /c/Users/$USER/AppData/Local/AMD/DxcCache
rm -rf /c/Users/$USER/AppData/Local/AMD/RadeonSoftware
rm -rf /c/Users/$USER/AppData/Local/AMD/CN

# Puppeteer / Codex / OpenCode caches
rm -rf /c/Users/$USER/.cache/puppeteer
rm -rf /c/Users/$USER/.cache/codex-runtimes
rm -rf /c/Users/$USER/.cache/opencode
```

## Phase 3 — Software Audit (identify large unused programs)

When the user still wants more space after Phases 1 and 2, scan installed
software and identify candidates for uninstallation.

### Measure Program Files sizes
```bash
# Biggest dirs in Program Files
timeout 20 du -sh "/c/Program Files"/* 2>/dev/null | sort -rh | head -15
timeout 20 du -sh "/c/Program Files (x86)"/* 2>/dev/null | sort -rh | head -15
```

### Present as a structured table with categories

| Category | Typical suspects | Typical size |
|----------|-----------------|-------------|
| Android SDK | `C:\Program Files\Android` | ~3 GB |
| Docker | `C:\Program Files\Docker` | ~2.7 GB |
| Embedded dev | Arduino IDE, Creality (3D print) | ~0.5-1 GB each |
| Runtimes | Erlang OTP, Python venvs, Node | varies |
| Remote tools | AnyDesk, AudioRelay, Angry IP | ~20-100 MB |
| Amazon/AWS tools | `C:\Program Files\Amazon` | ~166 MB |

Present the user with a **multi-select choice list** (clarify tool with
multi_select=true) so they pick what to delete without risking unwanted removal.
Never uninstall software without explicit user approval.

### Windows Component Store (WinSxS) cleanup
```bash
# Analyze first (slow, 30-60s)
timeout 60 dism /Online /Cleanup-Image /AnalyzeComponentStore

# Clean if reclaimable space > 1 GB
timeout 120 dism /Online /Cleanup-Image /StartComponentCleanup
```
Note: `dism` is very slow and may timeout. Run it early in the background if
you need it.

## Pitfall — Browser/app locks while running
Brave, Chrome, Edge, VS Code, and Antigravity hold file locks on their cache
databases (LevelDB LOCK/MANIFEST/LOG files). `rm -rf` deletes everything it
can (often 80-90%) but leaves locked files. The remaining files auto-free when
the user closes the app or reboots. Don't warn excessively — say "some files
were locked by running apps; a reboot will clear the rest."

## Pitfall — Aggressive cleanup interaction pattern
When a user says "I need more space" after Phase 1, do NOT silently delete
Phase 2/3 items. Instead: measure → present a structured table → ask with
clarify(multi_select=true). Users want to see what's taking space and choose.
This builds trust and avoids wiping something they value.
