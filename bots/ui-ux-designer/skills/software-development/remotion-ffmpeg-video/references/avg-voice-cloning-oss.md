# Open-source voice-cloning / TTS — license-verified matrix (AVG feature)

Verified live (GitHub LICENSE files + repo status) on 2026-07-18 for the
Automated-Video-Generator agentic pipeline. Filter: FREE + open-source + license-clean
(MIT / Apache / BSD — NO AGPL, NO non-commercial) + self-hostable + offline.

## RECOMMENDED (use these)
| Tool | License (verified) | Role | Notes |
|---|---|---|---|
| **F5-TTS** (SWivid) | **MIT** (switched from MPL!) | Zero-shot clone | Primary clone engine. Lightweight, maintained, ~10s reference. |
| **Chatterbox** (Resemble) | MIT | Zero-shot clone | Secondary. Heavier (GPU/CPU, several-GB); `[laugh]`/`[sigh]` tags. |
| **Qwen3-TTS** (Alibaba) | Apache-2.0 | Multilingual clone | Backup; many languages + voice-design directions. |
| **Kokoro** | Apache-2.0 | Default narrator | Built-in voices only (no clone). Tiny/fast/low-RAM — use as default. |
| **GPT-SoVITS** | MIT | Few-shot clone | Strong alt with very little reference audio. |
| **VibeVoice-ASR** (MS) | MIT | Transcription/align | NOT for cloning — use as offline word-timing source (long-form 60-min, 50+ langs). |

## ACCEPTABLE / NICHE
| **OpenVoice** (MyShell) | MIT (core; "MIT and MyShell") | Instant clone | Self-hosted code MIT; hosted API has MyShell restrictions. |
| **RVC** (Retrieval-VC) | MIT | Voice *conversion* | Transforms existing audio to target voice — not TTS-from-script. |
| **VALL-E-X** (Plachtaa) | MIT | Zero-shot clone | ARCHIVED/read-only since Nov 2025 — dead, skip. |

## REJECTED (do NOT use)
| Coqui XTTS (coqui-ai/TTS) | MPL-2.0 + repo **archived 2y** | Clone | File-level copyleft + unmaintained. |
| Fish Speech | **Non-commercial** | Clone | License violates zero-cost MIT project rule. |
| OmniVoice | AGPL | Clone | Copyleft. |
| Microsoft/VibeVoice-TTS | Code removed | — | Unusable. |
| Azure / ElevenLabs | Paid cloud | — | Violates "completely free" rule. |

## Recommended AVG wiring
- Default narrator: **Kokoro** (always works, low-RAM).
- Clone engine (primary): **F5-TTS**; backup **Chatterbox** + **Qwen3-TTS** (multilingual).
- Few-shot alt: **GPT-SoVITS**.
- Offline word-timing (#3): **VibeVoice-ASR** or whisper.cpp.
- Cloud fallback: **Edge-TTS** (current) when no local TTS server reachable.
- All wrapped in a null-safe local-TTS provider abstraction (graceful fallback to
  Edge-TTS), same pattern as the existing `voice-generator` null-safe design.

## Verification method (reuse for any OSS license audit)
Fetch the RAW LICENSE file on GitHub (`raw.githubusercontent.com/<owner>/<repo>/<branch>/LICENSE`)
and the repo's last-commit date — do NOT trust README claims or star-count summaries
from AI comparisons (they hallucinate). Confirm: (1) SPDX identifier, (2) repo not
archived, (3) no "non-commercial"/"personal use only" clause.
