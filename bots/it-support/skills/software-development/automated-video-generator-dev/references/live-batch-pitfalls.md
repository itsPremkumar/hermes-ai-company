# Live-Batch Pitfalls & Verified Fixes (2026-08)

Session-proven findings from running curated agentic batches on the 6GB
Lenovo laptop. Trust these over guesses; each was root-caused with real
ffprobe/process evidence.

## 1. Ken Burns: probe the CODEC, never `-count_frames`

**Symptom chain:** `fx_*_kb.mp4` occasionally corrupt ("moov atom not
found") with a large partial size (13.9MB), while siblings are valid. The
final still PASSES because compose falls back to the original clip — but the
scene silently loses its Ken Burns effect.

**Root cause:** `ffprobe -count_frames` DECODES every frame. On a 24s 4K
clip (576 frames, 40MB) that took **69 seconds** — past the 20s probe
timeout. The probe returned 0 → `isStill = (0 <= 1) = true` → zoompan used
`d=75` on a REAL video → 75 output frames per input frame (~43k frames) →
90s execFileSync timeout → ffmpeg killed mid-write → corrupt partial left on
disk (inert; `run()`'s readability guard returns the original input).

**Fix (committed, `visual-fx.ts`):** classify still-vs-video by the video
stream's **codec_name** — metadata-only, **0.12s** vs 69s (575× faster):

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 FILE
# → h264/h265/av1/vp9 = real video (d=1, pass-through)
# → png/mjpeg/bmp/gif/tiff/webp = still (a .png reclassified to .mp4 by
#   acquire — d=sceneFrames so the zoom animates ~3s)
```

Failure direction matters: probe failure → assume STILL. A still
misclassified as video just drops the effect; a video misclassified as
still EXPLODES frame count (timeout + corrupt partial).

**Mnemonic:** for per-frame logic on this pipeline, probe `codec_name`, not
frame counts.

## 2. Zombie batches: wrapper kills leave the real node trees alive

**Symptom:** RAM collapses to ~5MB free mid-batch; the run dies with no
`EXIT=` line. Repeated kills via `taskkill` on MSYS `ps` PIDs report
SUCCESS but the batch keeps coming back.

**Root cause:** the PIDs from MSYS `ps` are bash-wrapper PIDs, NOT the real
`node.exe`/`npx` trees. Killing the wrapper leaves the actual node process
running. Over a session, **four agentic-batch node trees accumulated
simultaneously** — each holding node+ffmpeg memory — starving the machine.

**Verified kill recipe (real node PIDs):**
```bash
# list REAL batch node PIDs:
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.Name -eq 'node.exe' -and \$_.CommandLine -like '*agentic-batch*' } | Select-Object ProcessId,CreationDate | Format-List"
# kill each exact PID (works where taskkill fails):
powershell -NoProfile -Command "Stop-Process -Id <pid> -Force"
```

**Verification is mandatory:** after killing, confirm
`(Get-CimInstance ... 'agentic-batch').Count` returns **0** (mind pipeline
self-matching: the query's own command line contains 'agentic-batch' —
filter `Name -eq 'node.exe'` and exclude powershell/bash). A "SUCCESS"
taskkill message is NOT evidence the process died.

**Lesson:** never trust MSYS ps PIDs for Windows kills; enumerate by
CommandLine filter and Stop-Process, then verify zero remain.

## 3. Batch died with no EXIT line → check system uptime FIRST

A silent batch death (no `EXIT=` in log) on this box is most often the
**machine rebooting** (Windows update / overnight restart), not a pipeline
bug:

```bash
powershell -NoProfile -Command "(Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime | Select-Object -ExpandProperty TotalMinutes"
```

Uptime < ~10 min after a death = reboot killed it. Also check System log
for Id 41/1074/6008 (crash/restart) and Id 42/107 (sleep/wake). No crash
events + no sleep events + fine RAM = silently killed externally (network
drop or third-party process); that is the "batch 3 / bees" pattern.

**Recovery:** relaunch the SAME jobs; the 1.2GB asset cache at
`workspace/assets/cache` (65 files) survives reboots, so re-runs are fast.
Always `AGENTIC_WORKSPACES_ROOT=<fresh>/workspace/batch2X` + `--parallel 1`.

## 4. Mid-write probe race: files grow while ffmpeg writes

Probing an fx file WHILE ffmpeg is still writing gives false positives:
"moov atom not found" + a small size (e.g. 197KB), then the same file reads
13.9MB valid minutes later. Before declaring a file corrupt, check
**mtime/size stability across ~5s**:

```bash
for i in 1 2 3; do stat -c "%s %y" FILE; sleep 2; done
```

If size is still changing, the file is mid-write — wait, then re-probe.
Only a stable size + `moov atom not found` is real corruption.

## 5. 1:1 square orientation is proven

`preset: "square"` → `orientation: 'portrait', aspect: '1:1'`
(`VIDEO_FORMAT_PRESETS` in `src/agentic/config.ts`). A full 5-job batch
with 16:9×2 + 9:16×2 + 1:1×1 all verified PASS (avs-verify.sh), including
Ken Burns on all scenes. The variety matrix (9:16 / 1:1 / 16:9) is now
complete and can be mixed in one config.

## 6. Batch CLI: --file config must be a JSON ARRAY

An object keyed "0".."4" silently runs 0 jobs ("undefined jobs", instant
EXIT=0). Trimming a config programmatically:

```bash
node -e "
const full = require('./input/scripts/agentic-scripts.json');
require('fs').writeFileSync('./out.json', JSON.stringify([full[3], full[4]], null, 2));
"
```

## 7. Don't trust `ls` size field on MSYS

`ls -la | awk '{print $5}'` prints a wrong/stale size field on this box
(identical 197121 for every file). Use `stat -c %s FILE` for real sizes.
