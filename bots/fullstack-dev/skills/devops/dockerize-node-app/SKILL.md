---
name: dockerize-node-app
description: Containerize a Node/TypeScript app (esp. one run via tsx with no build step) into a correct, version-robust Docker image + compose. Use when the user says "dockerize this", "make a Dockerfile", "create docker-compose", "fix the docker error", or wants the project to run in a container without version/system errors. Covers the npm-ci --only=production trap that breaks tsx-run apps, healthcheck path mismatch, platform pinning for native binaries (ffmpeg-static), Docker-daemon-not-running, and a verified-good Dockerfile/compose pair as templates.
---

# dockerize-node-app

Containerize a Node/TS app so it actually runs in Docker — no version drift, no
"invalid ELF / module not found / container unhealthy" surprises.

## Decision: does the app need a build step?
- If `package.json` has `"build": "tsc ..."` (real emit) → build in image, run `node dist`.
- If the app runs via `tsx` / `ts-node` at runtime (common for agents/CLIs) →
  **`tsx` is a devDependency** and you MUST install ALL deps, not `--only=production`.

## THE #1 trap: `npm ci --only=production` breaks tsx-run apps
Many Node Dockerfiles do `RUN npm ci --only=production` to slim the image. If the
app's start script is `tsx watch src/server.ts` (or any tsx/ts-node invocation),
`--only=production` DROPS `tsx` + `typescript` → the container dies at boot with
`sh: tsx: not found` or `Error: Cannot find module 'tsx'`.
FIX: `RUN npm ci` (full install). If you must slim, install dev deps separately
and prune AFTER copying source + a real build, not before runtime.

## Healthcheck path must match the real route
- The Dockerfile `HEALTHCHECK` and the compose `healthcheck.test` MUST hit the
  SAME path the app actually serves. A classic mismatch: Dockerfile uses
  `/api/health` (correct) but compose uses `/health` (404) → container is
  permanently "unhealthy" even though the app is fine.
- Verify the route exists (grep the server source) before picking the path.

## Pin the platform for native binaries
Apps using `ffmpeg-static`, `@node-ffmpeg/...`, `sharp`, `sqlite3`, `bcrypt`, etc.
fetch a PLATFORM-SPECIFIC native binary at install time. On Apple Silicon / ARM
hosts, an unpinned build pulls the wrong arch → runtime `invalid ELF` / segfault.
FIX: set `platform: linux/amd64` in compose (and `FROM --platform=linux/amd64`
if you build on ARM). Match the daemon arch (`docker info` → Architecture).

## Don't double-install ffmpeg
If the code uses `ffmpeg-static` (bundled binary via `require('ffmpeg-static')`),
you do NOT need `apt-get install ffmpeg`. Installing both invites PATH confusion
and version drift. Keep apt ffmpeg only if the code shells out to a system `ffmpeg`.

## Docker daemon must be running (easy to forget)
`docker compose build` fails with a MISLEADING error when the daemon is down:
`error during connect: ... open //./pipe/dockerDesktopLinuxEngine: The system
cannot find the file specified.`
This is NOT a config bug — Docker Desktop just isn't started.
FIX (Windows): launch `"C:/Program Files/Docker/Docker/Docker Desktop.exe"` as a
background process, then poll `docker info` until `Server Version` appears (≈20-40s).
Then build.

## Network/pull errors are usually transient — retry
A build that dies with `short read: expected N bytes but got M: unexpected EOF`\nor `failed to compute cache key` is a PARTIAL IMAGE PULL (dropped connection),\nNOT a Dockerfile defect. Re-run `docker compose build`; Docker resumes from cache\nand re-pulls the corrupt layer. The Dockerfile parsed fine if it got past `FROM`.

## Dependency audit for Docker image size optimization

Before Dockerizing (or alongside it), audit which dependencies are
**desktop-only / build-only** and reclassify them from `dependencies` →
`devDependencies`. This doesn't shrink the current image if all-deps install is
needed for `tsx`, but it enables future **multi-stage builds** that skip devDeps
in the final stage, saving 800+ MB.

### Audit workflow

```bash
# 1. List current categories
node -e "const p = require('./package.json'); console.log('deps:', Object.keys(p.dependencies).join(', ')); console.log('---dev:', Object.keys(p.devDependencies).join(', '));"
```

