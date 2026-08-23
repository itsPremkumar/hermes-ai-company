# AVS Reel Generation — End-to-End (modular CLI)

Concrete, verified recipe for turning captured browser screenshots into a
9:16 Reel with the Automated-Video-Generator agentic pipeline, using the
**modular CLI** (`npm run agentic:modular`) which supports a `--file` flag for
a dedicated job file (so you never touch the big `agentic-scripts.json`).

Project root assumed: `C:\one\Automated-Video-Generator` (also reachable as
`/c/one/Automated-Video-Generator` in bash).

---

## 1. Capture screenshots (browser tools)

```
browser_navigate("https://sproutern.com")
browser_vision(question="Full page screenshot of the hero", annotate=false)
  -> screenshot_path returned (PNG)
```
The screenshot is saved even if the vision analysis fails — use `screenshot_path`.
Copy into the asset dir:
```bash
cp "<screenshot_path>" input/visuals/sproutern-hero.png
```
Capture 4–6 pages (home, tools, interviews, about, github). Each is a very TALL
full-page PNG (e.g. 1350x21525) — crop the top to 9:16 before render (see §4).

## 2. Write a dedicated job file (DO NOT edit agentic-scripts.json)

`input/scripts/sproutern-reel-job.json`:
```json
[
  {
    "id": "sproutern_reel",
    "title": "Sproutern — Free Career Platform for Students",
    "script": "90+ free tools. [Visual: sproutern-hero.png] [Grade: vivid] [Transition: fade]\nTired of paywalls? Sproutern is free forever. [Visual: sproutern-tools.png] [Grade: cool]\nReal interview experiences from Amazon, Google, Microsoft. [Visual: sproutern-interviews.png] [Grade: cinematic]\nCGPA converters, salary calculators, resume checkers. [Visual: sproutern-tools.png] [Grade: warm]\nBuilt by a student, for students. Open source, MIT. [Visual: sproutern-about.png] [Grade: cinematic]\nExplore it free today. [Visual: avs-github.png] [Grade: vivid]",
    "orientation": "portrait",
    "aspect": "9:16",
    "voice": "en-US-GuyNeural",
    "kokoroVoice": "af_heart",
    "hookFirst": true,
    "variablePacing": true,
    "backend": "agent",
    "candidatesPerAsset": 1,
    "captions": "burned",
    "captionTheme": "neon",
    "kineticText": true,
    "vignette": true,
    "musicQuery": "upbeat corporate technology",
    "kenBurns": true,
    "defaultVisual": "sproutern-hero.png",
    "intro": { "title": "Sproutern", "subtitle": "Free Career Platform", "durationSec": 2 },
    "outro": { "ctaText": "Search Sproutern", "durationSec": 2 }
  }
]
```
Notes:
- `kokoroVoice: "af_heart"` -> the repo's local Kokoro TTS (zero-config, no API
  key). The speech backend auto-starts from `venv/Scripts/python.exe` +
  `src/speech`. Do NOT set `TTS_PROVIDER=voicebox` unless a Voicebox repo exists.
- A `[Visual: file.png]` tag binds `localAsset` to the scene it sits in. Scenes
  WITHOUT a tag get keyword-based stock (Pexels) search — see the binding
  pitfall in §5.

## 3. Run the pipeline

The `pipeline` subcommand (plan->visuals->voice->render) **HANGS** at the
"Acquired N candidates" step (the gateway/verification stage between visuals and
voice never returns). Reliable workaround: run stages separately.

```bash
# voice alone — reuses plan + candidates on disk, generates Kokoro per scene
npm run agentic:modular -- voice --file input/scripts/sproutern-reel-job.json
# render alone — assembles the mp4 from plan/voice/candidates
npm run agentic:modular -- render --file input/scripts/sproutern-reel-job.json
```
- `voice` is SLOW: ~10–15s per scene; longer text scenes can stall up to ~2 min.
  It reuses completed scenes on re-run ("reused"/"done"), so re-running is safe.
- `render` emits `output/sproutern_reel/<title>.mp4` (~720x1280, 9:16).
Run both in background with `terminal(background=true, notify_on_complete=true)`
and `process(action="wait")`.

## 4. Crop full-page screenshots to 9:16

