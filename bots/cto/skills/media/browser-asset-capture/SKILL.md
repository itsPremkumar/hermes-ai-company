---
title: Browser Asset Capture
name: browser-asset-capture
description: >-
  Capture live web page screenshots via Hermes Agent's headless browser
  (browser_navigate + browser_vision) and use them as visual assets in
  video/media generation pipelines. Works with any pipeline that supports
  local file references (e.g., Automated-Video-Generator's [Visual: filename]
  tag system).
---

# Browser & Desktop Asset Capture

Use Hermes Agent's **three capture methods** to collect real visual assets and feed them directly into video/media generation pipelines.

## Three Capture Methods

| Method | Tool | Captures | Best For |
|--------|------|----------|----------|
| **🌐 Browser** | `browser_navigate` + `browser_vision()` | Any public web page (PNG) | GitHub profile, repo README, docs, dashboards |
| **🖥️ Desktop Window** | `computer_use capture(app='Code')` | Any running application window | VS Code, terminal, File Explorer, media player |
| **🎨 Custom HTML** | `write_file()` + `browser_navigate()` | Branded rendered HTML/CSS | Title cards, infographics, code showcases |

## When To Use

- You need a **live screenshot** of a web page, an app, or a custom-created graphic as a video scene
- You're generating a **promo reel / walkthrough / portfolio video** that includes real content
- The page/app is accessible and you want pixel-perfect rendering
- You want to avoid manual Snipping-Tool / PrintScreen steps — let the agent do it

---

## Method 1: Browser Screenshots

```
browser_navigate(url)  →  browser_vision()  →  screenshot.png  →  input/visuals/  →  [Visual: screenshot.png]  →  render
```

| Step | Tool | What Happens |
|------|------|-------------|
| 1 | `browser_navigate(url)` | Opens headless Chromium, loads page (JS/CSS/images fully render) |
| 2 | `browser_vision(question)` | Takes a PNG screenshot — **path returned even if vision analysis fails** |
| 3 | `cp screenshot.png input/visuals/` | Copy into the pipeline's asset directory |
| 4 | `[Visual: filename.png]` | Reference in script — pipeline uses it if file exists, falls back to stock media if not |
| 5 | Pipeline render | Image auto-detected as `type: 'image'` at orientation-adjusted resolution |

### Steps

1. **Navigate** — `browser_navigate(url="https://github.com/user/repo")`
2. **Capture** — `browser_vision(question="Full page screenshot", annotate=false)`
   - `annotate=false` → clean screenshot, no overlays
   - `annotate=true` → numbered element labels (useful for QA/targeting, not for clean assets)
3. **Check the result** — The response includes `screenshot_path` (absolute path to PNG). Vision analysis may fail (e.g., provider 400 error) but **the screenshot is still saved** — don't re-capture if vision fails.
4. **Copy to asset dir** — `cp <screenshot_path> input/visuals/<name>.png`
5. **Verify it's there** — `ls input/visuals/`
6. **Write script** — Include `[Visual: <name>.png]` tags in the narration script
7. **Generate** — `npm run generate` (legacy) or `npm run generate:agentic` (agentic)

### Multi-Page / Scrolling Pages

```
browser_navigate(url)
browser_vision()                     # Screenshot 1 — above the fold
browser_scroll(direction="down")     # Scroll
browser_vision()                     # Screenshot 2 — next section
browser_scroll(direction="down")
browser_vision()                     # Screenshot 3 — bottom
```

Name each uniquely: `github-top.png`, `github-mid.png`, `github-bottom.png`.

---

## Method 2: Desktop Window Capture

```
computer_use capture(app='Code')  →  screenshot with element overlay  →  copy to input/visuals/  →  [Visual: vscode.png]
```

| Step | Tool | What Happens |
|------|------|-------------|
| 1 | `computer_use capture(mode='vision', app='AppName')` | Captures the specified window (even if hidden/minimized) |
| 2 | Get screenshot from response | Save path varies; use `cp` from the temp/cache location |
| 3 | `cp <path> input/visuals/<name>.png` | Copy into the pipeline's asset directory |
| 4 | `[Visual: <name>.png]` in script | Reference like any local asset |

### Getting Clean Screenshots (no overlays)

Use `mode='vision'` for a plain screenshot without numbered element overlays. Use `mode='som'` for QA/debugging (numbered elements visible).

### Common App Names for capture()

| App Window | `app` value | Use Case |
|------------|-------------|----------|
| VS Code | `'Code'` | Show project code in action |
| Chrome | `'Chrome'` | Show a specific web app |
| File Explorer | `'explorer'` | Show project file structure |
| Windows Terminal | `'Windows Terminal'` | Show CLI commands/results |
| Media Player | `'Windows Media Player'` | Show rendered video preview |
| Any window | `'screen'` or `'desktop'` | Capture the whole desktop |

