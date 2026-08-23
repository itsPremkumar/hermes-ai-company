---
name: vendor-local-backend
description: Vendor a MIT/Apache OSS backend (e.g. a Python TTS/ML server) into a TypeScript/agentic project as a self-driving, ZERO-CONFIG, license-clean, RAM-aware stage — verified by a live integration test. Use when integrating a local backend (voice, vision, LLM) into an existing pipeline without paid keys, cloud deps, or brand leakage.
---

# Vendor a Local Backend into an Agentic Pipeline

Pattern proven on the Automated-Video-Generator (AVS) project: vendored the MIT
"Voicebox" TTS backend at `src/speech/` (renamed from `src/adapters/real-voice-backend/`
→ `src/tts/` → `src/speech/`) and wired it as a self-driving agentic voice stage.

## When to use
- User wants a local/OSS backend integrated (TTS, STT, vision, LLM) with NO paid API.
- Backend is a Python package; host project is TypeScript (Node/tsx).
- Requirements: zero-config (no manual profile/env), production-grade, license-clean, RAM-aware.

## The 8-phase method (all verified live, not theorized)

### 1. Strip paid/cloud/brand/trademark from the clone
Before copying, DELETE from the source:
- Cloud sync (`routes/cloud.py`, `services/cloud.py`), paid backends (HumeAI `hume_backend.py`, TADA),
  ROCm/CUDA **auto-updaters** (device *detection* is fine — only remove auto-download/self-update logic),
  unused shims (`dac_shim.py`), upstream test suites, `__pycache__`.
- Keep the `LICENSE` + copyright notice intact (MIT/Apache required for compliance).
- Verify strip: `grep -rniE "hume|tada|cuda|rocm|\.cloud|telemetry|phone.?home|jamiepine" src/<pkg> --include=*.py`
  — expect ONLY legit ROCm/CUDA device-detection lines, nothing paid/cloud.

### 2. Flatten the package
- Copy backend so `src/<pkg>/` IS the importable Python package (no `backend/` subfolder).
- Run via `python -m <pkg>.main` with `cwd = src/` (so `import <pkg>` resolves).
- Fix hardcoded `backend.` imports → `<pkg>.` in `main.py`, `server.py`, `routes/*`.

### 3. Redirect runtime data OUT of the repo (leak fix)
Source resolves data dir relative to `cwd`. If cwd=`src/`, it writes `src/data/<pkg>.db` (untracked leak).
FIX in the TS spawner: pass `--data-dir <workspace>/cache/<pkg>` and add `src/data/` + `*.db` to `.gitignore`.
Verify: after boot, `src/data` must NOT exist; DB lands in the cache dir.

### 3b. CRITICAL — guard the `.gitignore` rule itself (a silent leak vector)
The vendored folder stays local via a `.gitignore` rule (e.g. `src/<pkg>/`). That rule is a
SINGLE line and can be **silently lost** — a later `git mv` / `git checkout` / editor overwrite can
drop it without error, after which `git status` shows `?? src/<pkg>/` and a naive `git add .`
would COMMIT THE ENTIRE VENDORED BACKEND (and any sqlite db) to GitHub. This happened once
in practice and was only caught by a final pre-push review.
MITIGATIONS (do all):
- After ANY `.gitignore` edit, re-assert: `git check-ignore -v src/<pkg>/LICENSE` must print the
  matching ignore rule (not "not ignored").
- Before committing, dry-run: `git add -n src/<pkg>/` → must report "ignored by one of your
  .gitignore files" with nothing staged.
- Confirm remote never received it: `git ls-files origin/main -- 'src/<pkg>/'` must be EMPTY.
- If the rule is missing, RESTORE it before any commit/push; never `git add -f` the folder.

### 4. Rename brand → functional (user explicitly wants this)
- File `voicebox-lifecycle.ts` → `speech-backend.ts`.
- Internal constants `VOICEBOX_DEFAULT_*` → `SPEECH_DEFAULT_*`.
- Log tag `[VOICEBOX-LIFECYCLE]` → `[SPEECH-BACKEND]`.
- **KEEP `process.env.VOICEBOX_*` READS as aliases** so the user's `.env` still works (config contract).
  Only rename internal identifiers, not the external env-var keys.
