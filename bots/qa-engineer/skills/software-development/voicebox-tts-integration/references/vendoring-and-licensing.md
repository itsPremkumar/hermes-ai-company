# Voicebox Vendoring + Licensing Reference

Authoritative facts pulled from `github.com/jamiepine/voicebox` (LICENSE file,
README license statement) and the local clone at `/c/one/voicebox` (commit
`52f8d8d`, 2026-07-20). Used when the user wants to copy Voicebox source into the
AVS project, or asks "is it legal / safe to copy for commercial use?"

## License verdict (verified from raw LICENSE)
- **MIT License**, `Copyright (c) 2026 Voicebox Contributors`.
- Grants: use, copy, modify, merge, publish, distribute, sublicense, **sell**.
- ONLY obligation: include the copyright notice + permission notice in all copies.
- No copyleft, no source-disclosure requirement (unlike GPL).
- README license section: "MIT License — see LICENSE." No Commons Clause, no
  non-commercial restriction.

## What MIT does NOT cover (the real risks)
| Risk | Detail | Mitigation |
|------|--------|------------|
| Trademark / branding | MIT covers code, not the name "Voicebox" or logos (`voicebox-logo.png`, `Voicebox.png`, macOS/iOS `.icon/`). | Keep engine, drop logos, run under your own product name. |
| Model weights | Downloaded at runtime via `huggingface_hub`. Separate licenses: Kokoro=Apache-2.0, Chatterbox=MIT, Qwen=Apache-2.0, Hume=TADA gated/paid. | Don't bundle `.safetensors`. Let users pull at runtime (already the AVS pattern). Zero weight-license exposure. |
| Voicebox Cloud | Paid hosted sync (`voicebox.sh` / `api.voicebox.sh`). Opt-in endpoints in `routes/cloud.py`. | Strip `routes/cloud.py` + `services/cloud.py`. Not called by local TTS. |
| HumeAI TADA | Paid commercial TTS API needing your own key + ToS. `backends/hume_backend.py` pulls `HumeAI/tada-1b`, `HumeAI/tada-3b-ml`. | Strip `backends/hume_backend.py`. Code is MIT; USING it costs money. |
| Third-party deps | Repo bundles many npm/Rust/PyPI deps, each own license (all permissive). | All MIT/Apache. Keeping the repo/lockfile provenance satisfies notices. |

No phone-home / telemetry: scan of `backend/` for `posthog|sentry|mixpanel|telemetry|license.?key|enforce` returned ZERO matches. Server runs air-gapped.

## Exact file tiers (what to copy for AVS)

### Tier 1 — REQUIRED (AVS pipeline breaks without these)
Your `src/lib/voicebox-lifecycle.ts` calls: `GET /models/status` (health, line 57),
`POST /models/load` (line 119), `POST /models/{engine}/unload` + `POST /models/unload`
(lines 131,141), spawns `python -m backend.main --port 17493` (line 91).
- `backend/main.py` — entry point spawned.
- `backend/app.py` — FastAPI factory; mounts `/mcp` (imports `mcp_server` unconditionally).
- `backend/config.py` — data-dir/model-dir/DB paths (pure MIT).
- `backend/backends/__init__.py` + `base.py` — backend abstraction.
- `backend/backends/kokoro_backend.py` — your engine (`VOICEBOX_ENGINE=kokoro`, `af_heart`).
- `backend/services/tts.py` — `audio_to_wav_bytes()`.
- `backend/routes/__init__.py` + `generations.py` + `models.py` + `health.py`.
- `backend/services/__init__.py` + `generation.py` + `profiles.py` + `history.py` + `task_queue.py`.
- `backend/database/*` — SQLAlchemy models/session/migrations/seed.
- `backend/models.py` — Pydantic request/response models.
- `backend/utils/audio.py`, `chunked_tts.py`, `platform_detect.py`, `progress.py`, `cache.py`, `tasks.py`.
- `backend/mcp_server/*` — required because `app.py` mounts `/mcp` at startup.