### ⚠️ CUA Session Lifecycle

- CUA driver sessions may expire after inactivity. If capture fails with `session has ended`, run `hermes computer-use doctor` in the terminal to restart, then retry.
- On Windows, `computer_use` can capture ANY window including those behind other windows — **no need to bring to front**.

---

## Method 3: Custom HTML → Title Cards

Generate branded assets by writing HTML/CSS and screenshotting it:

```
write_file('card.html', html_content)  →  browser_navigate('card.html')  →  browser_vision()  →  title-card.png
```

### Example: Branded Title Card

```html
<html>
<body style="background:linear-gradient(135deg,#667eea,#764ba2);
             width:1080px; height:1920px;
             display:flex; align-items:center; justify-content:center;
             font-family:sans-serif; color:white; text-align:center;">
  <div>
    <img src="input/visuals/logo.png" width="300">
    <h1 style="font-size:80px; margin:40px 0;">Video Title</h1>
    <p style="font-size:40px; opacity:0.8;">by Author</p>
  </div>
</body>
</html>
```

Match dimensions to your target aspect ratio:
- Portrait (9:16) → 1080×1920
- Landscape (16:9) → 1920×1080
- Square (1:1) → 1080×1080

---

## Asset Directory

All captured assets go to **`input/visuals/`** — the same directory the pipeline reads for `[Visual: ...]` tags.

```
project-root/
├── input/
│   ├── visuals/           ← 📁 ALL captured/local assets go here
│   │   ├── logo.png              (from your assets/)
│   │   ├── github-profile.png    (from browser capture)
│   │   ├── vscode-code.png       (from desktop capture)
│   │   ├── title-card.png        (from custom HTML capture)
│   │   └── contribution-graph.png(from browser capture)
│   └── scripts/
│       ├── input-scripts.json          (legacy pipeline)
│       ├── agentic-scripts.json        (agentic pipeline)
│       └── agentic-scripts.example.json
```

The `inputAssetPath()` function (`src/lib/path-safety.ts`) resolves to **`input/visuals/`**, not `input/input-assets/`.

---

## How Pipelines Resolve Local Assets

### Legacy Pipeline (`npm run generate`)

Uses `input/scripts/input-scripts.json`:
```json
[{
  "script": "[Visual: logo.png] About my project. [Visual: team-photo.jpg]",
  "voice": "en-US-GuyNeural",
  "orientation": "portrait"
}]
```

Resolution in `src/video-generator.ts`:
1. `parseScript()` extracts `[Visual: filename]` tags
2. Checks `inputAssetPath(filename)` (`input/visuals/`) for file existence
3. If exists → copy to workspace, set type (image/video by extension), extract duration for videos
4. If NOT found → treat tag text as stock media search keywords

### Agentic Pipeline (`npm run generate:agentic`)

Uses `input/scripts/agentic-scripts.json`:
```json
[{
  "script": "[Visual: logo.png] About my project. [Visual: team-photo.jpg]",
  "orientation": "portrait",
  "backend": "agent"
}]
```

**Three paths for local assets:**

**Path 1 — `[Visual: ...]` tag in custom script (NEW):**
When `req.script` is provided, the pipeline uses it directly via `parseScript()`. Scenes with existing `localAsset` (from file-found tags) are **NOT overwritten** by auto-detection (fixed in this session).

**Path 2 — `localAssets` parameter (agentic-native):**
```typescript
localAssets?: string[];  // Filenames in input/visuals/
// Only binds to scenes WITHOUT existing localAsset (from tags)
for (const s of plan.scenes) {
    if (!s.localAsset) {
        s.localAsset = files[i % files.length];
    }
}
```

**Path 3 — Auto-detection (automatic fallback):**
Scans `input/visuals/` for media files, binds to scenes without existing `localAsset`:
```typescript
const files = fs.readdirSync(assetsDir).filter(f => LOCAL_MEDIA_RE.test(f));
let li = 0;
for (const s of plan.scenes) {
    if (!s.localAsset) {
        s.localAsset = files[li % files.length];
        li++;
    }
}
```

### ⚠️ Important: `.env` Loading for Agentic CLI

The agentic CLI (`agentic-cli.ts`) requires `import 'dotenv/config'` at the top of the file to load environment variables. Without this, `TTS_PROVIDER`, `VOICEBOX_*`, and other `.env` vars are NOT available. This was a discovered fix in this session — when running `npm run generate:agentic`, the `.env` is loaded by `agentic-cli.ts`.

### ⚠️ Known Gap: Video Duration Not Auto-Adjusted

