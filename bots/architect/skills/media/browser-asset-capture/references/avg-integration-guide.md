# AVG + Hermes Integration: Browser Screenshot → Reel Video

> Written for the `itsPremkumar/Automated-Video-Generator` project.
> Applies to any pipeline that supports `[Visual: filename.ext]` local-asset tags.

## Real Walkthrough: GitHub Profile → Promo Reel

### What We Built

A portrait (9:16) reel promoting the Automated-Video-Generator open-source project, using two visual assets:

1. **Project logo** → from `assets/logos/logo-automation.png`
2. **GitHub profile screenshot** → captured live from `https://github.com/itsPremkumar`

### Step 1: Discover Existing Assets

```bash
find . -iname "*logo*" -maxdepth 3
# → assets/logos/logo-automation.png
# → public/logo.png
```

Pick the highest-resolution version. Copy to `input/visuals/`:

```bash
cp assets/logos/logo-automation.png input/visuals/logo-automation.png
```

### Step 2: Capture the GitHub Page

```typescript
// Agent tool calls:
browser_navigate(url="https://github.com/itsPremkumar")
browser_vision(question="Screenshot of full GitHub profile page")
// → screenshot_path: "C:/Users/.../cache/screenshots/browser_screenshot_....png"
// → vision analysis may 400, but the PNG is still saved
```

Copy to assets:

```bash
cp /path/to/screenshot.png input/visuals/github-profile.png
```

### Step 3: Verify Assets

```bash
ls -la input/visuals/
# -rw-r--r--  github-profile.png  (486 KB)
# -rw-r--r--  logo-automation.png  (708 KB)
```

### Step 4: Write the Script

```json
[
  {
    "id": "avg-promo-reel",
    "title": "Automated Video Generator — Open Source Reel",
    "orientation": "portrait",
    "script": "[Visual: logo-automation.png]\nIntroducing Automated Video Generator — the free, open-source, zero-cost text-to-video pipeline.\n\nPowered by Remotion, 400+ AI voices, and multiple stock media APIs — all behind a single script.\n\n[Visual: github-profile.png]\nBuilt by Premkumar M — open-source contributor, OSCG 2026 Mentor, and creator of production-grade AI tooling.\n\n20+ GitHub stars, MIT licensed, and fully agentic via MCP.\n\n[Visual: logo-automation.png]\nFork it, use it, contribute. Automated Video Generator — open source video, for everyone.",
    "showText": true,
    "voice": "en-US-JennyNeural"
  }
]
```

### Step 5: Generate

Via MCP: `generate_video(script, title, orientation="portrait")`
Via CLI: `npm run generate`

### Scene Structure Template

| Scene | Visual Tag | Duration | Narration Role |
|-------|-----------|----------|---------------|
| 1 | `[Visual: logo-automation.png]` | 5s | **Hook** — name the project, what it is |
| 2 | *(stock — code/dashboard)* | 6s | **Features** — what it does (Remotion, TTS, APIs) |
| 3 | `[Visual: github-profile.png]` | 6s | **Credibility** — creator, stars, license |
| 4 | `[Visual: logo-automation.png]` | 4s | **CTA** — fork, contribute, MIT |

## Key Code References

Asset resolution path (`src/video-generator.ts`):

```
line 199: if (scene.localAsset) {
line 200:     sourcePath = path.join(inputAssetPath(), scene.localAsset)
line 202:     ext = path.extname(scene.localAsset)
line 203:     isVideo = ['.mp4','.mov','.webm','.m4v'].includes(ext)
line 206:     if (fs.existsSync(sourcePath)) { copyFileSync → visual = { type, url, width, ... } }
line 227:     if (!visual) { fetchVisualsForScene(...) }   // ← stock fallback
```

## Script Format Reference

From `input/INPUT_FORMAT.md`:

```
[Visual: filename.ext]     → Check input/input-assets/ first. If exists, use locally.
[Visual: search keywords]  → If file not found, search stock media (Pexels → Pixabay → Free).
No tag at all             → Auto-extract keywords from narration text.
```

## MCP Tools Available

| Tool | Purpose |
|------|---------|
| `upload_asset` | Upload base64 file to `input/visuals/` (50MB cap) |
| `delete_asset` | Remove a file from assets |
| `write_input_script` | Save/update a job definition |
| `generate_video` | Start background video generation |
| `get_video_status` | Poll job progress |

## Desktop Capture via computer_use

In addition to browser screenshots, you can capture ANY running application window:

```bash
# Capture VS Code showing the project
computer_use capture(app='Code', mode='vision')
cp <path> input/visuals/vscode-demo.png

# Capture File Explorer showing project structure
computer_use capture(app='explorer', mode='vision')
cp <path> input/visuals/explorer-structure.png

# Capture the full desktop
computer_use capture(app='screen', mode='vision')
cp <path> input/visuals/desktop-overview.png
```

These go to `input/visuals/` and are referenced as `[Visual: vscode-demo.png]` — same as any other local asset.

## Agentic Pipeline Flow

The agentic pipeline (`npm run generate:agentic`) uses `input/scripts/agentic-scripts.json`:

```json
[
  {
    "id": "avg-promo-reel-agentic",
    "title": "Automated Video Generator — Agentic Reel",
    "script": "[Visual: logo-automation.png]\nIntroducing Automated Video Generator.\n[Visual: github-profile.png]\nBuilt by Premkumar M.\n[Visual: vscode-demo.png]\nFull TypeScript codebase.\n[Visual: rocket-launch]\nGet started today.",
    "orientation": "portrait",
    "backend": "agent",
    "hookFirst": true,
    "variablePacing": true
  }
]
```

Run: `npm run generate:agentic`

This produces a video with:
- **6 quality gates** (X1-X16 checks)
- **Voicebox/Kokoro realistic audio** (when `TTS_PROVIDER=voicebox` in `.env`)
- **25+ plugins** (transitions, overlays, captions)
- **Multi-aspect exports** (16:9, 1:1, 9:16)
- **Auto-subtitles** (SRT + VTT)
- **Publish manifest** + YouTube upload script

## Related Docs

- `docs/CUA_ASSET_COLLECTION.md` — Full CUA capture guide with all 3 capture methods
- `docs/INPUT_ASSETS_GUIDE.md` — Local asset basics
- `docs/VOICEBOX_SETUP.md` — Realistic TTS audio setup
