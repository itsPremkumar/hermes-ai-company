# Voicebox Env Vars — Quick Reference

All env vars for Voicebox integration into a video-generation pipeline.

## Required (for Voicebox to work)

```env
TTS_PROVIDER=voicebox
VOICEBOX_API_URL=http://127.0.0.1:17493
VOICEBOX_ENGINE=chatterbox_turbo
VOICEBOX_PROFILE_ID=<your-cloned-profile-uuid>
```

## Auto-Start (pipeline spawns Voicebox on demand)

```env
VOICEBOX_BACKEND_DIR=C:/one/voicebox
VOICEBOX_PYTHON=C:/one/voicebox/.venv/Scripts/python.exe
```

## Engine Options

| Engine | VRAM Use | Quality | Clone Support |
|--------|----------|---------|---------------|
| `kokoro` | ~0.8 GB | Good | No (presets only) |
| `chatterbox` | ~3.2 GB | High | Yes (multilingual) |
| `chatterbox_turbo` | ~3.8 GB | Very High | Yes (fast) |
| `qwen-3-tts` | ~3.6 GB | Excellent | Yes |

## Secrets Checklist

- [ ] `VOICEBOX_PROFILE_ID` — local credential, DO NOT commit real value
- [ ] `PEXELS_API_KEY` — real API key, never commit
- [ ] `GEMINI_API_KEY` — real API key, never commit
- [ ] `OPENROUTER_API_KEY` — real API key, never commit

Safe to commit (in .env.example): paths, engine names, port numbers,
placeholder values.
