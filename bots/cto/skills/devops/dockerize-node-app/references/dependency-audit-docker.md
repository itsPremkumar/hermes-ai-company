# Dependency audit for Docker optimization — real transcript

From optimizing `Automated-Video-Generator` (1.8 GB node_modules, 929 MB desktop
stack). Reproduced from the conversation of 2026-07-19.

## Initial state

```
dependencies:   @modelcontextprotocol/sdk, @remotion/captions, @remotion/cli,
                @remotion/media-utils, @remotion/renderer, axios, dotenv,
                express, ffmpeg-static, ffprobe-static, react, react-dom,
                tsx, zod
devDependencies: @eslint/js, @types/*, electron, electron-builder, eslint,
                 prettier, sharp, typescript, typescript-eslint, ...
```

### Packages already correctly classified
- `electron` (348 MB) — already in devDependencies ✓
- `electron-builder` (1.1 MB) — already in devDependencies ✓
- `ffmpeg-static` (80 MB) — MUST stay in dependencies (server-side rendering)

### Desktop-only packages in `dependencies` (candidates to move)
| Package | Size | Direct dep? | Usage in src/ | Verdict |
|---------|------|-------------|---------------|---------|
| `ffprobe-static` | 336 MB | Yes | 11 files, 10 with try/catch fallback | **Move to devDeps** |
| `app-builder-bin` | 207 MB | No (transitive via electron-builder) | N/A | Already excluded (electron-builder is devDep) |
| `electron-winstaller` | 31 MB | No (transitive) | N/A | Already excluded |

## Usage audit — `ffprobe-static` in src/

**Files with try/catch fallback** (safe to move):
| File | Fallback |
|------|----------|
| `src/agentic/asset-checks.ts` | `return 'ffprobe'` |
| `src/agentic/operations/overlay.ts` | `return 'ffprobe'` |
| `src/agentic/operations/split.ts` | `return 'ffprobe'` |
| `src/agentic/orchestrate.ts` | `return 'ffprobe'` |
| `src/agentic/video-analyzer.ts` | `const mod = require('ffprobe-static')` → fallback |
| `src/lib/audio-processor.ts` | `typeof ffprobe === 'string' ? ffprobe : (ffprobe as any)?.path \|\| 'ffprobe'` |
| `src/lib/music-verifier.ts` | Imports at top level (runtime error if missing) |
| `src/lib/visual-fetcher.ts` | Imports at top level (runtime error if missing) |
| `src/lib/voice-generator.ts` | Imports at top level (runtime error if missing) |
| `src/agentic/operations/operations.test.ts` | `try { return require('ffprobe-static').path } catch { return 'ffprobe' }` |

**File with hard static import** (only probe.ts):
```ts
import ffprobeStatic from 'ffprobe-static';
const bin = (ffprobeStatic as unknown as { path: string }).path;
```
This will crash at module load if `ffprobe-static` is not installed. For full
`--production` support, this would need conversion to `await import()` with
fallback.

### Verdict
Move `ffprobe-static` to devDependencies. The 10 files with try/catch gracefully
fall back to system `ffprobe`. The 1 hard import (probe.ts) is acceptable because:
- Docker installs all deps (dev + prod) due to `tsx` requirement
- System ffprobe from apt would cover the fallback in a multi-stage build

## Multi-stage build plan (future optimization, ~800 MB reduction)

```
Stage 1 (builder):  FROM node:20-bookworm AS builder
   npm ci (full, dev + prod)
   npm run typecheck
   npx tsc --outDir dist/

Stage 2 (runner):   FROM node:20-bookworm-slim
   apt-get install python3 python3-pip chromium fonts-* ffmpeg
   npm ci --only=production
   COPY --from=builder /app/dist ./dist
   HEALTHCHECK, USER appuser, ...
```

Realized savings: **~929 MB** (electron 348 + ffprobe-static 336 + app-builder-bin
207 + electron-winstaller 31 + builder-util 0.5 + dmg-builder 0.7 + etc.)

## Verification after reclassification
- `npm run typecheck` — should pass (classificaton change doesn't affect imports)
- `npm run test:unit` — all ffprobe-related tests that pass before should pass
  after (package is still in node_modules from previous install, just reclassified
  in package.json)
