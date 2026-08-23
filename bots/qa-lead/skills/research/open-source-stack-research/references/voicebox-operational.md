# Voicebox (jamiepine) — Operational Reference & Community-Fork Notes

Verified live 2026-07 from repo source (`jamiepine/voicebox`, MIT, 42k★, pushed this week).
Complements the license/size bank in `verified-stacks.md`. Use this when a user wants to
actually RUN a local voice-clone stack on a low-spec laptop, not just pick a model.

## 1. What Voicebox is (verified)
- MIT-licensed local-first "AI voice studio" — free ElevenLabs alternative.
- Bundles **7 TTS engines** behind ONE headless FastAPI backend + built-in MCP server + REST API:
  Qwen3-TTS, Qwen CustomVoice, LuxTTS, Chatterbox Multilingual, Chatterbox Turbo,
  HumeAI TADA, Kokoro.
- **All engines run LOCAL.** Verified `backend/backends/hume_backend.py` imports `torch` + a
  local DAC shim and makes NO cloud HTTP call / needs NO API key. The "HumeAI TADA" engine is
  on-device despite the brand name.
- **Models are NOT bundled.** They download on-demand from HuggingFace on first use, then cache.
  Proof: `backend/utils/hf_offline_patch.py` exists solely to force offline mode when weights are
  already cached. A fresh install is small (venv deps only); each engine's weights pull at load time.

## 2. Control surface for "use only when needed" (key for 6 GB laptops)
Run **headless** (skip the Tauri GUI to save RAM):
```bash
cd voicebox/backend
pip install -r requirements.txt
python -m backend.main --host 127.0.0.1 --port 17493
```
REST endpoints (verified in `backend/routes/*.py`):
- `POST /generate`  — `{"text","profile_id","language"}`
- `POST /speak`     — speak in a cloned/voice profile (MCP-equivalent)
- `POST /transcribe`— Whisper STT on an audio file
- `GET  /profiles`  — list voice profiles
- `POST /models/load`              — load ONE engine (`{"model_size":"chatterbox-turbo"}`); downloads first time
- `POST /models/unload`            — unload default TTS model (free RAM)
- `POST /models/{name}/unload`     — unload a SPECIFIC engine without deleting from disk

**Efficiency pattern (user-confirmed goal):** wake backend → `POST /models/load` the ONE engine
needed (Kokoro for narration; Chatterbox Turbo / Qwen3-TTS 0.6B for cloning) → generate →
`POST /models/{name}/unload` → kill backend process when the video job is done. Nothing stays
resident. Never load two clone engines (Chatterbox-Multilingual + Qwen-1.7B + TADA-3B) together =
OOM on 6 GB.

## 3. Engine tiering inside Voicebox (cloning vs preset)
- **Clone your voice (reference sample):** Qwen3-TTS, Chatterbox Multilingual (23 langs),
  Chatterbox Turbo (350M, `[laugh]`/`[sigh]` tags), TADA (1B/3B).
- **Preset only (NO cloning):** Kokoro (50 built-in voices, 312 MB, always-on narrator),
  LuxTTS (English, ~1 GB VRAM, 150x realtime CPU), Qwen CustomVoice (designed voices, no ref audio).
- RAM-feasible on 6 GB: Kokoro + Chatterbox Turbo, or Qwen3-TTS 0.6B. Avoid TADA-3B / stacking.

## 4. vibevoice-community/VibeVoice — the fork that restored the deleted code
- `microsoft/VibeVoice` had its TTS/cloning code **removed** by Microsoft (Sept 2025, "responsible
  AI" after misuse). Only ASR + fixed-voice Realtime remain → NOT usable for cloning.
- **`vibevoice-community/VibeVoice`** (MIT, 1.1k★, 428 forks, created Sep 2025) **re-published the
  TTS code** Microsoft deleted. Contains `demo/inference_from_file.py` + `modeling_vibevoice_inference.py`.
- Cloning = **voice prefill** from a reference `.wav`. Demo's `VoiceMapper` only wires Microsoft's
  bundled preset wavs; to clone YOUR voice you drop your own reference wav + adapt the script
  (small change — the model supports reference audio input).
- **BUT VibeVoice-1.5B (Qwen2.5 backbone) is 1.5B+ params** → needs several GB RAM, slow on CPU.
  Impractical on a 6 GB laptop. Only worth it on 16 GB+ / GPU for 90-min multi-speaker podcasts.
- The official `microsoft/VibeVoice` ASR weights are ~15.9 GB → never fits 6 GB.

## 5. Why Microsoft removed VibeVoice-TTS but NOT Voicebox (ownership insight)
- VibeVoice = Microsoft-authored models; Microsoft owns the repo and exercised corporate
  "responsible AI" risk control to delete the cloning code they owned.
- Voicebox = independent MIT project by one dev; it only *aggregates* third-party MIT/Apache engines
  (Chatterbox, Qwen, Kokoro…) hosted elsewhere. No corporate owner, no single asset to delete, and
  MIT means it's already forked everywhere. Hence never at risk of the same removal.
- Lesson: a self-authored model repo can be pulled by its corporate owner; a permissive aggregator
  of third-party models is structurally resilient. Prefer aggregators for longevity.

## 6. General-audience verdict (Voicebox vs VibeVoice-community)
- **Voicebox = best overall** for the average user: GUI + headless REST/MCP, 7 switchable engines,
  42k★ vs 1.1k★, updated weekly, runs on consumer laptops, agent-ready.
- **VibeVoice-community = best ONLY** for long-form (≤90 min) multi-speaker (≤4) conversational
  synthesis on capable hardware. Overkill + infeasible on 6 GB.

## 7. Disk hygiene
- Models cache after first download (~312 MB Kokoro, ~1.7 GB Qwen, ~1.8 GB Chatterbox). Plan +5–8 GB
  free on `C:\`. Unused engines (LuxTTS, TADA, Chatterbox-Multilingual) stay undownloaded until loaded.
- Safe to DELETE a cloned unused repo (e.g. `C:\one\VibeVoice`) to reclaim space — confirmed it does
  not affect the real project (`Automated-Video-Generator`) or the HF cache holding Qwen3-TTS.
