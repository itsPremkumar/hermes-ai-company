# Free Music API Provider Research

Verified status of free music APIs for agentic video pipelines (as of July 2026).

## ✅ Working Providers (Verified End-to-End)

| Provider | Auth | Quality | Speed | Notes |
|----------|------|---------|-------|-------|
| **ccMixter.org** | None | Good | ~5-15s | Free CC-licensed music. Search + download working. Requires Referer header. [Documented in SKILL.md] |
| **Internet Archive** | None | OK | ~3-10s | Public domain audio. Two-step resolution needed. [See internet-archive-audio.md] |
| **Bundled MP3s** | None | Good | Instant | Locally shipped files in `input/bgm/__bundled__/`. Always available. |
| **ffmpeg Procedural** | None | OK | 1-2s/first, instant/cached | 3 profiles: ambient, upbeat, cinematic. Always works. |

## 🚫 Broken / Non-Working Providers

| Provider | Reason | Status |
|----------|--------|--------|
| **Pixabay Audio API** | `/api/audio/` returns 403. Pixabay API only covers images and videos — no audio endpoint despite nav links. | **Permanently unavailable** |
| **OpenLofi (btahir/open-lofi)** | All 166 catalog entries return 404. GitHub repo removed all audio files — only catalog.json remains. | **Permanently broken** |
| **Pixabay npm library (dderevjanik/pixabay-api)** | Only wraps `searchImages` and `searchVideos` — no audio search. | **Not for audio** |

## How to Find New Free Music APIs

Methodology:
1. Search GitHub for "free music api", "music api no key", "cc0 music api"
2. Test search endpoint with `curl -s` — check response format and speed
3. Test download URL with `curl -sI` — check for proper content-type and no auth
4. Check license — must be CC0, CC-BY, or public domain for commercial use
5. Check rate limits and terms of service
