# Sproutern Reel — known-good job + run recipe

Captured and run 2026-07-26 via the AVS agentic pipeline. Use as boilerplate for any
"website promo reel" — copy, swap the `[Visual: …]` filenames + script text.

## Assets captured (Hermes browser tools → input/visuals/)
Full-page screenshots, then cropped to 9:16 top section via `scripts/crop_9x16.sh`:
- `sproutern-hero.png`       — homepage hero "Build Your Career Advantage"
- `sproutern-tools.png`      — the 90+ free tools grid
- `sproutern-interviews.png` — real interview experiences (Amazon/Google/Microsoft/Barclays…)
- `sproutern-about.png`      — mission / "Open Source / Free Forever"
- `avs-github.png`           — the AVS GitHub repo (MIT, 23★)

Capture: `browser_navigate(url)` → `browser_vision("clean full-page screenshot")` →
copy `C:\Users\PREM KUMAR\AppData\Local\hermes\cache\screenshots\browser_screenshot_*.png`
into `input/visuals/`.

## Job file (input/scripts/sproutern-reel-job.json)
```json
[
  {
    "id": "sproutern_reel",
    "title": "Sproutern — Free Career Platform for Students",
    "script": "90+ free tools. Real interview experiences. Study-abroad guides. All in one place — Sproutern. [Visual: sproutern-hero.png] [Grade: vivid] [Transition: fade]\nTired of career platforms that lock help behind a paywall? Sproutern gives students everything for free — forever. [Visual: sproutern-tools.png] [Grade: cool] [Transition: slide]\nReal interview experiences from Amazon, Google, Microsoft, Barclays and more — written by students who actually got in. [Visual: sproutern-interviews.png] [Grade: cinematic] [Transition: zoomblur]\nCGPA converters, salary calculators, resume checkers, aptitude tests — 90+ tools already used by 2 lakh-plus students. [Visual: sproutern-tools.png] [Grade: warm] [Transition: fade]\nBuilt by a student, for students. Open source, MIT licensed, and free for the whole world. [Visual: sproutern-about.png] [Grade: cinematic] [Transition: slide]\nStart your career advantage today. Search Sproutern and explore it free. [Visual: avs-github.png] [Grade: vivid] [Transition: fade]",
    "orientation": "portrait",
    "aspect": "9:16",
    "voice": "en-US-GuyNeural",
    "kokoroVoice": "af_heart",
    "hookFirst": true,
    "variablePacing": true,
    "backend": "agent",
    "candidatesPerAsset": 1,
    "language": "english",
    "captions": "burned",
    "captionTheme": "neon",
    "kineticText": true,
    "vignette": true,
    "jCutSec": 0.4,
    "musicIntensity": "mid",
    "musicQuery": "upbeat corporate technology",
    "preset": "reels",
    "videoType": "product",
    "platform": "reels",
    "kenBurns": true,
    "defaultVisual": "sproutern-hero.png",
    "lowerThird": "Sproutern — Free for students",
    "titleCard": { "title": "Sproutern", "subtitle": "Free Career Tools for Students" },
    "endCta": "Explore free today",
    "intro": { "title": "Sproutern", "subtitle": "Free Career Platform", "durationSec": 2 },
    "outro": { "ctaText": "Search Sproutern", "durationSec": 2 }
  }
]
```

## Run
```bash
cd C:\one\Automated-Video-Generator
npm run agentic:modular -- pipeline --file input/scripts/sproutern-reel-job.json
```
Stages: plan → visuals (Pexels fallback download, ~1–2 min for stock .mp4s) →
voice (Kokoro af_heart, cold auto-start ~seconds) → render → `output/sproutern_reel/`.

## Verify (empirical — required by this user)
- `ffprobe output/sproutern_reel/<title>.mp4` → audio bitrate >160 kbps, sane duration.
- Extract frames: `ffmpeg -ss 2 -i final.mp4 -frames:v 1 s1.jpg` (note `-ss AFTER -i`).
- `vision_analyze` each frame: confirm 9:16, captions legible in English, Sproutern
  screenshots actually shown (not stock leak), watermark/intro/outro present.
- Edit a scene if needed: `npm run agentic:modular -- edit --scene N --grade cinematic`