**Candidates to move → `devDependencies`:**
- `ffprobe-static` (≈336 MB) — bundled binary; most imports have `try/catch`
  fallback to system `ffprobe`. Verify fallback coverage in src/.
- Desktop frameworks (`electron`, `electron-builder`) — verify they're *already*
  in devDeps.
- Any package imported only in test files, build scripts, or Electron-specific dirs.

**MUST stay in `dependencies`:**
- `ffmpeg-static` — server-side rendering, no fallback
- Runtime libs: `express`, `react`/`react-dom` (Remotion), `@remotion/*`
- `tsx` — runtime if no build step exists

### Measure the size impact

```bash
# Per-package
du -sh node_modules/ffprobe-static node_modules/electron 2>/dev/null

# Total desktop stack
du -sch node_modules/ffprobe-static node_modules/electron node_modules/app-builder-bin \
  node_modules/electron-winstaller node_modules/electron-builder \
  node_modules/dmg-builder node_modules/electron-publish \
  node_modules/builder-util node_modules/builder-util-runtime \
  node_modules/electron-builder-squirrel-windows node_modules/app-builder-lib \
  2>/dev/null | tail -1
```

Typical: **900 MB – 1 GB** (electron 348M + ffprobe-static 336M +
app-builder-bin 207M + electron-winstaller 31M + rest ~7M).

### Multi-stage build plan (after reclassification)

```
Stage 1 (builder):  npm ci (all deps) → typecheck → tsc → dist/
Stage 2 (runner):   npm ci --only=production  ← skips all desktop devDeps
                    + apt install ffmpeg (replaces ffprobe-static)
```

**Caveat:** Stage 2 needs a compiled dist/ — if the app runs via `tsx` without a
build step, keep the single-stage all-deps install and document the multi-stage
path as the future optimization.

### Pitfall: verify src/ usage, don't guess by name

```bash
grep -rn "require('<pkg>')\|from '<pkg>'\|import.*from '<pkg>'" src/ --include='*.ts'
```

- If found in `src/`: check whether the import has a `try/catch`. A **hard static
  import** (`import x from 'y'` at top level) crashes at startup if the package
  is missing under `--production`.
- Convert hard imports to `await import()` with fallback if the dep is truly optional.
- Test/build scripts using the dep are fine — they only run in dev/CI.

See `references/dependency-audit-docker.md` for a full real-audit transcript
showing per-file fallback analysis and the exact multi-stage savings calculation.

## Python deps in a Node image (PEP 668 + missing venv) — REAL version/system errors
If the Dockerfile installs a pure-Python tool (e.g. `edge-tts` for TTS) on a
Debian **Bookworm** base, two errors bite that don't happen on Bullseye:
1. `pip3 install edge-tts` -> `error: externally-managed-environment` (PEP 668).
   Bookworm's Python refuses pip installs outside a venv.
   FIX: create a venv and install there, then add it to PATH:
   `RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir edge-tts`
   `ENV PATH="/opt/venv/bin:${PATH}"`
2. `python3 -m venv /opt/venv` -> `ensurepip is not available` because the
   `node:20-bookworm` image ships Python WITHOUT `python3-venv`.
   FIX: add `python3-venv` (and `python3-pip`) to the `apt-get install` line.
Miss either and the build fails at the Python layer. (This is exactly why a
Bullseye->Bookworm base bump silently breaks a working Dockerfile.)

## npm ci itself can fail on a flaky network — add retry resilience
Even after the pull succeeds, `RUN npm ci` can die with
`npm error code ECONNRESET` / `network aborted` on a throttled/unstable link
(the whole install can take 4-6 min, plenty of time to reset). A single failure
aborts the build.
FIX: set npm retry config and wrap the install in a bounded shell loop so one
reset doesn't kill the layer:

**⚠️ CRITICAL: the retry loop must fail the build when all attempts are exhausted.**
A naive loop `for i in 1 2 3; do cmd && break || echo fail; done` always exits 0
because `echo` is the last command that runs — Docker happily reports a **passed
build** even though `npm ci` never completed. The `|| exit 1` guard is essential.
```
COPY package.json package-lock.json* ./
RUN npm config set fetch-retries 5 \
    && npm config set fetch-retry-mintimeout 20000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && npm config set fetch-timeout 300000 \
    && for i in 1 2 3; do \
         npm ci --prefer-offline --no-audit --no-fund && break \
         || echo "npm ci attempt $i failed (network), retrying..."; \
       done || { echo "ERROR: npm ci failed after 3 retries"; exit 1; }
```
For very flaky CI runners, bump `fetch-retry-mintimeout` to `60000` so npm waits
a full minute before each retry. The 20000 value is fine for most local builds.
(Also consider pre-warming the host npm cache and building with
`--prefer-offline` so retries resume from partial downloads.)

