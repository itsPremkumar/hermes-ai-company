# License Vendoring Framework

## The four-layer classification (read the LICENSE file, not the README badge)

A repo's top-level "MIT" license covers ONLY its own **source code**. "The repo"
= MIT code + things MIT does NOT cover. Audit each layer you actually use.

| Layer | License source | Can you copy? | Can you sell/commercialize? | Duty |
|-------|---------------|--------------|------------------------------|------|
| **App/source code** | repo LICENSE (e.g. MIT) | ✅ yes | ✅ yes (MIT literally says "sell") | Retain LICENSE + copyright notice |
| **Model weights** | each model's own license (Apache-2.0/MIT/common) | ✅ at runtime | ✅ usually | Don't bundle; download at runtime |
| **Trademark / name / logos** | NOT in any code license | ❌ re-brand as them | ❌ | Drop logo/name; use your own |
| **Paid/commercial API** | provider ToS (not MIT) | code copy OK | using needs paid key + ToS | Strip the module |

## Worked example: jamiepine/voicebox (MIT, Copyright 2026 Voicebox Contributors)
Vendored into an Automated-Video-Generator project as a local TTS backend.

- **MIT code kept**: FastAPI server, `backends/` (Kokoro/Apache-2.0 wrapper, Chatterbox/MIT, Qwen/Apache-2.0), `services/`, `routes/`, `chunked_tts.py` (unlimited-length+crossfade), `mcp_server/`.
- **Stripped (paid/cloud/bloat)**: `routes/cloud.py` + `services/cloud.py` (Voicebox Cloud SaaS), `backends/hume_backend.py` (HumeAI TADA paid API), `routes/cuda.py`+`services/cuda.py` + `rocm` (GPU binary auto-updaters), `tests/`, `pyi_hooks/`, `build_binary.py` dead tada refs, `build_binary.py`.
- **Trademark dropped**: `voicebox-logo.png`, `Voicebox*.png`, `*.icon/` — never vendored.
- **Weights**: Kokoro/Chatterbox/Qwen pulled via `huggingface_hub` at runtime — never in the tree.
- **Verified**: `from backend.app import app` → 115 routes; all required endpoints (`/generate`, `/models/load`, `/models/status`, `/speak`, `/health`) present.

## Common license traps
1. **"MIT" repo with a Commons Clause / "non-commercial" extra file** — read the full LICENSE; if present, commercial use is forbidden. Voicebox has no such clause (verified).
2. **Copyleft (GPL/AGPL)** upstream — would force you to open-source your project. Vendoring GPL code is fine for internal use but NOT for a closed-source product. Prefer MIT/Apache upstreams.
3. **Model weights with RAIL/community licenses** (e.g. some Llama/Mistral variants) — restrict commercial use or outputs. Check each weight's license before relying on it.

## Verification checklist before declaring a vendored copy "commercial-safe"
- [ ] Read the actual LICENSE file (raw, not the badge).
- [ ] No Commons Clause / non-commercial addendum.
- [ ] LICENSE + copyright line retained next to vendored code.
- [ ] No upstream trademark assets shipped.
- [ ] No paid-API modules enabled.
- [ ] Model weights downloaded at runtime, not bundled.
- [ ] Boot test passes (import the app).
