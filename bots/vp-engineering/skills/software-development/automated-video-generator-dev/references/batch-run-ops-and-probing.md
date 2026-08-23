# Batch Run Ops, Process Hygiene & Probe Timing (Windows)

Session-proven techniques for running AVS agentic batches on the 6GB RAM Windows
laptop and diagnosing silent deaths. Empirical, from real batch runs (2026-07-31
→ 2026-08-01).

## 1. ffprobe still-vs-video classification — NEVER `-count_frames`

Used by `visual-fx.ts` to pick zoompan `d` (real video → `d=1`, still source →
`d=sceneFrames`).

- **`ffprobe -count_frames` decodes EVERY frame.** On a 24s 4K clip it took
  **69 seconds** (576 frames). With a 20s execFileSync timeout the probe times
  out → returns 0 → a REAL video is misclassified as a still → zoompan
  `d=sceneFrames` explodes (each input frame → 75 output frames) → 90s ffmpeg
  timeout → corrupt partial MP4 (moov atom missing) left on disk.
- **Correct probe: read the stream CODEC, metadata-only, ~0.12s:**
  ```bash
  ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 <file>
  # h264 → real video; png/mjpeg → still (a .png reclassified to .mp4 by acquire)
  ```
- Classify: `codec in (png, mjpeg, bmp, gif, tiff, webp)` → still; anything else
  → video. On probe failure, default to **still** is wrong for videos — default
  to **video** (a still misread as video only drops the effect; a video misread
  as still explodes frame count).
- PNG-as-mp4 landmine: the acquire pipeline reclassifies `.png` downloads to
  `.mp4` filenames (codec=png, format=png_pipe, 1 frame, ~17KB). Probe codec,
  never trust extension or duration.

## 2. Zombie batch processes — the RAM crisis root cause

Symptom: batch "dies" with no `EXIT=` line, yet RAM keeps dropping to ~5MB free
and renders get OOM-killed.

Root cause found: **multiple agentic-batch node trees alive simultaneously**.
`taskkill /PID` against MSYS `ps` PIDs fails silently ("not found") — MSYS ps
PIDs are NOT Windows process IDs. Early "kills" only killed bash wrapper PIDs;
the real `node.exe` trees (npx → tsx → node) survived, froze, and each held
hundreds of MB. 4 zombies ≈ RAM collapse.

Reliable kill + verify recipe (PowerShell, works every time):
```powershell
# list real batch processes
Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'node.exe' -and $_.CommandLine -like '*agentic-batch*' } |
  Select-Object ProcessId, CreationDate, @{n='Cmd';e={$_.CommandLine.Substring(0,120)}}
# kill by exact PID
Stop-Process -Id <pid> -Force
# verify 0 remain (repeat the list query; also check ffmpeg: Get-Process ffmpeg)
```
Also kill leftover `ffmpeg.exe` orphans from a dead batch — they keep rendering
into nothing and hold 130–210MB each.

Post-kill sanity: RAM should jump back (e.g. 5MB → 450MB → 1.3GB). Then relaunch
with a NEW `AGENTIC_WORKSPACES_ROOT`; the 1.2GB shared asset cache
(`workspace/assets/cache`) makes the re-run fast.

## 3. Silent batch death — check for a REBOOT, not a crash

Twice a batch stopped with no EXIT line, no Windows crash events
(41/1074/6008/7034/7031/7023), no orphan processes. First suspicion: reboot.

```powershell
# system uptime in minutes — < 10 right after "death" ⇒ machine rebooted
(Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime | Select-Object -ExpandProperty TotalMinutes
```
Also inspect the workspace: `*.part` files mid-download = killed mid-acquire;
`.part` files with recent mtimes while log is stale = downloads progressing but
log buffered (do NOT kill; wait).

## 4. `music: false` job flag (added 2026-08-01)

Opt-out of background music → voice-only final. Wire path:
`AgenticCliJob.music?` (cli-job.ts) → `buildPipelineRequest` → `PipelineRequest.music?`
(orchestrator/types.ts) → `fetchMusic()` returns `[]` when `req.music === false`
(pipeline.ts) → acquire produces zero music candidates → compose skips music mix.
Log marker: `🎵 Background music disabled (music: false) — voice-only final`.
This completes the 9:16/1:1/16:9 × music/no-music variety matrix.

**VERIFYING a music-off final — do NOT use audio analysis.** The music bed is
ducked so deep (0.35 volume + ducking) that it sits below the noise floor:
silencedetect gap RMS was **-91 dB in BOTH** a music-on and a music-off final,
and full-length volumedetect means were within 1 dB of each other. You cannot
distinguish them acoustically. The ONLY reliable proof is pipeline-side:
1. The log marker fires **exactly once** per music:false job (grep -ac it — a
   music-on batch shows 0).
2. No music candidates in the workspace (`find workspace/<job> -name "*.mp3"`).
3. Single AAC audio stream + avs-verify speech proof (astats zcr) still pass.
If someone asks "prove the no-music video has no music", show the log line, not
an audio waveform.

Also note: `music: false` and `musicQuery`/`musicIntensity` are mutually
exclusive in a job config — remove the query fields when opting out.

## 5. Batch monitoring cadence that works

- `--parallel 1` (RAM-safe), workspace isolation env overrides
  (`AGENTIC_WORKSPACES_ROOT`, `AGENTIC_KEEP_WORKSPACES=25`).
- Poll with `grep -a "Wave [0-9]/N complete" log`, `grep -a EXIT= log`, RAM via
  `wmic OS get FreePhysicalMemory /value`.
- A stuck-looking render is often fine: check `Get-CimInstance Win32_Process`
  for a fresh `ffmpeg.exe` CreationDate and log-buffer staleness before killing.
- A config for `--file` MUST be a JSON **array**; an object keyed "0".."N" runs
  0 jobs instantly ("undefined jobs", EXIT=0).
- When a run is externally killed mid-batch, re-run only the missing jobs with a
  trimmed array config (reuse the cached assets) instead of restarting the full
  batch.
