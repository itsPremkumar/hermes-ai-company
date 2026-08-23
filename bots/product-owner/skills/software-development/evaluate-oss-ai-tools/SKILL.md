---
name: evaluate-oss-ai-tools
description: Evaluate open-source AI models/tools for the user's projects against hard constraints (zero-cost, MIT/Apache license only, self-hosted, fits a 6 GB RAM laptop, CLI/MCP for agentic pipelines). Verify claims with live API data, never trust README marketing.
---

# Evaluate Open-Source AI Tools & Models

Use this when the user asks to pick, compare, or vet any open-source AI model, engine, or app (TTS/voice, vision, agents, etc.) for their projects.

## Hard constraints (from the user's standing rules — verify against these, do not assume)
- **Zero-cost, no paid API keys.** Reject ElevenLabs/Azure/cloud-TTS.
- **License MUST be MIT or Apache-2.0** for shipping inside their MIT projects. REJECT: AGPL (copyleft dominates MIT), MPL (file-level copyleft), and **non-commercial** licenses (Fish Speech's "Fish Audio Research License" forbids commercial use).
- **Self-hosted / offline.** Models run on the user's machine; data stays local.
- **Fits ~6 GB RAM** (laptop shows ~5.86 GB total, often < 400 MB free, 280+ procs). Model size is the deciding filter after license.
- **Agentic-ready:** prefer engines with CLI / REST / MCP so the `orchestrate.ts` pipeline can drive them headlessly.

## Method — VERIFY, don't trust claims
Marketing/README copy is frequently wrong (this user explicitly distrusts unverified claims). Pull live data:

**1. License (real, not claimed):**
```bash
curl -s https://api.github.com/repos/OWNER/REPO | python -c "import sys,json;d=json.load(sys.stdin);print('license:',(d.get('license') or {}).get('spdx_id'));print('stars:',d.get('stargazers_count'));print('pushed:',d.get('pushed_at'))"
```
For "NOASSERTION" on GitHub, fetch the raw `LICENSE` file — it usually hides a non-commercial/MPL clause (e.g. Fish Speech).

**2. Model size (RAM fit):**
```bash
curl -s "https://huggingface.co/api/models/OWNER/REPO/tree/main?recursive=true" | python -c "import sys,json;d=json.load(sys.stdin);tot=0;[tot:=tot+(f.get('size') or 0) for f in d if f['path'].endswith('.safetensors')];print('TOTAL',tot//1024//1024,'MB')"
```

**3. Bundled vs download-on-demand:** check backend source for `snapshot_download` / `hf_hub_download` / `from_pretrained` and any `hf_offline_patch.py` (proves weights fetch from HF at runtime, not shipped).

**4. Maintenance:** `pushed_at` recent = alive; archived/stale (Coqui XTTS archived ~2y, OpenVoice stale since Apr 2025) = avoid.

## Decision pattern
- License clean + size fits + maintained + agentic interface → **recommended**.
- License violated → **reject** regardless of quality.
- Size too big for 6 GB → **load on-demand then unload**, or pick a lighter alternative.
- "Code removed by vendor" (Microsoft VibeVoice-TTS) or "fixed voices only" → **not a cloning engine**, reject for cloning needs.

## VRAM-vs-RAM on the user's GPU laptop (KEY for ML model fit)
The "6 GB RAM" constraint is the **system RAM**, but the box also has a
**discrete GPU** (RTX 3050, 4096 MiB VRAM). The deciding factor for heavy
models is which memory they load into:
- **CPU torch (default pip install torch)** loads weights into SYSTEM RAM →
  OOMs on a 5.86 GB box (Qwen 1.7B at 3.6 GB killed the process).
- **CUDA torch (`torch==X.Y.Z+cu126` from download.pytorch.org/whl/cu126)**
  loads weights into **VRAM** → frees system RAM, makes 4 GB-class models
  viable IF they fit the 4 GB VRAM (minus ~1 GB OS/CUDA overhead → ~3 GB usable).
- **Sizing rule:** model VRAM footprint must be < ~3 GB to run on the 4 GB
  card. Kokoro-82M (~0.8 GB VRAM) ✅; Chatterbox-Turbo (~3.8 GB VRAM) ⚠️ fits
  but leaves no headroom (don't co-run a GPU render); Qwen 1.7B (>4 GB) ❌.
- **Pitfall:** some pip packages (e.g. `chatterbox-tts`) DOWNGRADE torch to
  CPU-only. After installing such a dep, reinstall CUDA torch explicitly:
  `uv pip install --index-url https://download.pytorch.org/whl/cu126 "torch==2.13.0+cu126" "torchaudio==2.11.0+cu126"`.
- **Network note:** the pytorch CDN occasionally returns HTTP 200 but 0-byte
  transfer (transient block). If a CUDA reinstall stalls >10 min, retry later
  or reuse uv's cached wheel (`UV_OFFLINE` won't help if uv tries index first;
  use `--offline --no-deps` against a cached version, or wait for CDN recovery).

## HARD POLICY: do NOT clone a famous/real person's voice
When the user asks to clone a celebrity/famous-person voice (for video narration,
impersonation, etc.), **refuse the impersonation** and offer the legal alternatives.
This is a standing decision from the Voicebox integration session — not a technical
limit but a legal/ethical one:
- Cloning a specific identifiable real person's voice risks right-of-publicity /
  personality-rights violations, platform TOS breaches (YouTube etc.), and the
  MIT tool licenses (Voicebox, Chatterbox) do not permit impersonating real
  individuals.
- Offer instead: (A) Kokoro **fictional preset** narrator voices (af_heart,
  am_adam, af_bella, ... — license-clean, zero setup); (B) clone the USER'S OWN
  voice (they supply a 10-30s clip → `scripts/setup-voicebox-clone.mjs`); or
  (C) a voice they have explicit written permission to use.
- Phrase it clearly as a line you won't cross, then immediately give the legal path.

## Voicebox-specific contract
jamiepine/voicebox is the user's chosen clone backend. Its API has non-obvious
traps (`/models/load` is Qwen-only; generation is profile-based via `/speak`).
Full verified contract + engine VRAM table: **`references/voicebox-integration.md`**.

## Reference
- `references/voice-tts-models.md` — verified 14-model TTS/voice comparison
  (license + size + RAM-fit + clone-capability); recommended stack: Kokoro
  (default narrator) + F5-TTS/Chatterbox/Voicebox (on-demand clone).
- `references/voicebox-integration.md` — Voicebox REST contract, /speak async
  flow, profile creation, and VRAM engine-sizing for the 4 GB RTX 3050.