- Update all importers (static + dynamic `await import(...)`) and the doc-comment header.

### 5. Build a self-driving controller (the "no asking" core)
New `src/<area>/media/<pkg>-controller.ts` owns the full lifecycle:
`ensureBackend → resolveProfile → loadEngine → generate per scene → unloadAll → killBackend`.
- **Auto-provision profiles IDENTOTENTLY**: `GET /profiles`, reuse one matching
  `preset_engine`+`preset_voice_id`; else `POST /profiles` with a **unique name**
  (`agentic-<engine>-<voice>-<Date.now()>`) to avoid "already exists" 400 on repeat runs.
  Cache the resolved id in `<workspace>/cache/<pkg>/profile.json`.
- **Engine preload gotcha** (caught live): the backend's `/models/load` may 500 for some
  engines (e.g. kokoro) because that endpoint drives a *different* default loader.
  Kokoro loads lazily inside `/speak`. FIX: skip `loadEngine` for engines that don't
  support `/models/load`; let them lazy-load. Also: `/models/load` takes a **query param**
  (`params: { model_size }`), NOT a JSON body — a JSON body silently defaults and 500s.
- **RAM-aware teardown**: `unloadAll()` then `killBackend()` at stage end (zero footprint
  until next run). Critical on low-RAM machines.

### 6. Wire into the orchestrator as a FIRST-CLASS stage (mirror an existing stage)
- Replace the old call with `try { runStage(...) } catch { fallback() }` so failure never
  blocks the pipeline (fallback to Edge-TTS / tone). Emit live `percent` progress.
- Add `audioDir` (or equivalent) to the workspace type; all downstream stages consume it.

### 7. License compliance (tracked, even if code is gitignored)
- Keep `src/<pkg>/LICENSE` (MIT) + a `VENDORED.md` (source URL, commit, what was stripped).
- Add a **tracked** `THIRD_PARTY_LICENSES.md` at repo root reproducing the full MIT text +
  provenance — because the vendored folder is git-ignored (user chose gitignore over commit),
  this doc is the compliance record that ships to GitHub.
- Confirm: `git ls-files src/<pkg>/` is EMPTY (not pushed); only the license doc is.

### 8. Verify with a LIVE integration test (not just typecheck)
- `node --import tsx --test` test that spawns the real backend, generates real output, asserts
  file size > 1KB, asserts no `src/data` leak, then `killBackend()`.
- Run it **twice** to prove idempotency (profile reuse, no 400).
- Also run **zero-config**: delete all `<PKG>_*`/`TTS_PROVIDER` env and confirm it still works
  via built-in defaults.
- Full `npm test` may show pre-existing network/provider fails in a sandbox — confirm those are
  UNRELATED to your changes (grep the failing tests; they're offline-image/visual tests, not yours).

## Hard rules from this user
- NEVER delete/modify old code — build standalone + backward-compat shim; commit before approval, push only after explicit "go".
- EVERY claim needs evidence in the SAME turn: typecheck exit code, test pass/fail counts, real file sizes, git status.
- RAM discipline: keep backend resident only during its stage; kill after.
- Zero-cost mandate: no paid keys, no cloud deps in the vendored copy.

## Verification gates (all must be green before declaring done)
- `npm run typecheck` exit 0
- Integration test `pass N, fail 0` with REAL output bytes
- `git status` clean: no `src/data`, no `*.db`, vendored folder git-ignored, no secrets
- **`.gitignore` rule holds** (run BEFORE commit/push — see Phase 3b):
  `git check-ignore -v src/<pkg>/LICENSE` prints the rule; `git add -n src/<pkg>/` stages nothing;
  `git ls-files origin/main -- 'src/<pkg>/'` is empty.
- Zero-config run works with no env vars
- License doc on remote, vendored code not on remote

## Pre-push safety checklist (run this exact sequence)
1. `git status --porcelain | grep -v node_modules` — only intended files.
2. `git check-ignore -v src/<pkg>/LICENSE` — MUST match a rule (not "not ignored").
3. `git add -n src/<pkg>/` — MUST say ignored, nothing staged.
4. `git commit` then `git push`; then `git ls-files origin/main -- 'src/<pkg>/'` — MUST be empty.
If step 2 or 3 fails: restore the `.gitignore` rule FIRST, never force-add the folder.
