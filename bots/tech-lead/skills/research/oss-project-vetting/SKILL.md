---
name: oss-project-vetting
description: Evaluate whether an open-source AI/software project is fit for adoption — verify license cleanliness (MIT/Apache only for MIT projects; reject AGPL/MPL/non-commercial), model/resource size, ACTUAL capability vs marketing claims, and fitness for constrained hardware. Use whenever the user asks "is X suitable for my project", pastes a comparison list of tools, wants a free/self-hosted alternative, or is evaluating voice/TTS/ML models for a low-spec laptop.
---

# OSS Project Vetting

Adopting the wrong open-source dependency is expensive. Marketing copy (README badges, blog roundups, "open-source alternative to ElevenLabs" claims) is routinely **false or misleading** about license, capability, and self-hosting. Always verify against the source of truth, never the claim.

## When to use
- "Is <project> suitable for my project?"
- "Compare these voice/TTS/cloning models and tell me the best fit."
- "Find a free, self-hosted, privacy-first alternative to <paid tool>."
- Any "add <OSS thing> to my pipeline" request where license or resource fit is unknown.

## Verification sequence (do ALL, in order)

### 1. License — hard filter first
```bash
curl -s https://api.github.com/repos/OWNER/REPO | python -c "import sys,json;d=json.load(sys.stdin);print((d.get('license') or {}).get('spdx_id'))"
```
- **Clean for an MIT project:** `MIT`, `Apache-2.0`, `BSD*`.
- **Reject:** `AGPL-3.0` (copyleft dominates MIT shipping path), `MPL-2.0` (file-level copyleft; also usually a dead project), anything `NOASSERTION` or missing.
- **`NOASSERTION` is a RED FLAG, not "open".** Fetch the raw LICENSE and read it — it almost always hides a **non-commercial** clause (e.g. Fish Speech = "Fish Audio Research License", commercial use forbidden). See `references/verified-voice-models.md` for the worked example.
- Don't trust the README's "open-source" label. Verify the actual license file.

### 2. Maintenance status
```bash
curl -s https://api.github.com/repos/OWNER/REPO | python -c "import sys,json;d=json.load(sys.stdin);print('pushed',d.get('pushed_at'),'stars',d.get('stargazers_count'))"
```
- **Reject archived/stale:** Coqui XTTS (archived ~2y), OpenVoice (stale since Apr 2025). A dead project = no security fixes, bit-rot.
- Active = pushed within last few months.

### 3. Model / resource size (HuggingFace)
```bash
curl -s "https://huggingface.co/api/models/OWNER/REPO/tree/main?recursive=true" | python -c "
import sys,json
d=json.load(sys.stdin)
tot=0
for f in d:
    if isinstance(f,dict) and f.get('path','').endswith(('.safetensors','.bin','.pt')):
        sz=f.get('size')
        if isinstance(sz,int): tot+=sz
print('model weights: %.2f GB'%(tot/1024**3))
"
```
- This decides fitness for a **low-spec laptop** (the user's box: ~6 GB RAM, often <400 MB free, 280+ procs). A model that needs >2 GB RAM resident is impractical there.
- Note: many apps (e.g. Voicebox) **do NOT bundle weights** — they download on demand from HF. Verify by reading the backend source for `hf_hub_download` / `snapshot_download` / `from_pretrained` and the presence of an offline-patch (proves models are fetched at runtime, not shipped).

### 4. Capability — read the SOURCE, not the README
Marketing claims lie about cloning. Verify:
- **Does it actually clone, or only ship preset voices?** Grep the inference code for `reference`, `voice_prompt`, `clone`, `speaker_embedding`, `prefill`. If it only scans a `voices/` folder of bundled `.wav` presets → it does NOT clone your voice (VibeVoice realtime = fixed presets; VibeVoice-TTS code was *removed* by Microsoft).
- **Is it truly local / no cloud key?** Grep the engine backend for `requests.`, `httpx`, `api_key`, `os.getenv`. If empty → runs on-device (Voicebox's hume_backend.py imports torch + local shim, no HTTP = verified local).
- **Is the "TTS" code even present?** Microsoft removed VibeVoice-TTS; the repo only has ASR + fixed-voice realtime. A docs page linking to HF weights with no `inference.py` = code was pulled.

### 5. Interface for agentic pipelines
For an automated pipeline you need a headless surface: REST API, MCP server, or Python lib/CLI. Confirm it exists in the repo (`backend/server.py`, `mcp_server/`, `--port` args). GUI-only apps are harder to automate.

## Pitfalls (learned the hard way)
- **"Open-source" ≠ license-clean.** Fish Speech (31k★) is NON-COMMERCIAL. OmniVoice is AGPL. Both were pitched as free alternatives.
- **"Removed code" leaves a zombie repo.** VibeVoice still has a shiny README + 50k★ but the cloning code is gone. Stars != usable.
- **Archived + copyleft = double reject.** Coqui XTTS: MPL-2.0 AND archived.
- **Unverifiable "desktop app" claims.** A project cited only via Instagram reels + a docs site (original "Voicebox" paste) was NOT the real repo. The real `jamiepine/voicebox` (MIT, 42k★) exists and is legit — but you must confirm the actual repo, not trust the blog.
- **Why Microsoft removed VibeVoice-TTS but not the indie Voicebox:** Microsoft *owns* the model and a corporate responsible-AI board deleted it on misuse. Voicebox is an independent MIT *aggregator* of third-party engines — no single corporate owner can yank it, and MIT means it's already forked everywhere. Structural, not technical.

## Low-spec hardware fitness rule
On a ~6 GB RAM laptop: standalone **Kokoro-FastAPI (82M weights, ~312 MB)** = always-on narrator; clone engines (Chatterbox Turbo 350M, F5-TTS 1.3 GB, Qwen3-TTS 0.6B) = **load on demand, unload after**. Never run all engines at once. Reject anything needing >2 GB resident.

**CRITICAL correction (verified 2026-07-18):** the `jamiepine/voicebox` *bundled* Kokoro is NOT 312 MB — its HF repo downloads **3.86 GB** (`model.safetensors`) and **OOMs a 5.86 GB box during model init** (backend process dies silently; port stops listening). So Voicebox's own engines are NOT usable on this laptop, even headless. The 312 MB "lightweight Kokoro" claim applies only to the standalone Kokoro-FastAPI server, NOT Voicebox's bundled engine. For this box, use Edge-TTS (default, zero RAM) or standalone Kokoro-FastAPI; keep Voicebox wired but fail-safe to Edge-TTS (it works on ≥16 GB RAM machines). Install pitfalls for Voicebox on this box (PYTHONPATH leak, `python -m venv` broken → use `uv venv --python 3.11`, stale-port kill) are in `free-dev-team` → `references/windows-python-voicebox-isolation.md`.

## Output format for the user
A comparison table (License | Size | Clones? | Maintained? | RAM fit | Interface) + a clear "best fit" call + an explicit "rejected, because X" list. See `references/verified-voice-models.md` for a fully worked example.

## Reference files
- `references/verified-voice-models.md` — license-verified TTS/voice-clone model table (the user's video project uses this repeatedly).
- `references/verification-techniques.md` — exact API commands, Windows git-bash sizing workaround, and repo-cleanup safety rules.
