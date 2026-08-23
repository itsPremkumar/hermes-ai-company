# Voice / TTS Model Audit (verified 2026-07)

All licenses, sizes, and maintenance dates pulled live from GitHub API + HuggingFace
during a session evaluating voice-cloning engines for a zero-cost MIT video generator
on a 6 GB RAM laptop. Treat sizes as approximate (weights evolve); licenses are stable.

## Comparison table

| Model | License | Weights | Clones? | Langs | Maintained? | RAM-fit (6 GB) | Notes |
|---|---|---|---|---|---|---|---|
| **Kokoro** | Apache-2.0 | 312 MB | No (presets) | 8 | Yes | Comfortable | Default narrator; tiny/fast |
| **F5-TTS** | MIT | 1.3 GB | Yes (10s ref) | EN (+forks) | Yes | On-demand | Lightest clean clone engine |
| **Qwen3-TTS** (0.6B) | Apache-2.0 | 1.7 GB | Yes + delivery | 10 | Yes | On-demand | Multilingual clone |
| **Chatterbox** | MIT | ~1.8 GB | Yes (few-sec) | 23 | Yes | On-demand + **HF gated (login)** | Strong clone; download needs auth |
| **GPT-SoVITS** | MIT | ~2–3 GB | Yes (1–2s few-shot) | 50+ | Yes | Heavy | Few-shot extreme; RAM-hungry |
| **Voicebox** (jamiepine) | MIT | bundles 7 | Yes (few-sec) | 23 | Yes (this week) | Run light engine | REST+MCP headless server; Hume TADA backend is local (no cloud key) |
| **OpenVoice** | MIT | ~1 GB | Yes | EN/JP/KR/ZH | **Stale Apr 2025** | Edge but dead | Avoid as dependency |
| **RVC** | MIT | ~1 GB | No (conversion) | many | Yes | Wrong job | Voice conversion, not TTS |
| **VibeVoice-ASR** | MIT | 15.9 GB | n/a (transcribe) | 50+ | Yes | Impossible here | 15.9 GB won't run on 6 GB |
| **VibeVoice-Realtime-0.5B** | MIT | 1.9 GB | No (fixed) | EN+9 | Yes | Edge, no clone | Fixed voices only |
| **Coqui XTTS** | MPL-2.0 | ~1.5 GB | Yes | 16 | **Archived ~2y** | Edge | Reject: MPL + dead |
| **Fish Speech** | Non-commercial | ~1 GB | Yes | many | Yes | Edge | Reject: commercial use forbidden |
| **OmniVoice Studio** | AGPL | — | Yes | — | Yes | Edge | Reject: AGPL copyleft |
| ElevenLabs / Azure | Proprietary/paid | cloud | Yes | many | — | n/a | Reject: paid cloud |

## Best-fit conclusions
- **Default narrator:** Kokoro (312 MB) — always-on, fits RAM.
- **Clone engine (primary):** Voicebox headless server (Kokoro default + Chatterbox Turbo / Qwen3-TTS on-demand). All MIT/Apache, local, MCP+REST.
- **Clone engine (standalone):** F5-TTS (MIT, 1.3 GB) — lighter than Chatterbox, clean license.
- **Multilingual clone backup:** Qwen3-TTS (Apache).
- **Few-shot extreme:** GPT-SoVITS (MIT) — only with RAM headroom.
- **Transcription helper (not on 6 GB):** VibeVoice-ASR (15.9 GB) or Whisper.cpp.

## Why these passed/failed the MIT-project filter
- Clean: Kokoro, F5-TTS, Qwen3-TTS, Chatterbox, GPT-SoVITS, Voicebox, OpenVoice, RVC, VibeVoice (MIT/Apache).
- Rejected: Fish Speech (non-commercial), OmniVoice (AGPL), Coqui XTTS (MPL + archived), ElevenLabs/Azure (paid cloud).
- Cloning: real zero/few-shot = F5-TTS, Qwen3-TTS, Chatterbox, GPT-SoVITS, Voicebox, OpenVoice. NOT cloning = Kokoro, VibeVoice (code removed / fixed), RVC (conversion), VibeVoice-ASR (transcription).

## VibeVoice-specific note
The official `microsoft/VibeVoice` had its TTS/cloning code **removed** by Microsoft
(responsible-AI policy, Sept 2025). Only ASR + fixed-voice realtime remain. A community
fork `vibevoice-community/VibeVoice` restores the TTS code (MIT, 1.1k stars) but uses
voice-prefill from reference wav; the demo only wires bundled presets; the 1.5B model
is impractical on 6 GB RAM. Not recommended for this user's laptop.
