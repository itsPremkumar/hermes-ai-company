---
name: oss-backend-vendoring
description: Copy a third-party open-source backend/package (e.g. a TTS/ML server, API, CLI) into your own project as a self-contained, strip-cleaned, license-compliant local module. Covers the license audit (MIT code vs model weights vs trademark vs paid API), deleting paid/cloud/bloat parts, PATCHING the import/registration graph so boot doesn't break, retaining the LICENSE, choosing gitignore-vs-commit, and verifying it boots when there is no test suite. Use whenever you vendor an upstream MIT/Apache tool instead of shelling out to a separate clone.
---

# oss-backend-vendoring

Embed an upstream open-source backend directly in your repo: copy it, strip the
parts you don't use (paid/cloud/commercial/UI bloat), stay legally safe, and prove
it still boots.

## When to use
- You want a third-party tool (TTS server, ML backend, API) self-contained in your
  repo instead of requiring users to `git clone` it separately or download at setup.
- The upstream ships paid/cloud/commercial features or desktop/web UI you don't use.
- You need commercial use to be legally clean.

## Step 0 — License audit (BEFORE copying)
Read the repo's **actual LICENSE file**, not just the README badge. Then classify
what you'll actually use — the code license is NOT the model/asset license:
- **MIT/Apache CODE you copy** → free to use/modify/sell; only duty = retain LICENSE + copyright line.
- **Model weights** (downloaded at runtime: Kokoro, Chatterbox, Whisper, Qwen) → their own licenses (usually Apache/MIT). NEVER bundle `.safetensors`/`.bin`; let them download at runtime so they never enter your tree.
- **Trademark/branding** (name, logos) → NOT covered by MIT. Drop logo/name assets; run under your own product name.
- **Paid/commercial APIs** (e.g. HumeAI, upstream "Cloud" SaaS) → code may be MIT but *using* it needs a key + their ToS. Strip these modules.
Full matrix + worked example in `references/license-vendoring-framework.md`.

## Step 1 — Copy into a clean subfolder (never modify the original clone)
```
cp -r /path/to/upstream/backend  src/adapters/<name>/backend
```
The original upstream clone stays your regeneration source.

## Step 2 — Delete unwanted modules
Remove paid/cloud/bloat files (e.g. `routes/cloud.py`, `services/cloud.py`,
`backends/hume_backend.py`, `routes/cuda.py`, `services/rocm.py`, `tests/`,
`__pycache__/`).

## Step 3 — PATCH registration/import references (CRITICAL — boot WILL break otherwise)
Deleting a module that is **imported in an `__init__.py` or `app.py`** raises
`ModuleNotFoundError`/`ImportError` at startup. After deleting, grep the whole tree
for each removed module name and fix every reference:
- Router registration lists (`routes/__init__.py`: `from .cloud import router as cloud_router` AND `app.include_router(cloud_router)`).
- `app.py` startup imports/calls (`from .services.cloud import ...`, `create_background_task(cloud_sync())`).
- Engine dispatch (`backends/__init__.py`: `TTS_ENGINES` dict, `get_tts_backend_for_engine` `elif engine == "tada":`, `load_engine_model`, `ensure_model_cached_or_raise`).
- Re-export lists (`database/__init__.py`: `from .models import (... CloudSettings ...)` + `__all__`).

### Step 3b — Flattening or renaming the package (the ref-name trap)
If you flatten the upstream layout (`backend/` → package lives directly at
`src/<name>/`, e.g. `src/speech/main.py`) or rename the package, you MUST update
**hardcoded absolute package-name references** — the import graph breaks at runtime,
not at import time, so a plain import check passes while the server still dies.
- Grep for package-name refs: `tts.main|from tts import|import tts\b` and the
  uvicorn target string `"backend.main:app"` / `"tts.main:app"`.
- `main.py`: `uvicorn.run("speech.main:app", ...)` — this string is ONLY used when
  the server actually starts; an import check will NOT catch a wrong value.
