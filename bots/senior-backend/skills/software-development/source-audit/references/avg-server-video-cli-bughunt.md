# AVG server / views / CLI / video-generator bug-hunt (read-only)

A second worked example for `source-audit`, from a read-only defect hunt of the
**server/views/config/CLI/video-generator** slice of `Automated-Video-Generator`
(`C:/one/Automated-Video-Generator`). Companion to `avg-adapter-http-mcp-cli-bughunt.md`
(which covers the adapter/HTTP/MCP layer); this file covers the REST bootstrap,
views, services, `pipeline-workspace`, `video-generator`, `scene-editor`, `env.service`,
and `cli-runner`.

Verification approach this session: read every target file end-to-end, then
RUNTIME-VERIFY each suspected bug with a small `node -e` path-expansion probe or an
`esbuild`/`od -c` byte check before reporting (per the SKILL.md "Rule out display
artifacts" + "RUNTIME-VERIFY" steps). Report-only: no source edited.

## Verified findings

### 1. `assertPathWithinProject` is a string-prefix test → sibling-directory escape + absolute-path bypass
- `src/infrastructure/filesystem/local-filesystem.ts:19-24`.
- `path.resolve(filePath).startsWith(projectRoot)` has **no trailing-separator boundary**. A path whose prefix equals the project root followed by a non-`/` char passes: `C:\one\AVG-secret\f`.startsWith(`C:\one\AVG`) → `true`.
- Worse, `getViewFile` (`local-filesystem.ts:173-175`) accepts an **absolute** `req.query.path` and feeds it straight to `path.resolve` (`path.isAbsolute(rawPath)` branch), bypassing the `..`-stripping that `resolvePublicFilePath` would otherwise enforce for relative inputs.
- Reached by `api-routes.ts:151-156` `/fs/view` (only `viewFileQuerySchema` `max(2048)`, no format/segment restriction) gated solely by `requireLocalAccess`. A loopback client can read a sibling dir's allowlisted-type file.
- **REPRODUCED:** `node -e "console.log('C:/one/AVG-secret/f'.startsWith('C:/one/AVG'))"` → `true`.
- **Fix:** `const rel = path.relative(projectRoot, resolved); if (rel === '' ? false : rel.startsWith('..') || path.isAbsolute(rel)) throw;` and reject absolute paths in `getViewFile` (normalize via the project-rooted resolver).

### 2. Auto free-music path double-prefixes `music/` → feature silently dead + swallowed throw
- `src/video-generator.ts:357-394`, specifically `:363`: `backgroundMusic = \`music/__auto__/${path.basename(freeMusic.localPath)}\`;`
- `freeMusic.localPath` is already `input/music/__auto__/<file>` (set in `free-music.ts:255,267`). Later (`:369-371`) `resolveProjectPath('input','music', backgroundMusic)` → `input/music/music/__auto__/<file>` — the file never exists, so the `if (fs.existsSync(musicInputPath))` block is always skipped. The `catch` then `fs.copyFileSync(musicInputPath, ...)` throws on a non-existent source and is swallowed → **every** generation without user-supplied `backgroundMusic` renders with no music.
- **REPRODUCED:** Node path expansion showed `input/music/music/__auto__/lofi_x.mp3` ≠ real `input/music/__auto__/lofi_x.mp3` (MISMATCH=true).
- **Fix:** derive the value from the resolver's expected base — `basename(freeMusic.localPath)` placed under `input/music/__auto__` (don't prepend `music/__auto__/`).
- Reusable probe for ANY "constructed path doesn't match where the writer saved it" bug: expand both the real store path and the resolved path in Node and compare.

### 3. Unauthenticated server-side fetch endpoints (access-control inconsistency, even when SSRF-guarded)
- `src/adapters/http/api-routes.ts:113-122`: `/video-download/process` (no `validateRequest`), `/social-download/process`, `/free-video/search`, `/free-video/download` are registered with **no `requireLocalAccess`**, unlike `/fs/*`, `/setup/env`, and `/api/agentic` (`app.ts:175`).
- SSRF is hardened (`isSafeUrl` in `net-safety.ts` / `downloader.ts:147`), so no private-IP leak — but any remote client can drive the server to fetch arbitrary public files into the served `/jobs/` tree (`social-download-app.service.ts:58-76` returns `localPath: /jobs/...`) and burn CPU/network.
- **Fix:** add `requireLocalAccess` (or stricter auth + rate-limit) to every route that triggers server-side fetches, matching the rest of the local-only security model.