### Tier 2 — OPTIONAL, high value for video TTS
- `backends/chatterbox_backend.py` / `chatterbox_turbo_backend.py` — expressive TTS with `[laugh]`/`[sigh]` tags (MIT).
- `backends/qwen_custom_voice_backend.py` / `qwen_llm_backend.py` — Qwen3-TTS + NL delivery (Apache-2.0).
- `utils/effects.py` + `services/effects.py` + `routes/effects.py` — pitch/reverb/delay/chorus.
- `routes/speak.py` + `mcp_server/resolve.py` — simpler `POST /speak` one-shot endpoint.
- `backends/pytorch_backend.py` / `mlx_backend.py` / `luxtts_backend.py` — other free engines.

### Tier 3 — DO NOT COPY
- `tauri/`, `app/`, `web/`, `landing/` — desktop/iOS/web UI (bloat + trademark assets).
- `backends/hume_backend.py` — HumeAI paid API.
- `routes/cloud.py` + `services/cloud.py` — Voicebox Cloud paid sync.
- `voicebox-logo.png`, `Voicebox*.png`, `*.icon/` — trademark.
- `backend/pyi_hooks/*`, `build_binary.py` — PyInstaller freezing for desktop builds.

## Vendoring recipe (concrete, VERIFIED — produces a bootable backend)

> **CRITICAL LESSON (2026-07-22):** the naive "delete cloud files + 2 lines in
> `routes/__init__.py`" recipe produces a backend that FAILS TO BOOT
> (`IndentationError` then `ModuleNotFoundError: No module named 'backend'`).
> The cloud/cuda/rocm routers are registered in `routes/__init__.py`, and the
> `tada`/Hume backend is referenced in FIVE more places. The FULL strip list
> below is what actually works — verified by a live `from backend.app import app`
> boot test returning 115 routes.

Target folder used in AVS: `src/adapters/real-voice-backend/` (a `backend/`
subdir inside it). Rename is fine, but be consistent with `VOICEBOX_BACKEND_DIR`.

```
1. Copy the ENTIRE backend/ tree -> src/adapters/real-voice-backend/backend/

2. DELETE these files/dirs:
   - routes/cloud.py            (Voicebox Cloud paid sync)
   - services/cloud.py          (Voicebox Cloud paid sync)
   - backends/hume_backend.py   (HumeAI TADA — paid API)
   - routes/cuda.py             (CUDA GPU-binary auto-updater)
   - services/cuda.py
   - routes/rocm.py             (ROCm GPU-binary auto-updater)
   - services/rocm.py
   - tests/                     (upstream test suite, not needed at runtime)
   - __pycache__/               (bytecode caches — also gitignored)

3. PATCH routes/__init__.py (cloud router is registered here):
   - remove `from .cloud import router as cloud_router`
   - remove `from .cuda import router as cuda_router`
   - remove `from .rocm import router as rocm_router`
   - remove `app.include_router(cloud_router)`
   - remove `app.include_router(cuda_router)`
   - remove `app.include_router(rocm_router)`
   - FIX any stray indentation left on the next line (the partial-delete
     leaves `        app.include_router(health_router)` over-indented ->
     IndentationError). Re-indent to 4 spaces.

4. PATCH app.py (startup wires the deleted GPU updaters):
   - remove `from .services.cuda import check_and_update_cuda_binary`
   - remove `from .services.rocm import check_and_update_rocm_binary`
   - remove `create_background_task(check_and_update_cuda_binary())`
   - remove `create_background_task(check_and_update_rocm_binary())`
   (The `torch.cuda`/`torch.rocminfo` GPU-DETECTION calls in app.py and
   backends/base.py are FINE — keep them. Only the deleted *module* imports
   and their `create_background_task` calls must go.)

5. PATCH backends/__init__.py (the `tada`/Hume backend is referenced in 5 places):
   - TTS_ENGINES dict: remove `"tada": "TADA",`
   - get_tts_backend(): remove the `elif engine == "tada": from .hume_backend import HumeTadaBackend; backend = HumeTadaBackend()` block
   - model-config list: remove BOTH `tada-1b` and `tada-3b-ml` ModelConfig blocks
   - load_engine_model(): remove `elif engine == "tada": await backend.load_model(model_size)`
   - ensure_model_cached_or_raise(): change
     `if engine in ("qwen", "qwen_custom_voice", "tada"):` -> `("qwen", "qwen_custom_voice")`

6. PATCH services/profiles.py:
   - CLONING_ENGINES = {"qwen","luxtts","chatterbox","chatterbox_turbo","tada"}
     -> drop `tada`: {"qwen","luxtts","chatterbox","chatterbox_turbo"}

7. PATCH models.py (engine validation regex, 4 occurrences):
   - pattern="^(qwen|qwen_custom_voice|luxtts|chatterbox|chatterbox_turbo|tada|kokoro)$"
     -> drop `tada` from all four spots.

8. PATCH build_binary.py (packaging only — not imported by the server, but
   clean it so PyInstaller builds don't reference the deleted Hume/TADA/cuda):
   - remove hidden-import `"backend.services.cuda"`
   - remove `--collect-submodules` + `"tada"`
   - remove `"tada"` from the `--exclude-module` list
   (Remaining `tada` comments in dac_shim.py are harmless; the shim is unused
   once Hume is gone — leave the file.)

9. KEEP mcp_server/* — app.py imports it unconditionally (mounts /mcp); app
   won't boot without it (or patch app.py to skip the MCP mount). Cheap to keep.

10. Retain LICENSE + a VENDORED.md note next to the vendored backend. MIT
    requires ONLY the copyright notice: "Copyright (c) 2026 Voicebox Contributors".

11. VERIFY before declaring done — run a LIVE boot test:
    cd src/adapters/real-voice-backend
    /c/one/voicebox/.venv/Scripts/python.exe -c "import sys; from pathlib import Path; sys.path.insert(0,'.'); from backend.app import app; print('routes', len(app.routes))"
    -> expect "routes 115" with no traceback. A passing import = the strip was
       complete. Also confirm required endpoints exist: /models/status,
       /models/load, /models/unload, /models/{model_name}/unload, /generate,
       /health, /speak.
```

