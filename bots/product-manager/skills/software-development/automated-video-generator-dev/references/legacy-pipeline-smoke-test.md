# Legacy Pipeline Smoke Test (`npm run generate`)

Verified 2026-08-01: one clean sample video through the LEGACY path, end-to-end, with empirical QA.

## Path map (legacy ≠ agentic)
- `npm run generate` → `src/cli.ts` → `src/adapters/cli/cli-runner.ts` → `pipeline-app.service.ts` (`createJob`) → `video-generator.ts` → output + subtitles.
- Input file: `input/scripts/input-scripts.json` (single JSON array of jobs). **It is git-committed** — edit freely, restore with `git checkout -- input/scripts/input-scripts.json` (no manual .bak needed).
- Output: `output/<id>/<Title>.mp4` + `subtitles.srt` / `subtitles.vtt` (+ `details.txt`, `thumbnail.jpg`, `scene-data.json` when full pipeline runs).

## Pre-flight: concurrent-render guard (RAM crisis rule)
Before launching, check for a live agentic render — `workspace/jobs/` is transient and RAM rule is "1 video at a time":
```bash
powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -in @("ffmpeg.exe","node.exe") } | Select-Object ProcessId, Name, @{N="MB";E={[int]($_.WorkingSetSize/1MB)}}, CommandLine | Format-List'
```
If ffmpeg is encoding (`zoompan`/`drawtext` filter in CommandLine) → a job is mid-render. Wait for it (poll `ls -lt workspace/jobs/<job>/render/` for new `_seg_*.mp4`), then run. Never run legacy concurrently.

## Sample job pattern
Use **existing local visuals** (zero network risk, deterministic):
```json
[{
  "id": "legacy-sample",
  "title": "Nature in Motion - Legacy Pipeline Sample",
  "script": "The ocean waves crash against the golden shore at sunrise. [Visual: ai_ocean.jpg]\nTowering mountains rise above the misty valley. [Visual: ai_mountains.jpg]\nGalaxies swirl in the dark night sky above the desert. [Visual: ai_galaxy.jpg]\nNature is the oldest story ever told. [Visual: ai_desert.jpg]",
  "orientation": "landscape",
  "voice": "en-US-GuyNeural",
  "showText": true,
  "language": "english"
}]
```
NOTE: the committed `avs-promo-reel` job references `logo-automation.png` / `github-profile.png` which do NOT exist in `input/visuals/` — don't reuse it as a smoke test.

## Run + verify
```bash
npm run generate   # ~1.5 min for 4 scenes; exit 0 + 'Completed "..."' = success
```
ffprobe — use `node_modules/ffprobe-static/bin/win32/x64/ffprobe.exe` (there is NO `node_modules/.bin/ffprobe`; system chocolatey ffprobe also works):
```bash
ffprobe -v error -show_entries format=duration,size,bit_rate -show_entries stream=codec_name,width,height,r_frame_rate,pix_fmt,sample_rate,channels -of default=noprint_wrappers=1 "output/legacy_sample/<Title>.mp4"
```
Expect: h264 1920x1080@30fps (landscape), aac 48kHz stereo, ~17s for 4 scenes.

Pixel QA (REAL frames only — `-ss` AFTER `-i`):
```bash
ffmpeg -hide_banner -i in.mp4 -vf "cropdetect,blackdetect=d=0.2:pix_th=0.10,freezedetect=n=-50dB:d=1.0" -an -f null - 2>&1 | grep -E "black_start|freeze_start"
```
Audio presence — `volumedetect` (astats ZCR metadata key did NOT extract via ametadata print; volumedetect is the reliable speech check):
```bash
ffmpeg -hide_banner -i in.mp4 -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"
```
Real voice ≈ mean −20..−30 dB, max ≥ −10 dB.

## PITFALL: freezedetect "freeze" events on still-image scenes are BY-DESIGN on legacy
- Legacy path (`video-generator.ts`) renders still images **statically — no Ken Burns**. Ken Burns zoompan exists ONLY on the agentic path (`src/agentic/orchestrator/render.ts:804` `zoompan=z='1+0.04*time'...`, `src/agentic/plugins/motion/ken-burns-pro.ts`). `grep zoompan src/ --include=*.ts` returns hits only under `src/agentic/`.
- So freezedetect will flag one "freeze" span per scene (spans align exactly with scene boundaries). NOT a defect — verify before reporting.
- Prove static-vs-frozen with SSIM between two frames 1s apart mid-scene:
```bash
ffmpeg -hide_banner -ss 7.0 -i in.mp4 -frames:v 1 -vf scale=320:-1 /tmp/f1.png -y
ffmpeg -hide_banner -ss 8.0 -i in.mp4 -frames:v 1 -vf scale=320:-1 /tmp/f2.png -y
ffmpeg -hide_banner -i /tmp/f1.png -i /tmp/f2.png -lavfi ssim -f null - 2>&1 | grep -oE "All:[0-9.]+"
```
SSIM ≈ 0.99999 = truly static frames → expected for legacy stills. A working Ken Burns pan gives SSIM measurably < 1.0.

## MSYS gotcha (reconfirmed)
Bash eats `$` inside double-quoted PowerShell → ALWAYS single-quote PowerShell commands in git-bash: `powershell -NoProfile -Command '...'`.