- `server.py` / PyInstaller entry: `from speech import config` etc.
- **CRITICAL distinction — package name vs module name with the same word:**
  `from ..services import tts` / `from . import tts` refer to a **file** `services/tts.py`
  (the TTS *service* module) and MUST KEEP the name `tts`. Only `from tts import ...`
  (no dot, top-level package) and `"tts.main:app"` (uvicorn target) are package refs
  to rename to `<name>`. Grep and read each hit; don't blind-replace.
- Also update the TS spawner (see Step 8): `python -m <name>.main`, `cwd`,
  `pythonExe()`, `.env` `<NAME>_BACKEND_DIR`, and `backendDir()` default.

## Step 4 — Scrub residual references
- `config.py`: remove helper/URL funcs for the removed service (e.g. `get_cloud_web_url()`).
- **DB models**: remove the ORM table class (e.g. `CloudSettings`) — but FIRST grep to confirm nothing else imports it.
- Packaging scripts (`build_binary.py`): remove `--hidden-import`/`--collect-submodules` entries for deleted modules (dead but misleading).
- Pydantic `pattern=` regex validators: drop removed engine names (e.g. `tada`) so validation matches available engines.
- Comment-only mentions are harmless; optional to clean.

## Step 5 — Retain the LICENSE (the only hard MIT duty)
Copy the upstream `LICENSE` next to the vendored folder; keep the copyright line
(e.g. `Copyright (c) 2026 Voicebox Contributors`). Add a `VENDORED.md` noting the
source commit + what was stripped.

## Step 6 — Git strategy (commit vs gitignore-as-local-artifact)
- **Commit** → repo is self-contained for clones (most common).
- **Gitignore as local artifact** → if the folder is large/regenerable: add
  `src/adapters/<name>/` to root `.gitignore` with a comment pointing at the regen
  script, and keep the vendoring script in the repo so it's reproducible.
- Either way, scope a `.gitignore` INSIDE the folder for `__pycache__/`, `*.py[cod]`,
  `.venv/`, `data/`, `*.db`, `models/`, `cache/`, generated audio.
- Accidental commit, NEVER pushed? `git reset --mixed HEAD~1` — files preserved on
  disk, commit gone, nothing touches remote. (Do NOT `git reset --hard` — deletes files.)

### Step 6b — The cwd-relative RUNTIME DATA-DIR leak (common, silent)
Many backends resolve their data dir relative to `cwd` (e.g. `config._data_dir =
Path("data").resolve()`). If your TS spawner runs them with `cwd = src/` (or any
project dir), the server writes `src/data/<name>.db` / profiles / audio **inside the
repo** — which is NOT covered by the folder-only `.gitignore`, so it shows as
Untracked in VS Code / `git status`. Fix BOTH ways (defense in depth):
1. Pass `--data-dir <gitignored path>` at spawn (e.g. `workspace/cache/<name>/`,
   which your project already gitignores), AND/OR set `<NAME>_DATA_DIR` if the
   backend reads it.
2. Add `src/data/`, `*.db`, `<name>.db` to root `.gitignore` as a leak catch.
3. Delete any leaked `src/data/` from disk and re-verify `git status` shows only the
   intended file changes.

## Step 8 — TS-side integration contract (when the host app is TypeScript)
The vendored backend is spawned as a child process by the host app. Wire it so input
(text) and output (audio) flow through the project's existing pipelines:
- **Spawner** (`src/lib/<name>-lifecycle.ts`): `backendDir()` returns the dir whose
  parent makes `<name>` an importable package; spawn `python -m <name>.main` with
  `cwd` = that parent. Fix `pythonExe()` to point at the real venv (avoid `||` chains
  referencing deleted paths like `src/tts/.venv`).
- **`.env`**: set `<NAME>_BACKEND_DIR` to the vendored path (NOT the upstream clone),
  keep `<NAME>_PYTHON` at the real venv, `<NAME>_API_URL` at the chosen port.
- **Provider routing**: a `TTS_PROVIDER`/`*_PROVIDER` env selects the backend; the
  call site (e.g. `api-tts-provider.ts`) does POST `/speak` → poll
  `/generate/{id}/status` → GET `/audio/{id}`, writing output to the agentic
  workspace `audio/` dir. Confirm the call-site shape matches the backend's actual
  routes (read both sides); a mismatch is a silent fallback to Edge-TTS, not a crash.