## Git decision: gitignore the vendored folder, do NOT commit it

Decision taken 2026-07-22: the vendored `real-voice-backend/` is a LOCAL,
regenerable asset — it is **gitignored, not committed** to the AVS GitHub repo.
Rationale: keeps the repo lean, the source is always recoverable from the local
`/c/one/voicebox` clone via the regen script, and MIT obligations are satisfied
by keeping the LICENSE on disk locally. (If you later want a self-contained repo
with no separate clone step, commit it instead — MIT permits that — but then you
must periodically sync upstream for fixes.)

Gitignore setup (two layers):
- Root `.gitignore`: add `src/adapters/real-voice-backend/` (whole-folder exclusion).
- Scoped `.gitignore` inside `src/adapters/real-voice-backend/` covering Python
  artifacts so even if the outer ignore is removed the folder stays clean:
  ```
  __pycache__/
  *.py[cod]
  .venv/
  data/
  .voicebox-data/
  *.db
  models/
  cache/
  *.wav *.mp3 *.flac *.ogg *.m4a *.aac *.webm
  generations/ profiles/ captures/
  *.log
  ```
- Regeneration: `scripts/vendor-real-voice-backend.mjs` (Node script that copies
  `/c/one/voicebox/backend`, deletes the unwanted files, patches the source
  files, and drops the retained LICENSE). Running it rebuilds the ignored folder
  deterministically — so gitignoring it loses nothing.

Verify the ignore works: `git check-ignore -v src/adapters/real-voice-backend/backend/main.py`
should resolve to the root `.gitignore` line; `git status --porcelain src/adapters/`
should show the folder as NOT tracked.

Your existing `VOICEBOX_BACKEND_DIR` clone path still works — vendoring is additive
and the gitignored folder is the local, offline copy.

## Keep clone updated
```
cd /c/one/voicebox
git fetch origin
git merge --ff-only origin/main        # safe: tree only had untracked test artifacts
git rev-list --count HEAD..origin/main  # should be 0
```
Re-verify strip list after each pull:
`git diff --name-only OLD..NEW -- backend/routes/__init__.py backend/routes/cloud.py backend/services/cloud.py backend/backends/hume_backend.py backend/config.py`
If those 5 are untouched, the recipe above still applies verbatim. (In the
2026-07-05 -> 2026-07-20 jump only `config.py` changed among them.)

## Notes on defaults
- `routes/generations.py` line ~53 hard-defaults engine to `"qwen"` — harmless
  because the AVS client sends `engine: "kokoro"` explicitly.
- `routes/speak.py` mirrors `/generate` for non-MCP callers; resolves profile via
  `mcp_server/resolve.resolve_profile`.
