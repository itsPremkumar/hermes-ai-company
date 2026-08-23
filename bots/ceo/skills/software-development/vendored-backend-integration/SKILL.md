---
name: vendored-backend-integration
description: Vendor a third-party open-source backend (Python/FastAPI) into a TypeScript/JS project as a LOCAL, gitignored, ZERO-CONFIG subprocess. Covers license compliance, gitignore hygiene, a self-driving controller, LIVE verification, and STRIPPING THE UPSTREAM BRAND from file names / identifiers / committed config. Use when the user wants to copy/reuse another repo's server code into their project, integrate a local TTS/ML/API engine into an agentic pipeline, make a vendored backend need no separate env/setup step, OR remove the upstream project name (e.g. "voicebox") from the repo. The full class is audit license, vendor plus rename, gitignore, spawn correctly, auto-provision runtime resources, zero-config, strip brand, then test against the live backend.
---

# Vendored Backend Integration

Copy a third-party open-source server into your project and wire it as a local
subprocess that the app drives — without leaking files into git, without
requiring the user to set up env vars, and without breaking on repeat runs.

## When this applies
- "copy this repo's backend into my project / vendor it locally"
- "users can separately download and configure X, or we copy it in"
- Integrating a local TTS/ML/API engine (Voicebox, Kokoro, Whisper, ComfyUI)
  into an agentic/TS pipeline as a first-class stage.
- "make it zero-config / no env setup needed"

## Workflow (plan, then implement, then verify)
For large integrations the user expects a DETAILED plan first, then full
implementation plus live tests. Do not skip the verify step.

### 1. License audit (BEFORE copying)
- MIT/Apache-2.0: you may vendor, modify, and use commercially. ONLY duty is
  retain the LICENSE file plus the copyright/permission notice in copies.
- Strip paid/cloud surfaces from the vendored copy (HumeAI paid API, "Cloud"
  sync, CUDA/ROCm GPU updaters). Delete the files AND patch every importer
  that references them (routes/__init__.py, app.py, backends/__init__.py,
  build_binary.py, models.py).
- The upstream MODELS are usually NOT the upstream author's IP (Kokoro is
  hexgrad's; Chatterbox is ResembleAI's). Keep them as runtime downloads;
  never bundle weights. The wrapper code you vendor is what is MIT.

### 2. Vendor and name it cleanly
- Pick ONE meaningful outer folder name; avoid double-naming like
  real-voice-backend/backend/. Prefer a term tied to the subsystem:
  tts, speech, narrator, vocal. Put the Python package directly inside:
  repo/src/speech/ with main.py, app.py, backends/, etc.
- If you FLATTEN a package (drop the inner backend/ subfolder), you MUST
  rewrite internal imports or boot fails with ModuleNotFoundError: backend.
  - uvicorn.run("backend.main:app") becomes "<pkg>.main:app"
  - from backend.server import x becomes from ..server import x (relative)
    or from <pkg>.server import x
  - from backend import config becomes from <pkg> import config
  - DO NOT rename a module that coincidentally shares the old package name.
    services/tts.py (the TTS service module) must stay tts, so
    from ..services import tts is correct and must NOT be touched.

### 3. Gitignore hygiene (prevents the repo-leak class of bug)
- Add the whole vendored folder as local-only: src/speech/.
- ALSO ignore its runtime data as defense-in-depth: src/data/, *.db,
  voicebox.db. The vendored backend typically writes a sqlite DB plus profiles
  relative to cwd (see Pitfall 1).
- Keep a LICENSE plus VENDORED.md (attribution) inside the folder.
- INPUT ASSETS (reference clips / source recordings) also need gitignore:
  input/voices/ (cloned-voice reference .wav) and any personal source media
  must be gitignored so a personal voice is NEVER committed. Document the
  folder's purpose in a README inside it.
