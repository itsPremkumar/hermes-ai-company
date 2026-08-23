# Voicebox (jamiepine/voicebox) — verified integration contract

MIT-licensed local multi-engine voice studio. This is the user's chosen
voice-clone backend, integrated into Automated-Video-Generator via
`src/lib/api-tts-provider.ts` + `src/lib/voicebox-lifecycle.ts`.

## Critical API facts (verified against repo source, not README)

- **Profile-based, ALWAYS.** Every generation (even plain Kokoro narration)
  requires a voice `profile`. There is no "default voice, no profile" path.
  Set `VOICEBOX_PROFILE_ID` or the provider throws (falls back to Edge-TTS).

- **`POST /models/load` is QWEN-ONLY.** Its signature is
  `load_model(model_size: str = "1.7B")` -> internally does
  `from qwen_tts import Qwen3TTSModel` with `qwen-tts-{size}`. Sending
  `{"model_size":"kokoro"}` is IGNORED (JSON body isn't read; default "1.7B"
  loads Qwen 1.7B -> OOM on small boxes). Kokoro / Chatterbox / clone engines
  load LAZILY on first `/speak` via `get_tts_backend_for_engine(engine)`.

- **Correct generation flow (what the provider must do):**
  1. `POST /speak`  body `{ text, profile, engine, language }`
     -> `{ id, status:"generating" }`
  2. Poll `GET /generate/{id}/status` (SSE stream, lines `data: {json}`)
     until `status == "completed"` (or `error`). Cold Kokoro load on GPU
     ~60-90s; Chatterbox-Turbo first run also downloads ~4 GB once.
  3. `GET /audio/{id}` -> WAV (24 kHz mono PCM). NOT `/generate/{id}/audio`
     (that returns `{"detail":"Not Found"}`).

- **Profile types:**
  - `preset` (no reference audio): `{"voice_type":"preset","preset_engine":"kokoro","preset_voice_id":"af_heart","default_engine":"kokoro"}`.
    Kokoro presets: af_heart, af_bella, am_adam, etc. (GET `/profiles/presets/kokoro`).
  - `cloned` (voice cloning): `{"voice_type":"cloned","default_engine":"chatterbox_turbo"}`,
    then `POST /profiles/{id}/samples` with `file` (audio) + `reference_text`
    (verbatim transcript, 2-30s clip). Engine clones from the sample.

## Engine sizing on the user's RTX 3050 (4 GB VRAM, 4096 MiB)

| Engine | Size | VRAM used | Fits 4 GB? | Notes |
|---|---|---|---|---|
| Kokoro-82M (`hexgrad/Kokoro-82M`) | ~350 MB | ~800 MB | OK comfortable | Recommended narrator. No clone. |
| Chatterbox-Turbo (`ResembleAI/chatterbox-turbo`, MIT) | ~4.0 GB dl | ~3.8 GB | tight, fits | Clones voice. Leaves little headroom — don't run GPU render simultaneously. |
| Chatterbox (multilingual) | ~3.2 GB | ~3.2 GB | tight | Clones, more languages. |
| Qwen 1.7B (`Qwen/Qwen3-TTS-12Hz-1.7B`) | ~3.6 GB | >4 GB | OOM on 4 GB | Needs bigger VRAM. |

**Rule:** on this box, Kokoro for narration, Chatterbox-Turbo for cloning.
Qwen needs >4 GB VRAM.

## PYTHONPATH isolation (MUST do on this box — see windows-box-maintenance)
The global `PYTHONPATH` leaks Hermes venv site-packages into every python,
so `huggingface_hub` resolves to Hermes's 1.2.3 and model loads fail. Launch
backend AND run uv installs with `env PYTHONPATH=` (empty) so the venv is
isolated. CUDA torch must be reinstalled after `chatterbox-tts` downgrades it
(see windows-box-maintenance CUDA note + this skill's VRAM pattern).

## Verified working command (RTX 3050)
```
env PYTHONPATH= .venv/Scripts/python.exe -m backend.main \
  --host 127.0.0.1 --port 17493 --data-dir C:/one/voicebox/.voicebox-data
# log prints:  GPU: CUDA (NVIDIA GeForce RTX 3050 Laptop GPU); Ready
```
Clone proof: created cloned profile -> uploaded ref clip -> generated 4.96s
clip via Chatterbox-Turbo on cuda (~3.8 GB VRAM), valid 24 kHz WAV.

## One-command clone + all-scenarios test (built this session)
- **Clone your voice:** `node scripts/setup-voicebox-clone.mjs C:/path/to/your-voice.wav "verbatim transcript"`
  creates the `cloned` profile, uploads the reference sample, writes
  `VOICEBOX_PROFILE_ID` into `.env`. Re-run whenever you want to re-clone.
- **Test every voice path:** `node scripts/test-voicebox-voices.mjs` exercises
  Kokoro presets (af_heart / am_adam / af_bella) + the Chatterbox-Turbo clone,
  writes one WAV per scenario to `voicebox-test-output/`. Verified 4/4 on this box.
  Run it after any backend/env change to confirm every voice still produces audio.

## LEGAL: never clone a famous/real person's voice
A user asked to clone a celebrity voice for video narration. Refused — it's a
legal/ethical line (right-of-publicity, platform TOS, MIT tool licenses don't
permit impersonating real individuals), not a technical limit. Offer instead:
(A) Kokoro **fictional preset** narrators (zero setup, license-clean),
(B) clone the **user's own** voice via the script above, or
(C) a voice they have explicit written permission to use.
See SKILL.md "HARD POLICY" for the exact phrasing to use.