## Docker MCP via config.yaml is agent-BLOCKED — use the CLI
To give Hermes native `docker_*` tools you add an `mcp_servers` block to
`~/.hermes/config.yaml` and restart. BUT that file is agent-protected — the
agent CANNOT write it (gets "Refusing to write to Hermes config file"). The
USER must paste the block + restart Hermes. Until then, drive Docker via the
`docker` CLI in the terminal (fully works once Docker Desktop is running).
The `docker mcp server` subcommand exists if Docker Desktop >= 4.40, but it is
the MCP *manager*, not necessarily the stdio server entrypoint Hermes expects —
verify the exact entrypoint before relying on it.

## Security/stability hygiene
- Run as non-root (`useradd -m -u 1001 appuser && chown -R appuser:appuser /app`).
- Set `NODE_OPTIONS=--max-old-space-size=2048` to avoid OOM kills on small boxes.
- `start_period` ≥ 20s for tsx/TS startup (healthcheck shouldn't fail during boot).
- Pin a single Node base (`node:20-bookworm`, not `:latest`) so `engines` stays satisfied.

## .dockerignore must be tight — wildcards bite differently in Docker
A `.dockerignore` controls what the Docker daemon receives as build context.
A bloated context (node_modules, `.git`, agent workspaces, dev modules) slogs
through the Docker upload and can time out on large projects.

### Critical wildcard scoping pitfall (global vs root-anchored)
Docker's `.dockerignore` wildcards (`*.png`) match at **any directory depth**,
not just the project root. This means `*.png` would silently exclude
`assets/logo.png` or `public/favicon.ico` from the image even though those are
needed app assets.

**FIX: anchor media wildcards to root** with a leading `/`:
- `/*.png` — only matches `logo.png` at the project root (generated artifacts)
- `*.png` — matches `logo.png` AND `assets/logo.png` AND `public/favicon.ico`
  (BROKEN — excludes needed assets)

Same for all media extensions: `/*.mp4`, `/*.jpg`, `/*.ico`, etc.

### What to exclude (beyond the obvious)
Beyond `node_modules/`, `.env`, `.git/`, and `output/`, look for these category
bloaters in a Node/TS project:
- **AI agent dirs:** `.claude/`, `.codex/`, `.cursor/`, `.agent/` — working state
- **Dev modules:** separate experiment repos checked in as folders
- **Agentic pipeline workspaces:** can contain hundreds of MB of generated videos
- **Portable runtimes:** `portable-python/`, `.venv/`
- **Build artifacts:** `dist/`, `dist-electron/`, `release/`, `.remotion/`,
  `*.tsbuildinfo`
- **Dev scripts:** `bin/`, `scripts/`, `tools/` — not needed at runtime
- **Python cache:** `__pycache__/`
- **Sample/test data:** `samples/`, `examples/`

Measured impact on one project: the expanded `.dockerignore` excluded
**~45,000 files across 22 directories** from the build context.

## Verification gate (prove it works, don't announce)
1. `docker info` → daemon up.
2. `docker compose build` → exits 0, no error lines.
3. `docker compose up -d` then `curl -f http://localhost:<port>/api/health` → 200.
4. `docker compose down`.
If step 2 fails on a pull EOF → retry (transient). If it fails on a Dockerfile
instruction → that's a real config error to fix.

## Templates in this skill
- `templates/Dockerfile.node20-tsx-app` — verified-good Dockerfile for a tsx-run
  Node/TS app (full npm ci with retry+exit guard, python3-venv for PEP 668,
  venv-based edge-tts install, non-root user, correct healthcheck, no apt ffmpeg).
- `templates/docker-compose.yml` — compose with platform pin + matching
  healthcheck + optional commented Voicebox sidecar.
- `references/pitfalls.md` — expanded error→cause→fix table with real transcripts.
