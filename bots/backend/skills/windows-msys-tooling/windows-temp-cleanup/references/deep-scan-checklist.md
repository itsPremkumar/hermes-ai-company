# Deep Scan Checklist — Beyond Temp

This reference captures the full scan + categorization pattern from a real cleanup
session on a 474 GB Windows C: drive. Use these commands in Phase 2/3 to find
every recoverable GB before resorting to asking the user about personal files.

## Tier 1 — User Cache Directory (`~/.cache`)

### HuggingFace Hub (7-10 GB common)
```bash
du -sh /c/Users/$USER/.cache/huggingface/hub
# Delete: rm -rf /c/Users/$USER/.cache/huggingface/hub
```
Model weights cache. Every file is re-downloadable from HuggingFace Hub.
Single biggest space-recovery opportunity on machines that use AI tools.

### Puppeteer Browser Binary (1.2 GB)
```bash
du -sh /c/Users/$USER/.cache/puppeteer
```
Chromium downloaded by Puppeteer for web scraping. Re-download with:
`npx puppeteer browsers install chrome`

### Codex CLI Runtimes (1.2 GB)
```bash
du -sh /c/Users/$USER/.cache/codex-runtimes
```
Runtime builds cached by OpenAI Codex CLI. Regenerated on next use.

### OpenCode Cache (~80 MB)
```bash
du -sh /c/Users/$USER/.cache/opencode
```
Agent operation cache. Safe to delete.

## Tier 2 — Browser Caches

### Brave Browser (3-4 GB common)
```bash
timeout 20 du -sh "/c/Users/$USER/AppData/Local/BraveSoftware/Brave-Browser/User Data/Default"/* | sort -rh | head -10
```
| Sub-folder | Typical size | Safe? |
|---|---|---|
| Cache | 200-300 MB | ✅ |
| Code Cache | 500-600 MB | ✅ |
| Service Worker | 1-2 GB | ✅ |
| Media Cache | 0-10 MB | ✅ |
| IndexedDB | 100-200 MB | ✅ |
| GPUCache | 10-100 MB | ✅ |
| File System | 0-1 MB | ⚠️ (may have site data) |

### Chrome / Edge (similar profile)
Paths differ slightly:
```bash
# Chrome
"/c/Users/$USER/AppData/Local/Google/Chrome/User Data/Default/Cache"
# Edge
"/c/Users/$USER/AppData/Local/Microsoft/Edge/User Data/Default/Cache"
```

## Tier 3 — Electron App Updater Cached Installers

After an Electron app auto-updates, the downloaded `.exe` installer often stays
behind in `AppData/Local/@<app>-updater/installer.exe`. These are **already
applied** and can be safely deleted.

| Path | Typical size |
|---|---|
| `@mmx-agentelectron-updater/installer.exe` | 400 MB |
| `@opencode-aidesktop-updater/installer.exe` | 119 MB |
| `@opencode-aidesktop-updater/pending/` | 119 MB |
| `@zcodedesktop-updater/installer.exe` | 133 MB |
| `@zcodedesktop-updater/pending/` | 64 MB |

## Tier 4 — IDE / Editor Caches

### VS Code workspaceStorage (1-2 GB)
```bash
du -sh /c/Users/$USER/AppData/Roaming/Code/User/workspaceStorage
```
VSCode workspace metadata. Safe to delete — regenerated per-project.

### Antigravity IDE (~1.4 GB in Roaming)
```bash
timeout 15 du -sh /c/Users/$USER/AppData/Roaming/Antigravity/* | sort -rh | head -10
```
| Cache folder | Typical size |
|---|---|
| WebStorage | ~450 MB |
| User (profile data) | ~440 MB |
| CachedExtensionVSIXs | ~240 MB |
| Cache | ~100 MB |
| Crashpad | ~100 MB |
| CachedData | ~50 MB |

## Tier 5 — GPU Shader Caches

### AMD (2-3 GB after heavy gaming/rendering)
```bash
timeout 10 du -sh /c/Users/$USER/AppData/Local/AMD/* | sort -rh | head -10
```
Shader compilation caches. Auto-rebuilds when the app runs again. Locked files
may remain if the GPU driver is active.

## Tier 6 — Program Files Size Audit

```bash
timeout 20 du -sh "/c/Program Files"/* | sort -rh | head -15
timeout 20 du -sh "/c/Program Files (x86)"/* | sort -rh | head -15
```

Common large candidates:
| Software | Path | Size | Notes |
|---|---|---|---|
| Android SDK | `C:\Program Files\Android` | ~3.1 GB | Only if not doing Android dev |
| Docker | `C:\Program Files\Docker` | ~2.7 GB | Check `docker system df` too |
| Arduino IDE | `C:\Program Files\Arduino IDE` | ~540 MB | |
| Creality Print | `C:\Program Files\Creality` | ~535 MB | 3D printer slicer |
| Erlang OTP | `C:\Program Files\Erlang OTP` | ~430 MB | Needed for Elixir/RabbitMQ |
| Amazon | `C:\Program Files\Amazon` | ~170 MB | |
| AudioRelay | (x86) `AudioRelay` | ~110 MB | Stream audio to phone |
| AnyDesk | (x86) `AnyDesk` | ~11 MB | Remote desktop |

## Tier 7 — Windows Component Store (WinSxS)

```bash
# Analyze — slow (30-60s)
timeout 60 dism /Online /Cleanup-Image /AnalyzeComponentStore
# Clean
timeout 120 dism /Online /Cleanup-Image /StartComponentCleanup
```

## Interaction Pattern: Present → Ask → Execute

Do NOT silently delete Phase 2/3 items. Use this flow:

1. **Measure** all tiers above (batch with bounded timeouts)
2. **Present** a structured table showing each item + size + risk level
3. **Ask** with `clarify(choices=[...], multi_select=true)`
4. **Execute** only the user-selected items
5. **Verify** with `df -h /c` and report net gain
