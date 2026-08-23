---
name: vet-open-source-ai
description: Vet open-source AI tools, libraries, and models before adopting them — verify license, model size, maintenance, and self-hostability via APIs instead of trusting README/marketing claims. Use whenever the user asks "is X suitable for my project?", "analyze this project", "what's the best open-source alternative for Y", or pastes a "best of" list to evaluate. Especially relevant for zero-cost MIT projects on low-spec hardware.
---

# Vet Open-Source AI Projects & Models

## When to use
- User asks "is <repo/tool> suitable?" or "analyze this."
- User pastes a list/article of "best open-source X" and wants a recommendation.
- Choosing a model/engine to add to a build (voice, vision, LLM, etc.).

## Core principle: verify, never trust claims
Marketing copy, README blurbs, and pasted "best of" lists routinely lie or omit:
- "open-source" but actually **AGPL / non-commercial / MPL** (license conflict for MIT projects)
- "self-hosted" but actually needs **cloud API keys**
- "free" but paid tier / commercial license required
- Code that was **removed** by the maintainer (e.g. Microsoft pulled VibeVoice-TTS)
- Project **archived/unmaintained** (e.g. Coqui XTTS)

Always verify against the source before recommending.

## Verification workflow (API, not claims)
1. **GitHub repo facts** — `curl -s https://api.github.com/repos/<owner>/<repo>` → parse `license.spdx_id`, `stargazers_count`, `pushed_at`, `description`, `topics`. Use `python` (not `python3` — python3 is missing on this Win box).
2. **HuggingFace model size** — `curl -s https://huggingface.co/api/models/<org>/<model>/tree/main?recursive=true` → sum `size` of `.safetensors`/`.bin`/`.pt` files. This decides RAM-fit.
3. **License file** — when GitHub reports `NOASSERTION`, fetch `LICENSE` raw and read it; "NOASSERTION" usually hides a non-commercial or custom clause (e.g. Fish Speech = Fish Audio Research License = non-commercial).
4. **Code presence** — tree-ls or clone the repo; confirm the claimed capability's code actually exists (VibeVoice: TTS/cloning code removed, only ASR + fixed-voice realtime remain).
5. **Maintenance** — `pushed_at` within ~6 months = alive; older = stale (OpenVoice last push Apr 2025 = dead).

## Constraint checklist (adapt to the user's project)
For this user's zero-cost MIT projects, the hard filters are:
- **License:** MIT / Apache-2.0 only. Reject AGPL (copyleft dominates MIT), MPL (file-level copyleft), non-commercial.
- **Self-hosted / offline:** no cloud API keys, no per-character fees.
- **RAM-fit:** model weights must fit the target machine. On a 6 GB laptop, engines >~2 GB are impractical; load on-demand and unload after.
- **Maintenance:** prefer actively-maintained over archived.
- **Interface:** CLI / REST / MCP for agentic pipelines.

## Known pitfalls (verified)
Full voice/TTS audit in `references/voice-models-comparison.md`. Highlights:
- **Fish Speech:** "open-source" but **non-commercial license** — reject for published/commercial use.
- **Coqui XTTS:** **MPL-2.0 + repo archived ~2y** — reject.
- **OmniVoice Studio:** **AGPL** — reject for MIT project.
- **Microsoft VibeVoice:** TTS/cloning **code removed** by Microsoft; only ASR + fixed-voice realtime remain — cannot clone.
- **"Voicebox" desktop app** (unverifiable Instagram-sourced): avoid; the real one is `jamiepine/voicebox` (MIT, verified local, 7 engines, REST+MCP).
- **Voicebox (jamiepine) confirmed headless + on-demand API:** backend runs via `python -m backend.main` (FastAPI, no GUI needed). Verified REST endpoints `POST /models/load` (loads ONE engine), `POST /models/{name}/unload` and `POST /models/unload` (free RAM, keep weights on disk). Models download on first use (proven by `backend/utils/hf_offline_patch.py` forcing offline mode only when cached) — NOT bundled. This is the exact "load-on-demand, unload-after" pattern for low-spec boxes.
- **F5-TTS:** MIT (recently switched from MPL — verify LICENSE on each clone), 1.3 GB, zero-shot 10s ref. **Best standalone clone engine** (lighter than Chatterbox, clean license) when you don't want the heavy Voicebox app.
- **VibeVoice-community fork:** `vibevoice-community/VibeVoice` (MIT, 1.1k★) restored the TTS code Microsoft removed; uses voice-prefill from reference wav but demo only wires bundled presets; 1.5B model impractical on 6 GB. Not for low-spec.
- **OpenVoice:** MIT but **unmaintained since Apr 2025** — avoid as dependency.
- **RVC:** voice *conversion*, not text-to-speech — wrong tool for script→narration.

## Windows git-bash diagnostics (checking disk/RAM on this box)
Standard tools fail here; details in `references/windows-git-bash-diagnostics.md`. Key points:
- Measure directory size with a Python `os.scandir` recursive walk (MSYS `du -sh` times out on large trees; `robocopy`/`dir /s`/PowerShell quoting breaks).
- Inside Python use Windows-style paths `C:\\one\\...` (MSYS `/c/one` doesn't resolve in Python `os.path` here).
- Kill processes with `taskkill /PID <n> /F` (single slash — `//PID` is mangled by MSYS and silently no-ops).
- Windows auto-restarts some killed processes (SearchHost, StartMenuExperienceHost, erl.exe) with new PIDs.

## Presentation note
When asked to compare options "for everyone" vs "for me", give the **general-population** verdict (what's best for the average user/developer) unless the user wants the tailored-to-their-box view. State the constraint-set explicitly so the reader sees why.

## Support files
- `references/voice-models-comparison.md` — verified license + size + RAM-fit audit of voice/TTS models.
- `references/windows-git-bash-diagnostics.md` — techniques for measuring disk/RAM and killing processes from git-bash when standard tools fail.