The legacy pipeline extracts video duration (`getVideoMetadata()` → `videoDuration`) and adjusts scene timing. The agentic pipeline **does NOT** auto-adjust `durationSec` for video assets — it keeps the text-calculated duration. If using a 30s video clip, the scene may be cut short. This is fixable in `acquire.ts` after the local asset is copied.

---

## AVS Reel End-to-End (modular CLI — the reliable path)

`npm run generate:agentic` runs `agentic-cli.ts`, which reads `input/scripts/agentic-scripts.json`
and **runs ALL jobs** — risky to edit, and the full `pipeline` hangs. Use the
**modular CLI** instead: `npm run agentic:modular -- <subcommand> --file <jobfile.json>`.
It accepts a `--file` flag, so you can keep a dedicated job file (e.g.
`input/scripts/sproutern-reel-job.json`) and never touch the big array.

**Subcommands:** `plan`, `visuals`, `voice`, `render`, `pipeline`, `edit`, `list`.

### ⚠️ CRITICAL: `pipeline` subcommand HANGS
`npm run agentic:modular -- pipeline` stalls forever at the *"Acquired N candidates"*
line (the gateway/verification stage between visuals and voice never returns).
**Do not wait on it.** Kill it and run the stages separately:
```bash
npm run agentic:modular -- voice --file input/scripts/<job>.json   # Kokoro per scene, ~10–15s each
npm run agentic:modular -- render --file input/scripts/<job>.json  # assembles output/<id>/<title>.mp4
```
Both reuse on-disk plan/voice/candidates, so re-running is safe and idempotent.
Run them `terminal(background=true, notify_on_complete=true)`.

### ⚠️ CRITICAL: `render` reads `render-manifest.json`, NOT `plan.json`
If a scene's `[Visual: file.png]` tag was dropped (keyword treated as stock
search) and you patch `plan.json localAsset`, **`render` ignores it** — it reads
`workspace/jobs/<id>/render-manifest.json`, written by the visuals stage, which
points those scenes at downloaded Pexels `.mp4`. Symptom: re-render still shows
stock footage (lathe, tired woman…). Fix: patch `render-manifest.json` assets so
each scene's `localPath` points at `input/visuals/<your>.png` (`kind:"image"`),
then re-run `render`. Best practice: put a `[Visual: file.png]` tag in **every**
scene up front so `localAsset` is set during planning.

### Voice: local Kokoro, not Voicebox
The repo's `src/speech` (Kokoro) TTS is zero-config — auto-starts from
`venv/Scripts/python.exe`. Set `"kokoroVoice": "af_heart"` in the job. Do NOT set
`TTS_PROVIDER=voicebox` unless a separate Voicebox repo exists (it doesn't by default).

### Crop full-page screenshots to 9:16 BEFORE render
Browser captures are very tall (e.g. 1350×21525). Cover-crop at render shows the
page middle, not the hero. Crop the top to 9:16 first (see `references/avs-reel-workflow.md`
for the exact `scripts/crop_visuals.sh` — note: inline `ff=...` in a `for` loop
fails with exit 127 under MSYS; put it in a `.sh` file and `bash` it; use RELATIVE
ffmpeg paths, not `/c/one/...`).

### Verify before delivering (AVS bar)
`ffprobe` dimensions (expect 720×1280 for portrait) + extract 3 frames
(`ffmpeg -ss N -i … -frames:v 1`) + `vision_analyze` each (pass a `C:\...` Windows
path — `/c/one/...` gets mangled) to confirm: website screenshot visible (not
stock), burned caption legible, 9:16 fill. Only THEN copy to `Downloads`.

See `references/avs-reel-workflow.md` for the full copy-paste recipe.

## Pitfalls

- **Vision API may return 400** → the screenshot file is STILL captured and saved. Check `screenshot_path` in the response, don't assume failure.
- **Page behind login** → browser navigates to the page but won't see authenticated content unless cookies are pre-configured. Use `setup-browser-cookies` skill or capture public pages only.
- **Large screenshots** → a full profile page can be ~500KB PNG. Ensure your pipeline's asset size limit is respected (e.g., AVG's `upload_asset` caps at 50MB).
- **File extension matters** — the pipeline detects `type: 'video'` vs `type: 'image'` by extension. Screenshots should be `.png` or `.jpg`.
- **Headless JS rendering** — SPA pages (React, Vue) render fully. Very heavy pages may need a `browser_wait` or extra scroll to lazy-load content.

## Reference

See `references/avg-integration-guide.md` for the complete Automated-Video-Generator–specific integration guide walking through a real screenshot→asset→reel workflow (legacy pipeline).
See `references/avg-agentic-system-analysis.md` for deep **legacy vs agentic system comparison** — how local assets flow through the 6-stage agentic pipeline, visual tag handling, code gaps, and improvement recommendations for advanced workflows.