### 4. `updateSceneInJob` leaves a stale `scene.visual` when the visual refresh fails
- `src/infrastructure/pipeline/scene-editor.ts:104-118`. If `keywordsChanged || assetChanged` but the fetch/download throws, `visual` stays `null` and the `if (visual)` guard (`:115`) is skipped — the OLD `scene.visual` (which may now point at a deleted file) is left in `scene-data.json` with no revert. The text/voice branch (`:46-70`) reliably rewrites; the visual branch has no revert path.
- **Fix:** on the visual branch, clear/revert `scene.visual` when the refresh fails so render never references a missing asset.

### 5. `/health` leaks inventory to anonymous callers
- `src/adapters/http/setup-controller.ts:10-21`. `/health` (`api-routes.ts:45`, no `requireLocalAccess`) always returns `publishedVideos` count and full `jobStore.all().length` (job activity). Detail/dependency fields are correctly gated by `isLocalRequest`/`EXPOSE_HEALTH_DETAILS` — but the counts are not. Minor metadata disclosure of operational activity to the open internet.

### 6. `reorderJobScenes` rejects `toIndex >= length` but validation is split/inconsistent
- `src/infrastructure/pipeline/scene-editor.ts:130` checks `toIndex >= data.scenes.length`; the schema `reorderScenesBodySchema` (`api.schemas.ts:91-96`) only enforces `int >= 0`; `scene-app.service.ts:54-57` passes raw numbers through. Benign (a `fromIndex===toIndex` no-op still rewrites the file) but the validation responsibilities are split and a legal end-insert (`toIndex === length`) is rejected though `splice` permits it.

## Hypotheses checked and cleared (do not re-flag)
- **`read_file` rendered `function buildGeminiUrl(apiKey: *** string {`** (line 33 of `ai.service.ts`) — looks like syntax corruption, but `esbuild` transpile + `od -c` of the raw bytes prove the real source is `function buildGeminiUrl(apiKey: string): string {`. The `***` is a **read tool artifact**, not real bytes. (This is a NEW class of `***` artifact beyond the documented "Authorization → mask of Bearer" — it can appear in ANY line. Verify with esbuild/od before reporting syntax bugs.)
- **`processScene` concurrency (`video-generator.ts:309-321`):** `const p = ...` IS captured in the `.then` closure, so `activePromises.indexOf(p)` works — not a bug.
- **XSS in views:** user-supplied `title`/`voiceoverText`/`searchKeywords`/`assetUrl` all route through `escapeHtml` (`layout.view.ts:12`, `job-status.view.ts:339`, `helpers.ts`); `jobId` is regex-validated before interpolation into a JS literal. Safe.
- **`requireLocalAccess` / `ALLOW_UNSAFE_REMOTE_ADMIN`:** correctly restricts to GET/HEAD when the escape hatch is set (`local-only.ts:18`). Safe by design.
- **`/fs/view` relative `..` traversal:** blocked because `resolvePublicFilePath` (`paths.ts:91-98`) throws on `..` for relative inputs — only the absolute/sibling-prefix case (#1) is exploitable.
- **`free-video/download` SSRF:** guarded — `downloader.ts:147` calls `isSafeUrl(url)` before fetch. Safe (the gap is the *unauthenticated* access, #3, not SSRF).

## Verification techniques used (reusable)
- Path-mismatch probe: `node -e "const path=require('path'); const root='...'; const real=path.join(root,'input','music','__auto__','x.mp3'); const bg='music/__auto__/'+path.basename(real); const resolved=path.join(root,'input','music',bg); console.log('MISMATCH?', resolved!==real);"`.
- Syntax-corruption check: `npx esbuild <file> --format=esm` (compiles iff real syntax is valid) + `sed -n 'Np' <file> | od -c` for exact bytes — use before reporting any `***`/corrupted-line bug.
- Baseline typecheck: `npx tsc -p tsconfig.json --noEmit` (this session clean) to prove no pre-existing compile error masks the defects.