- CRITICAL: re-verify ignore state after EVERY .gitignore edit and before any
  commit that touches the vendored folder. A committed .gitignore rule can be
  silently dropped by an external rewrite/save, which suddenly makes the whole
  vendored folder show as untracked and would leak it to GitHub. Verify with
  `git check-ignore -q <vendored-path>` (must say ignored) AND a dry-run
  `git add -n <vendored-path>` (must list only clean source, no *.pyc/*.db/
  weights). See Pitfall 8.

### 3b. STRIP THE UPSTREAM BRAND from the project (commercial-safety + cleanliness)
The user will almost always want the upstream project NAME gone from the
repository — file names, source identifiers, and the committed .env.example.
This is a recurring, explicit demand; treat it as part of the job, not optional.
- RENAME files/folders that carry the brand: e.g. voicebox-lifecycle.ts ->
  speech-backend.ts (use `git mv` so history + renames are tracked; verify with
  `git status --porcelain | grep speech-backend`). Update every importer
  (static import AND dynamic `await import('./x.js')`).
- RENAME internal identifiers/constants: `VOICEBOX_DEFAULT_PORT` ->
  `SPEECH_DEFAULT_PORT`, `VOICEBOX_DEFAULT_URL` -> `SPEECH_DEFAULT_URL`.
- KEEP the upstream brand ONLY where it is an external config contract: the
  env-var READS (`process.env.VOICEBOX_*`). Do NOT rename these — the user's
  `.env` keys must keep working. Read the brand env var but expose a clean
  internal name. This "rename identifiers, keep env reads as aliases" split is
  the safe pattern; renaming env reads breaks `.env` and is usually rejected.
- Scrub the brand from committed docs (.env.example, ENVIRONMENT.md, ADRs,
  FILE_STRUCTURE.md, cli-reference.md) when the user asks for docs too — but if
  the user scopes "source code only", leave docs and stop after the source
  identifiers are clean. Always confirm scope with a clarify() when the blast
  radius is large (docs = safe to edit; renaming env reads = config contract).
- A stale upstream SETUP doc (e.g. docs/VOICEBOX_SETUP.md describing the old
  clone-based flow you replaced with vendored zero-config) is now misleading —
  flag it for deletion/rewrite; do not leave it contradicting the new design.

### 4. Spawn correctly (cwd and data dir)
- Spawn with cwd = the dir that makes the package importable
  (python -m speech.main, cwd = src/).
- Pass a --data-dir pointing at a gitignored cache
  (e.g. workspace/cache/voicebox) so the sqlite DB lands OUTSIDE the repo.
- Default the python interpreter to the real venv (a single hardcoded absolute
  path is fine); never leave a || chain pointing at a deleted path.

### 5. Build a self-driving controller (the integration seam)
A single module owns the backend lifecycle so the rest of the app just calls
one function. Pattern (verified against the AVS Voicebox integration):
- ensureBackend() spawns if not up. Gate on the PROVIDER
  (TTS_PROVIDER === 'voicebox'), NOT on a profile id. A bail-guard that
  refuses to start unless a profile exists will permanently disable the
  backend (Pitfall 3).
- resolveProfileId() auto-provisions runtime resources. Priority: explicit env
  id, cached id, reuse existing (Pitfall 2), then create unique.
- AUTO-CLONE seam (drop a reference clip → use YOUR voice). Add a priority
  BETWEEN explicit-env and cached: scan input/voices/*.wav (first clip
  alphabetically) → if present, POST /profiles {voice_type:'cloned',
  default_engine:'chatterbox_turbo'} then POST /profiles/{id}/samples
  (multipart file + reference_text). Cache the clone profile per source clip
  so re-runs reuse it (no re-clone 422 storm). Falls back to the preset if the
  clip is missing OR cloning throws. NOTE: cloning needs the chatterbox_turbo
  model (~1.5GB, more VRAM than kokoro) — on a 6GB box the preset path is the
  practical default; cloning is an optional heavier feature.
- loadEngine(engine) preloads the model ONCE at stage start (no per-scene cold
  stall). Default the engine to the lightest (kokoro, NOT chatterbox_turbo).
- Generate per item, then teardown: unloadAll() then killBackend() so RAM
  returns to zero until next run (critical on small-RAM machines).
- Wrap the whole stage in try/catch and fall back to the existing engine
  (Edge-TTS, tones) on any failure. Never hang, never crash.

### 6. Zero-config
- Remove the env-based setup from BOTH .env (gitignored, local-only) AND
  .env.example (TRACKED/committed — so this is a real committed-file change;
  keep only a comment listing the vars as OPTIONAL overrides). Hardcode safe
  defaults in code.
- With no env vars set, the system must still boot the backend, auto-provision
  its profile, and generate real output. Verify by running the integration
  test with ALL VOICEBOX_*/TTS_PROVIDER env vars deleted (simulates a fresh
  clone) — it must still produce real output and reuse the same profile on a
  second run (idempotent, no "already exists" 400).

### 7. Verify LIVE (not just typecheck)
- git check-ignore -v <vendored-path> confirms ignored.
- npm run typecheck exit 0 (covers the TS changes).
- Boot-test the backend via subprocess plus poll /health (see
  scripts/boot_voice_backend.py). Assert: /health returns 200, DB in the cache
  dir, NOT in src/data/.
- Integration test against the LIVE backend: generate a real asset (e.g. a
  WAV), assert bytes greater than 1 KB, assert idempotency (run twice, same
  profile reused, no 400). See references/avs-voice-backend.md.
- ALSO run the integration test with the voice env vars UNSET to prove
  zero-config (Step 6).

## Pitfalls (learned the hard way this session)
1. cwd-relative data dir leak. Backend writes data/voicebox.db relative to cwd.
   If spawned with cwd=src, the DB appears at src/data/voicebox.db and shows
   as Untracked in git. FIX: pass --data-dir <gitignored-cache> AND gitignore
   src/data/, *.db.
2. Auto-provision fixed-name resource causes 400 on repeat runs. Creating a
   profile named agentic-kokoro-af_heart every run hits "already exists" the
   second time (the backend persists profiles in its DB). FIX: GET /profiles,
   reuse one matching preset_engine plus preset_voice_id; else create with a
   unique name (add Date.now()).
3. Spawn bail-guard on missing profile. ensureBackend() that returns false
   unless VOICEBOX_PROFILE_ID is set means the backend never starts and
   silently falls back. FIX: gate startup on the provider, provision the
   profile later.
4. Flattened package import rewrites. See step 2. Miss one backend. reference
   and boot dies with ModuleNotFoundError.
5. TS "TS6053 file not found" lint false-positive on a freshly written .ts
   file. Ignore it; validate with npm run typecheck (the real check).
6. PRELOAD endpoint shape & engine support. The backend's
   POST /models/load takes model_size as a QUERY param (not a JSON body) —
   sending {model_size} as a body silently 500s. But more importantly, that
   route drives the DEFAULT Qwen/Chatterbox loader and CANNOT load "kokoro"
   (it 500s with "Failed to load model"). Kokoro instead loads LAZILY inside
   POST /speak, so a kokoro preload via /models/load is pointless AND errors.
   FIX: (a) call /models/load?model_size=<x> (query param) for preloadable
   engines (chatterbox/qwen), and (b) SKIP the preload entirely for kokoro —
   it loads on first /speak. Treat a 500 from loadEngine as non-fatal (catch
   + return false), but for kokoro don't even call it. Captured after a real
   run first showed "engine load failed (kokoro): 500" then still produced
   audio via lazy load — the warning was misleading and the preload was dead.
 8. .gitignore RULE SILENT-DROP (leaks the vendored folder to GitHub). A rule
  you committed (e.g. src/speech/) can be wiped by an external rewrite/save of
  .gitignore, after which `git status` shows the whole folder as Untracked and
  a later `git add` would commit it — including any *.pyc/*.db/weights if
  present. This is silent (no error). FIX/workflow: after ANY .gitignore edit,
  run `git check-ignore -q src/speech/LICENSE` (must report ignored) AND
  `git add -n src/speech/` (dry-run; must list only clean source). Add a
  scoped inner .gitignore inside the vendored folder (exclude __pycache__/,
  *.pyc, *.db, venv/, *.pt/*.onnx/*.safetensors/models/) so even if the outer
  rule is dropped, runtime junk never commits. Caught in-session when a final
  `git status` check revealed src/speech/ no longer ignored — fixed by
  restoring the rule + inner .gitignore before push.
 9. COLD-START FLAKE under RAM pressure. ensureBackend() with a hardcoded ~40s
  startup deadline flakes inside the full `npm test` suite (other heavy tests
  ran first, starving RAM; PyTorch/CUDA backend boot exceeds 40s) → the voice
  integration test fails with "speech backend unavailable". FIX: make the
  deadline configurable (VOICEBOX_STARTUP_TIMEOUT_MS, default 120_000) and make
  isBackendUp() also accept /health (lighter than /models/status). Re-run of the
  full suite then shows the voice test passing.
 10. ORPHANED BACKEND hijacks ensureBackend(). If a test times out mid-generation,
   the spawned backend process keeps running and holds port 17493. The next
   run's ensureBackend() sees the port OPEN and reuses the BROKEN/half-loaded
   backend instead of spawning fresh → cascade of hangs/failures. FIX: between
   test runs, find the listener PID (`psutil.net_connections` on Windows, or
   `lsof -i :17493` on *nix) and `taskkill -F -PID <id>` (MSYS needs single
   slash; double-slash //F fails). Then confirm the port is closed before
   re-running.
 11. FastAPI Form(...) 422 on EMPTY value. Uploading a sample with
   `form.append('reference_text', '')` via axios FormData arrives as null →
   backend 422 "Field required". FIX: send a non-empty placeholder
   ('voice reference sample'); the transcript only affects clone fidelity, not
   the upload succeeding. (Real best-clone quality still needs transcription —
   a TODO, not blocking.)
 12. CRLF normalization warning on commit is benign. Committing Windows-CRLF
   source to git triggers "CRLF will be replaced by LF" warnings — content is
   identical, ignore. Only act if .gitattributes forces normalization and you
   care about diff churn.
7. patch-tool re-read race after git mv / external edits. After `git mv` of a
   .ts file (or any external write), the `patch` tool may report "file modified
   since you last read it" / repeated identical-match failures on that SAME
   file. It is a stale-content race, not a real mismatch. Workarounds that
   worked: (a) re-read the file fresh with read_file, then patch a SMALL unique
   anchor; (b) for a doc-comment block that keeps failing, anchor on the first
   stable unique line (e.g. `import { spawn, ChildProcess }`) and prepend the
   new header before it; (c) avoid re-patching the same region in a loop —
   after 2 failures, switch strategy. The TS6053 "file not found" lint
   false-positive (Pitfall 5) is unrelated and also safe to ignore.
13. NEVER DESTROY A CANONICAL FILE TO "REMOVE" UNUSED DEPENDENCIES.
   When the user says "instead of deleting thing add a proper command for not
   used requirements" they are correcting a recurring instinct: do NOT overwrite
   or truncate requirements.txt (or any canonical install contract) to strip out
   deps you think are unused. KEEP the full base file intact; MOVE the
   unused / fragile deps into a SEPARATE opt-in file (e.g.
   requirements-clone.txt) and document the exact install command for it INSIDE
   that file. Reason: the base file is the source of truth future sessions
   (and `pip install -r` runs) rely on; deleting parts silently breaks a
   fresh install weeks later when the removed dep turns out to be imported.
   Verified-good split for a vendored Python TTS backend:
     - requirements.txt = FULL base (fastapi, sqlalchemy, torch, transformers,
       accelerate, huggingface_hub, qwen-tts, the DEFAULT zero-config
       engine e.g. kokoro, AND the clone-engine BASE deps like
       conformer/diffusers/omegaconf). No git-only / --find-links lines here.
     - requirements-clone.txt = the fragile bits ONLY (git+https sources,
       --find-links custom index, the engine packages themselves), with a
       header comment showing the two-line install:
         uv pip install --python venv/Scripts/python.exe -r src/speech/requirements.txt
         uv pip install --python venv/Scripts/python.exe -r src/speech/requirements-clone.txt
   Always confirm with grep that the server actually imports every dep you
   are tempted to move (e.g. grep -rn "import transformers" src/speech)
   BEFORE separating it.
14. FRESH REPRODUCIBLE INSTALL BEATS COPYING A FRAGILE EXTERNAL VENV.
   When making a vendored backend self-contained INSIDE the repo, do NOT
   `cp -r` the external working venv into the project, and do NOT
   `pip freeze > requirements.txt` from that external venv and install from the
   freeze. The external venv was built by an ad-hoc setup script with
   `--no-deps` hacks, git-only deps (linacodec, Zipvoice), and a
   `--find-links` custom index — copying/freezing drags all that cruft in
   and makes the project unreproducible on a fresh clone (git URLs 404,
   custom index vanishes, version pins fight Python 3.12+). The user's
   standing rule: "we can download it from here again because copying
   unwanted things means that will not work in future — I am correct to avoid
   future problem." CORRECT pattern:
     - Create the in-repo venv fresh: `python -m venv venv` (match the
       external's Python minor, e.g. 3.11, or the freeze import fails).
     - Install from the PROJECT's own declared requirements.txt (Pitfall 13
       split), NOT from a freeze of the external.
     - Point the controller's default interpreter at the in-repo venv
       (e.g. pythonExe() default = path.resolve(cwd,'venv','Scripts','python.exe')),
       gitignore `venv/`, and keep `VOICEBOX_PYTHON` (or equivalent) as
       an env override for machines that already have a working venv.
     - Verify the inside-only path LIVE before deleting the external folder:
       start the backend via the in-repo venv (python -m speech.main, cwd=src),
       hit /health, then /speak (the default engine) and assert real bytes.
       ONLY AFTER that passes, delete the outside folder.
   Pitfall: a `uv pip install -r requirements.txt` that "finishes" (exit 0)
   can still stop mid-resolve and miss a dep (e.g. kokoro never lands).
   Confirm with `venv/Scripts/python.exe -m pip list | grep -i kokoro`
   and a live /speak — NOT just the exit code.
15. DELETE-THEN-VERIFY is the ONLY proof the external dep is gone.
   After the in-repo venv boots + /speak returns real bytes (Pitfall 14),
   the migration is NOT proven until you (a) delete the external folder
   (e.g. `rm -rf C:/one/voicebox`), then (b) re-run the integration
   test against the LIVE inside-only backend. The test must still PASS with the
   external folder ABSENT. If it passes, the system is self-contained. If it
   flakes/400s, the controller still has a hardcoded external path or the
   in-repo venv is missing a dep the external one had. This gate caught a
   real case: the test passed with both venvs present (it was silently
   using the external one) and only FAILED once the external was removed,
   revealing a `pythonExe()` default still pointing outside.
   Gotcha: a background `node --test` run can swallow stdout so the
   summary shows only "exit 1" with no test output — run it FOREGROUND
   and grep the node:test summary (`# pass N / # fail 0`) to see the real
   result. Use scripts/verify_inside_only.py to automate the gate.
## References
## References
- references/avs-voice-backend.md gives AVS-specific detail: the Voicebox
  profile API schema, the exact db-leak fix recipe, and the zero-config
  verification transcript.
- references/brand-strip-matrix.md is the decision matrix for removing the
  upstream project NAME from files/identifiers/.env.example (rename internals,
  keep env-var reads as aliases, scope control, stale-doc trap).
- scripts/boot_voice_backend.py is a re-runnable boot/health/leak probe
  (--venv now DEFAULTS to <skill>/../venv — the in-repo venv; pass
  --venv only to test an external interpreter).
- scripts/verify_inside_only.py automates Pitfall 15: boots from the
  in-repo venv, /speak with the default engine, then asserts the
  external folder is GONE (deletes it if --external is passed) and the
  integration still produces real output. Exit 0 = self-contained.
