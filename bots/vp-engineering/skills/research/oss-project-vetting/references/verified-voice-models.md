# Verified Voice / TTS / Voice-Clone Models

License + size + capability facts below were pulled LIVE from GitHub/HuggingFace
and source code during a vetting session (mid-2026). Re-verify before shipping —
model weights and licenses change. All sizes are download/on-disk model weights
unless noted; "RAM fit" assumes the user's dev box: ~5.86 GB total RAM, often
<400 MB free, 280+ procs, no GPU.

## License-clean for an MIT project (RECOMMENDED SET)
| Model | License | Weights | Clones? | Langs | Maintained | RAM fit (6 GB) | Interface |
|---|---|---|---|---|---|---|---|
| Kokoro (hexgrad/Kokoro-82M) | Apache-2.0 | 312 MB | No (presets) | 8 | Yes | ✅ Comfortable | Lib/ONNX/HTTP |
| F5-TTS (swivid/F5-TTS) | MIT | 1.3 GB | Yes (10s ref) | EN (+forks) | Yes | ⚠️ on-demand | Lib/CLI |
| Qwen3-TTS (Qwen/Qwen3-TTS-12Hz-0.6B-*) | Apache-2.0 | 1.7 GB | Yes + delivery ctrl | 10 | Yes | ⚠️ on-demand | HF/server |
| Chatterbox (resemble-ai/chatterbox) | MIT | ~1.8 GB | Yes (few-sec) | 23 | Yes | ⚠️ on-demand + HF GATED (login) | HTTP API/MCP |
| GPT-SoVITS (RVC-Boss/GPT-SoVITS) | MIT | ~2–3 GB toolkit | Yes (1–2s few-shot) | 50+ | Yes | ❌ heavy | GUI/API |
| Voicebox (jamiepine/voicebox) | MIT | bundles 7 | Yes (few-sec) | 23 | Yes | ⚠️ run light engine | **REST + MCP + headless** |
| OpenVoice (myshell-ai/OpenVoice) | MIT | ~1 GB | Yes | EN/JP/KR/ZH | ❌ STALE Apr 2025 | ⚠️ edge but dead | Lib |
| RVC (RVC-Project/Retrieval-based-Voice-Conversion-WebUI) | MIT | ~1 GB | ❌ conversion only | many | Yes | ⚠️ wrong job | GUI/API |
| VibeVoice-ASR (microsoft/VibeVoice-ASR-HF) | MIT | 15.9 GB | n/a (transcribe) | 50+ | Yes | ❌ impossible here | HF/server |
| VibeVoice-Realtime-0.5B (microsoft) | MIT | 1.9 GB | ❌ fixed voices | EN+9 | Yes | ⚠️ edge, no clone | HF |

## REJECTED (license or fitness violation)
| Model | Reason |
|---|---|
| Fish Speech (fishaudio/fish-speech) | **Non-commercial** ("Fish Audio Research License") — commercial use forbidden. GitHub shows `NOASSERTION` which HIDES this. |
| OmniVoice Studio (debpalash/OmniVoice-Studio) | **AGPL-3.0** — copyleft dominates MIT shipping. |
| Coqui XTTS (coqui-ai/TTS) | **MPL-2.0** AND **archived ~2y**. Double reject. |
| ElevenLabs / Azure / cloud TTS | Proprietary/paid, data leaves box. |
| VibeVoice-TTS (microsoft/VibeVoice) | **TTS code REMOVED by Microsoft** (Sep 2025, "responsible use"). Repo keeps ASR + fixed-voice realtime only. Zombie repo (50k★) — unusable for cloning. |
| VibeVoice-community fork | MIT, restored TTS code, BUT 1.5B model + LLM backbone = impractical on 6 GB laptop. Only for 16 GB+/GPU long-form multi-speaker. |

## Best-fit call (for this user's video project)
- Default narrator: **Kokoro** (312 MB, always-on).
- Clone engine (primary, in Voicebox): **Chatterbox Turbo** (350M, light) / **Qwen3-TTS 0.6B**.
- Standalone clone fallback: **F5-TTS** (MIT, 1.3 GB).
- Voicebox (jamiepine) as the voice microservice: Kokoro default + on-demand clone,
  REST + MCP, fully local. Verified: hume_backend.py imports torch + local shim,
  NO cloud HTTP → all 7 engines run on-device.

## Capability truth-checks
- "Clone any voice" claims: real zero/few-shot cloning = F5-TTS, Qwen3-TTS,
  Chatterbox, GPT-SoVITS, Voicebox, OpenVoice. NOT cloning = Kokoro (presets),
  VibeVoice (fixed), RVC (conversion of existing audio, not TTS), VibeVoice-ASR.
- Voicebox does NOT bundle weights — downloads per-engine from HF on first use
  (proven by `hf_offline_patch.py` forcing offline only when cached). Small initial
  footprint; +5–10 GB after using several engines.