Browser full-page shots are very tall. Crop the top to 9:16 BEFORE render so the
hero content shows (cover-crop in render would otherwise show the page middle).
Use a `.sh` script with RELATIVE ffmpeg paths (absolute `/c/one/...` paths fail
with native ffmpeg — see avs-visual-frame-qa path gotcha).

`scripts/crop_visuals.sh`:
```bash
#!/bin/bash
cd /c/one/Automated-Video-Generator
FF="./node_modules/ffmpeg-static/ffmpeg.exe"
for f in sproutern-hero sproutern-tools sproutern-interviews sproutern-about avs-github; do
  src="input/visuals/$f.png"
  DIM=$("$FF" -i "$src" 2>&1 | grep -oE '[0-9]+x[0-9]+' | head -1)
  W=$(echo "$DIM" | cut -dx -f1); H=$(echo "$DIM" | cut -dx -f2)
  CH=$(( W * 16 / 9 )); [ "$CH" -gt "$H" ] && CH=$H
  "$FF" -y -i "$src" -vf "crop=${W}:${CH}:0:0" "input/visuals/_c_$f.png" >/dev/null 2>&1
  mv -f "input/visuals/_c_$f.png" "$src"
  echo "$f -> ${W}x${H} cropped to ${W}x${CH}"
done
```
(Inline `ff=...` variable in a `for` loop fails with exit 127 under MSYS — put
the command in a script file and `bash scripts/crop_visuals.sh`.)

## 5. Local-asset binding PITFALL (the #1 thing that bites)

The `render` subcommand reads **`render-manifest.json`**, NOT `plan.json`.
`render-manifest.json` is (re)written only by the `visuals` stage and points each
scene at a downloaded Pexels `.mp4` unless that scene had a `[Visual:]` tag.

Symptom: you edit `plan.json` `localAsset` to force your screenshots, re-run
`render`, and STILL get stock footage (lathe, tired woman, etc.). Because render
ignored plan.json.

Fix — patch `render-manifest.json` directly so every scene points at your
screenshot:
```python
import json
p = r"C:\one\Automated-Video-Generator\workspace\jobs\sproutern_reel\render-manifest.json"
d = json.load(open(p))
visuals = r"C:\one\Automated-Video-Generator\input\visuals"
bind = {1:"sproutern-tools.png", 2:"sproutern-interviews.png", 3:"sproutern-hero.png",
        5:"sproutern-about.png", 8:"sproutern-about.png", 10:"sproutern-hero.png"}
for a in d["assets"]:
    if a.get("sceneIndex") in bind:
        a["kind"] = "image"
        a["localPath"] = f"{visuals}\\{bind[a['sceneIndex']]}"
        a["license"] = "User-supplied — owner attribution"; a["licenseUrl"] = ""
json.dump(d, open(p,"w"), indent=2)
```
Then re-run `render`. Verify with frame extraction (§6).

Best practice: put a `[Visual: file.png]` tag in EVERY scene's text up front so
`localAsset` is set on all scenes during planning and the manifest already binds
them — avoids the post-hoc patch.

## 6. Verify empirically (AVS bar)

```bash
FF="./node_modules/ffmpeg-static/ffmpeg.exe"
OUT="output/sproutern_reel/Sproutern — Free Career Platform for Students.mp4"
$FF -i "$OUT" 2>&1 | grep -oE '720x1280|Duration: [0-9:.]+'   # expect 720x1280, ~58s
$FF -y -ss 8  -i "$OUT" -frames:v 1 frames/v1.png 2>/dev/null
$FF -y -ss 22 -i "$OUT" -frames:v 1 frames/v2.png 2>/dev/null
$FF -y -ss 44 -i "$OUT" -frames:v 1 frames/v3.png 2>/dev/null
```
Then `vision_analyze` each frame (pass a `C:\...` Windows path — NOT `/c/one/...`,
which vision_analyze mangles) and confirm: Sproutern screenshot visible (not
stock), burned caption present and legible, 9:16 fill (no letterbox).

## 7. Move to Downloads

```bash
cp "output/sproutern_reel/Sproutern — Free Career Platform for Students.mp4" \
   "/c/Users/PREM KUMAR/Downloads/Sproutern Reel.mp4"
```
Always confirm the mp4 EXISTS (probe shows 720x1280) BEFORE moving — the
`pipeline` hang leaves no output, so "move the video" only works after a real
render completed.