- **Backward-compat**: if the backend is down / no profile set, the pipeline must
  fall back to the existing engine (Edge-TTS) — never hard-fail the whole job.
- After editing the `.ts`, run the project's `npm run typecheck` — that IS the valid
  verification for the TS side (covers the spawner).

## Step 7 — Verify it boots (no test suite exists for vendored Python)
There is usually no `npm test`/`pytest` for the vendored backend. Verify by importing
the app from INSIDE the backend folder:
```python
# write a temp _boot.py INSIDE the folder, run, then delete it
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from backend.app import app
print("routes:", len(app.routes))
```
Pitfall: `python -c "import sys; sys.path.insert(0,'.'); from backend.app import app"`
fails with cwd drift — write the script file *inside* the folder instead. After
import, `__pycache__/*.pyc` regenerates; clear with
`find . -name __pycache__ -type d -exec rm -rf {} + ; find . -name '*.pyc' -delete`.

### Step 7b — An import check is NOT enough (start the server)
Importing the app only exercises module load. The **uvicorn target string**
(`uvicorn.run("backend.main:app")` or `"speech.main:app"` in `main.py`) is only
resolved when the server actually runs — a wrong value survives import but crashes
`on `python -m <name>.main`. Prove it with a **background boot + /health poll** so the
server stays up long enough to answer:
```python
# write to C:/tmp/boot_health.py OUTSIDE the repo (no project artifacts left)
import sys, subprocess, time, urllib.request
from pathlib import Path
sys.path.insert(0, r"C:\one\Automated-Video-Generator\src")
r = subprocess.Popen([r"C:\one\voicebox\.venv\Scripts\python.exe", "-m", "speech.main",
                      "--host","127.0.0.1","--port","17499"], cwd=r"C:\one\...dsd\src",
                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
for _ in range(40):
    time.sleep(1)
    try:
        with urllib.request.urlopen("http://127.0.0.1:17499/health", timeout=2) as resp:
            print("HEALTH", resp.status); break
    except Exception: pass
```
If it only errors with `No module named 'backend'` after ~instant, the package-name
ref (Step 3b) is still wrong. A 30s+ *timeout* (not instant error) means it started
and is just serving — that's the PASS case. Run boot scripts from `C:/tmp` (not in the
repo) so no `_boot.py` is left in the project tree. Clear `.pyc` after.
A `.gitignore` edit triggers "unverified" reminders with no test target — verify with
`git check-ignore -v <path>` (path printed = ignored).

## Step 9 — Self-driving stage integration (no user config, real-time-capable)
Vendoring the code is only half the job. To make the backend act as ONE system with the
host pipeline (user goal: "first-class stage, no asking"), wrap it in a single controller
that the orchestrator calls like any other stage (mirror the host's asset/acquire stage:
input = scene text, output = workspace audio, zero prompts).

### 9a — The controller seam (`src/agentic/media/<name>-controller.ts`)
One module owns the WHOLE lifecycle (do NOT scatter `ensureBackend()` calls inside the
call-site like the old `api-tts-provider.ts` did):
1. `ensureBackend()` → spawn if not up.
2. **Auto-provision a profile** (see 9b) — never require the user to set a profile id.
3. **Preload the engine** (`POST /models/load?model_size=<x>` — QUERY param,
   NOT a JSON body) at stage start → no per-scene cold stall. BUT see Pitfall
   "PRELOAD endpoint shape & engine support": that route drives the DEFAULT
   Qwen/Chatterbox loader and CANNOT load "kokoro" (500s). For kokoro, SKIP
   the preload — it loads lazily inside `/speak`. Default the engine to the
   lightest (kokoro, NOT chatterbox_turbo).
4. Generate per scene: `POST /speak {text, profile, engine, language}` → poll
   `GET /generate/{id}/status` (SSE — grab first `data:` frame) → `GET /audio/{id}`
   stream to `ws.audioDir/scene_{N}_voice.wav`. Reuse existing file (idempotent).
5. `unloadAll()` → `killBackend()` when the stage ends → **RAM returns to zero**
   (critical on a 6 GB box). Emit `percent` to the orchestrator so the UI shows live progress.

### 9b — Auto-provision the voice profile (the "no ask" core)
Voicebox is profile-based; create one on first run, cache the id. Profile-create schema
(`models.VoiceProfileCreate`, validated by the backend):
```json
POST /profiles
{ "name": "agentic-kokoro-af_heart", "voice_type": "preset",
  "preset_engine": "kokoro", "preset_voice_id": "af_heart" }
// → { "id": "<uuid>", ... }
```
Resolution priority in the controller: (1) explicit `VOICEBOX_PROFILE_ID` env (back-compat)
→ (2) cached id in `<ws>/cache/voicebox-profile.json` → (3) `POST /profiles` auto-create
+ persist. This is what removes the manual setup step.

### 9c — `ensureBackend()` gate on PROVIDER, not profile
A common bug: `ensureBackend()` bails unless `VOICEBOX_PROFILE_ID` is set. That's wrong —
profile is provisioned LATER (9b). Gate startup on `TTS_PROVIDER` instead:
```ts
const provider = (process.env.TTS_PROVIDER||'').toLowerCase().trim();
if (provider && provider !== 'voicebox') return false;  // don't burn RAM otherwise
```
Gating on profile makes the backend refuse to start, then silently fall back to Edge-TTS
on every voiceover call — defeating the native backend.

### 9d — Engine default mismatch (silent fallback trap)
The call-site often defaults the engine to a HEAVY one while `.env` says `kokoro`.
e.g. `voice-generator.ts` had `process.env.VOICEBOX_ENGINE || 'chatterbox_turbo'`.
Fix to `|| 'kokoro'` so a default run actually uses the light engine. Mismatch → slow/oom.

### 9e — Add `audioDir` to the workspace type
If the host `AgenticWorkspace` lacks an audio dir, add `audioDir: path.join(root,'audio')`
to BOTH the interface AND `buildWorkspacePaths()`. Then fix every test that builds a
literal `AgenticWorkspace` (they'll fail typecheck with "Property 'audioDir' is missing")
by adding `audioDir: <same-as-root-or-dir>`.

### 9f — Orchestrator wiring (primary + fallback)
```ts
try {
  const { runVoiceStage } = await import('../media/<name>-controller.js');
  const res = await runVoiceStage(plan, ws, req.voice, (p,m)=>emit({stage:'voiceover',percent:p,message:m}));
  voiceovers = normalize(res);            // map controller output → existing shape
} catch (e) {
  voiceovers = await generateAgenticVoiceovers(plan, ws, req.voice);  // Edge-TTS fallback
}
```
Keep the existing fallback path so the pipeline NEVER hard-fails on voice.

### 9g — LIVE integration test (the real proof)
The host test runner is **`node --import tsx --test --test-timeout=120000`** (Node built-in
test runner, NOT vitest). Write `src/agentic/media/<name>-controller.test.ts` that:
- sets `TTS_PROVIDER=voicebox`, `VOICEBOX_PYTHON=<real venv>`, and `delete process.env.VOICEBOX_PROFILE_ID`
  (to exercise the AUTO-PROVISION path),
- builds a minimal `Plan` + `AgenticWorkspace` (temp `mkdtemp`),
- calls `runVoiceStage`, asserts `voices.length`, `voiceoverDriven===true`, each WAV `>1000` bytes,
  `profileId` resolved, and `src/data` ABSENT (no leak),
- `killBackend()` + `rmSync(ws.root)` cleanup.
Run it: `node --import tsx --test --test-timeout=240000 src/agentic/media/<name>-controller.test.ts`.
Cold Kokoro load ~60-90s → use a long timeout. A PASSED run (pass 1 fail 0, real WAVs,
auto-provisioned profile, backend killed) is the production-readiness proof. This is the
verification gate for the whole integration; `npm run typecheck` only covers the TS wiring.

## Pitfalls
- Don't `git reset --hard` to undo a commit — it deletes your files. Use `--mixed`/`--soft`.
- Don't only `rm` a module and assume clean — the import graph breaks at boot. Always grep + patch.
- Don't bundle model weight files — weight licenses + repo bloat. Download at runtime.
- Don't ship upstream logos/name — trademark, not covered by MIT.
- A `.py`/`.gitignore` edit with no test command attached will be flagged "unverified"; the valid verification is the boot import + `git check-ignore`.
- **Flatten/rename trap**: importing the app ≠ booting it. The `uvicorn.run("<pkg>.main:app")` target string is only resolved at server start; a wrong package name survives import, then crashes. Always do a background boot + `/health` poll (Step 7b).
- **Package name vs module name**: `from ..services import tts` targets a *file* (`services/tts.py`) — keep it. Only rename `from tts import ...` (top-level pkg) and the `"tts.main:app"` uvicorn string to `<name>`.
- **cwd-relative data-dir leak**: a backend resolving its data dir from `cwd` writes `src/data/*.db` inside your repo (Untracked in git). Redirect via `--data-dir`/`<NAME>_DATA_DIR` to a gitignored path AND add `src/data/`, `*.db` to `.gitignore` as catch.
- **`ensureBackend()` gate on PROVIDER, not profile**: gating startup on `VOICEBOX_PROFILE_ID` makes the backend refuse to spawn, then silently fall back to Edge-TTS — the native backend never runs. Gate on `TTS_PROVIDER` instead; provision the profile later.
- **Engine default mismatch**: a call-site default like `VOICEBOX_ENGINE || 'chatterbox_turbo'` while `.env` says `kokoro` makes default runs use a heavy engine (slow/oom). Align the default to `kokoro`.
- **`audioDir` missing from workspace type**: adding `audioDir` to `AgenticWorkspace` breaks every test that builds the literal — they fail typecheck with "Property 'audioDir' is missing". Add `audioDir` to BOTH the interface and `buildWorkspacePaths()`, then to each test literal.
- **Self-driving needs a LIVE integration test**: `npm run typecheck` only proves TS wiring. The real gate is a `node --import tsx --test` run against the live backend that asserts real WAVs + auto-provisioned profile + no `src/data` leak + backend killed. Cold Kokoro ~60-90s → long timeout.
- **PRELOAD endpoint shape & engine support**: Backend `POST /models/load` takes
  `model_size` as a QUERY param (NOT a JSON body) — sending `{model_size}` as a
  body silently 500s. Worse, that route only drives the DEFAULT Qwen/Chatterbox
  loader and CANNOT load "kokoro" (errors with "Failed to load model"). Kokoro
  loads LAZILY inside `POST /speak`, so preloading kokoro via `/models/load` is
  both pointless and errors. FIX: call `/models/load?model_size=<x>` for
  preloadable engines (chatterbox/qwen), and SKIP the preload entirely for
  kokoro. Make `loadEngine` catch+return-false on 500 so a non-fatal miss never
  crashes the stage. (Caught after a real run logged "engine load failed
  (kokoro): 500" yet still produced audio via lazy load — the warning was
  misleading and the preload was dead.)

## References
- `references/license-vendoring-framework.md` — MIT-vs-weights-vs-trademark-vs-paid-API matrix + Voicebox worked example.
- `references/rename-flatten-package.md` — the ref-name trap: which `tts` hits are package refs vs the `services/tts.py` module; exact grep patterns + the uvicorn-target bug.
- `references/self-driving-stage-integration.md` — Step 9 detail: auto-provision profile payload, per-scene `/speak`→`/audio` shape, the proven `node --import tsx --test` integration test, and gotchas from the real AVS Voicebox→`src/speech` integration.

## Support files
- `scripts/vendor-strip-template.mjs` — re-runnable copy+strip+patch+license script template.
- `scripts/boot-health-check.py` — spawn the vendored package from C:/tmp, poll /health, report DB location + leak check (NO project artifacts left).
