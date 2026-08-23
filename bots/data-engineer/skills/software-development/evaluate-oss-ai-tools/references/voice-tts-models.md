# Verified Voice / TTS Model Comparison (built 2026-07-18)

All license/size numbers pulled live from GitHub + HuggingFace. Context: user's
Automated-Video-Generator (TS/Node, MIT) needs realistic human voice cloning,
free, self-hosted, license-clean, agentic-ready, on a 6 GB RAM laptop.

## License verdict (hard rule: MIT / Apache only)
- Clean: Kokoro (Apache-2.0, 312 MB), F5-TTS (MIT, 1.3 GB), Qwen3-TTS
  (Apache-2.0, 0.6B=1.7 GB / 1.7B), Chatterbox (MIT, ~1.8 GB, HF-gated),
  GPT-SoVITS (MIT, ~2-3 GB), Voicebox/jamiepine (MIT, bundles 7 engines),
  OpenVoice (MIT, ~1 GB, stale Apr 2025), RVC (MIT, ~1 GB, conversion-only),
  VibeVoice family (MIT).
- Reject: Fish Speech (non-commercial license), OmniVoice (AGPL),
  Coqui XTTS (MPL-2.0 + archived ~2y), ElevenLabs/Azure (paid cloud).

## Clone-capability
- Real zero/few-shot cloning: F5-TTS, Qwen3-TTS, Chatterbox, GPT-SoVITS,
  Voicebox, OpenVoice.
- NOT cloning: Kokoro (fixed voices), VibeVoice (TTS code REMOVED by Microsoft;
  realtime model = fixed preset voices only), RVC (voice conversion, not TTS),
  VibeVoice-ASR (transcription only, 15.9 GB -- won't run on 6 GB).

## RAM fit (6 GB box: ~5.86 GB total, ~400 MB free)
- Comfortable: Kokoro (312 MB).
- On-demand only (load + unload): F5-TTS (1.3 GB), Qwen3-TTS 0.6B (1.7 GB),
  Chatterbox (~1.8 GB).
- Impossible here: VibeVoice-ASR (15.9 GB), GPT-SoVITS full toolkit.

## VibeVoice note (verified)
- Official microsoft/VibeVoice: MIT, but TTS code removed Sept 2025 (responsible-AI
  misuse). Only ASR + realtime (fixed voices) remain. NOT a clone engine.
- Community fork vibevoice-community/VibeVoice: MIT, 1.1k stars, restored TTS
  code (1.5B), voice-prefill cloning. But 1.5B+LLM backbone = needs 16 GB+/GPU.
  Impractical on 6 GB. Better only for 90-min multi-speaker on capable HW.

## Voicebox (jamiepine) -- the recommended voice microservice
- MIT, 42k stars, actively maintained. Local-first studio bundling 7 engines
  (Qwen3-TTS, Qwen CustomVoice, LuxTTS, Chatterbox Multilingual/Turbo, HumeAI
  TADA, Kokoro) behind ONE headless FastAPI server + built-in MCP server + REST.
- Verified local-only: hume_backend.py imports torch + local DAC shim, NO cloud
  call. Models download on-demand from HF (not bundled).
- Headless: `python -m backend.main --host 127.0.0.1 --port 17493`.
- Load/unload per engine: POST /models/load, POST /models/{name}/unload.
- Clean agentic integration: orchestrator calls POST /speak with cloned profile;
  load clone engine on-demand, unload after to free RAM.

## Final recommended stack
- Default narrator: Kokoro (Apache, 312 MB).
- Clone engine (primary): Voicebox headless (uses bundled Chatterbox/Qwen).
- Clone engine (standalone): F5-TTS (MIT, 1.3 GB).
- Multilingual backup: Qwen3-TTS (Apache).
- Few-shot extreme: GPT-SoVITS (MIT) only with RAM headroom.
- Cloud fallback: Edge-TTS (current default) when no local server up.
