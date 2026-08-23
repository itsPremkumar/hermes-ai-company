# dockerize-node-app — error → cause → fix reference

## Build/connect errors
| Symptom | Root cause | Fix |
|---|---|---|
| `error during connect: ... open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.` | Docker daemon not running (Docker Desktop closed) | Launch `"C:/Program Files/Docker/Docker/Docker Desktop.exe"` (bg), poll `docker info` until `Server Version` shows (~20-40s), then build |
| `short read: expected N bytes but got M: unexpected EOF` / `failed to compute cache key` | Partial base-image pull (network drop), NOT a Dockerfile bug | Re-run `docker compose build`; Docker resumes from cache + re-pulls the corrupt layer |
| `sh: tsx: not found` / `Cannot find module 'tsx'` at container start | `npm ci --only=production` dropped devDeps; app runs via tsx | Use full `npm ci`; install dev deps too |
| container permanently "unhealthy" but app works | healthcheck path mismatch (e.g. `/health` vs real `/api/health`) | Make Dockerfile + compose healthcheck hit the SAME real route |
| runtime `invalid ELF` / `cannot execute binary` | native binary (ffmpeg-static/sharp/sqlite3) fetched for wrong arch | pin `platform: linux/amd64` in compose; match `docker info` arch |
| `JavaScript heap out of memory` in container | default Node old-space too small for the box | `ENV NODE_OPTIONS=--max-old-space-size=2048` |

## Common mistakes
- `--only=production` with a tsx/ts-node start script → boot failure.
- Ignoring `.dockerignore` → copying `.env`, `node_modules`, `.git` into image
  (bloat + secret leak). Keep `node_modules/`, `.env`, `.git/`, `.venv/` ignored.
- **Wildcard scoping in `.dockerignore`:** `*.png` matches at **any** directory
  depth, silently excluding needed app assets like `assets/logo.png`. Use
  `/*.png` (root-anchored) to only exclude root-level generated media while
  keeping subdirectory assets intact. Same for `*.mp4`, `*.ico`, `*.jpg`.
- **Retry loop silently succeeds on exhaustion:** `for i in 1 2 3; do cmd && break
  || echo fail; done` always exits 0 because `echo` is the last command. The
  build reports PASSED even though `npm ci` never completed. Always add
  `|| { echo "ERROR: failed after 3 retries"; exit 1; }` after the loop.
- `start_period` too short for tsx/TS startup → healthcheck marks unhealthy during
  normal boot. Use ≥ 20s.
- Using `node:latest` → surprises when engines require a floor (e.g. `>=18`). Pin
  `node:20-bookworm`.

## How to verify the fix worked
1. `docker info` → Server Version present.
2. `docker compose build` → exit 0, no `ERROR:` lines.
3. `docker compose up -d` → `curl -f http://localhost:3001/api/health` returns 200.
4. `docker compose down`.
