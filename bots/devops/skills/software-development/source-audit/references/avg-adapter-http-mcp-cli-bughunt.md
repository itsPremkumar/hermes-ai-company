# AVG adapter layer bug-hunt (desktop app + HTTP / MCP / CLI)

Worked example of the adapter-layer finding classes from a read-only bug-hunt of
`Automated-Video-Generator` (`C:/one/Automated-Video-Generator`). Companion to the
pitfalls in `SKILL.md`: a file:line map of verified issues, the confirmation
method, and the one-line fix. Nothing was edited (report-only per the task).

The review covered: `src/adapters/http/*` (controllers + `api-routes.ts`,
`app.ts`, `file-routes.ts`, `view-routes.ts`), `src/infrastructure/filesystem`,
`src/middleware/local-only.ts`, `src/schemas/api.schemas.ts`, `src/lib/path-safety.ts`,
`src/lib/net-safety.ts`, `src/lib/{video-downloader-service,media-downloader,free-video}*`,
`src/adapters/mcp/register-agentic-tools.ts`, `src/adapters/cli/{cli-runner,batch-queue}.ts`,
`src/application/*.{app.service,social-download-app.service}.ts`.

## Verified findings (8 real; 4 hypotheses dropped as non-bugs)

### 1. `pickFile` / `copyFileTo` skip containment on `sourcePath` -> local-file disclosure + write into served dir
- `src/infrastructure/filesystem/local-filesystem.ts:112` (`pickFile`) and `:256` (`copyFileTo`).
- `pickFileBodySchema`/`saveToBodySchema` only `.trim().max(2048)` — no path check. `pickFile` does `existsSync -> statSync -> copyFileSync(src, INPUT_ASSET_ROOT/...)` with **no `assertPathWithinProject(src)`**. A loopback client passes `sourcePath=/etc/passwd` (or `C:\Windows\...`); the file lands in `input/` and is served via `/assets/input/...`.
- **Fix:** call `assertPathWithinProject(sourcePath)` before `existsSync` in both. This is the already-documented "Copy-into-served-dir ... arbitrary file disclosure" pitfall; this session confirmed the second concrete instance (the `/fs/pick` and `/fs/save-to` routes both reach it — note `saveTo` does check `targetDirectory` but NOT `sourcePath`).

### 2. `/api/agentic/jobs/:id/scenes` guaranteed 500 on common jobs
- `src/adapters/http/agentic-controller.ts:76`. `fs.readFileSync(sd)` (no `try/catch`) throws `ENOENT` when a job has no `scene-data.json` (the usual case). `asyncHandler` forwards -> 500.
- **Fix:** `let raw='{}'; try { raw=fs.readFileSync(sd,'utf8'); } catch {} return res.json(JSON.parse(raw));` (the success path already defaults to `{scenes:[]}`).

### 3. Social-download copies a remote-derived filename into `public/jobs` with no sanitization (race + overwrite)
- `src/application/social-download-app.service.ts:53-68`. `filename = path.basename(absolutePath)` where `absolutePath` is influenced by the remote URL/title; copied to `public/jobs/social_<Date.now()>/<filename>` with no `sanitizeFilename` / `ensureAllowedExtension` / `buildUniqueFilePath`. `public/jobs` is `express.static`-served (`app.ts:158`), so a crafted name discloses/overwrites. Two downloads in the same ms also collide (`social_<ts>` not unique enough).
- **Fix:** sanitize `filename` + `ensureAllowedExtension` + `buildUniqueFilePath`; or reuse the existing safe copy path from `local-filesystem.pickFile`.

### 4. SSRF via redirect-following bypasses `isSafeUrl`
- `src/lib/free-video/http-client.ts` `createHttpClient` has **no `maxRedirects:0`**; `isSafeUrl` (`src/lib/net-safety.ts:55`) validates only the INITIAL URL. A public URL `302 -> http://169.254.169.254/latest/meta-data/` (or `http://127.0.0.1:6379/`) is followed with no re-validation.
- Same hole in `src/lib/media-downloader.ts:221` (`fetch()` default follows redirects).
- **Fix:** `axios.create({ maxRedirects: 0 })` + re-run `isSafeUrl` on each redirect `Location`; for `fetch`, `{ redirect: 'error' }` and re-validate. Pairs with the existing "SSRF guard only on the curated path" + "IPv4-mapped IPv6" pitfalls — this adds the *redirect* dimension.

### 5. MCP `recordDecision` corrupts scene/candidate indices
- `src/adapters/mcp/register-agentic-tools.ts:291`. `args.assetId.split(/_s|_c/)` on `"image_s5_c2"` -> `["image","5","2"]` (verified with `node -e` this session). `const [kind,, sIdx,, cIdx] = arr` -> `sIdx="2"`, `cIdx=undefined`. Writes `sceneIndex:2`/`candidateIndex:undefined` into the `number`-typed `AssetDecision` contract (`src/agentic/types.ts:71`).
- **Fix:** `const [kind, s, c] = id.split('_'); const sIdx=Number(s.slice(1)); const cIdx=Number(c.slice(1));`.

### 6. `/api/video-download/process` has no `validateRequest` schema
- `src/adapters/http/api-routes.ts:113` (`router.post('/video-download/process', asyncHandler(VideoDownloadController.processDownloadRequest))`) — no `validateRequest({ body })`, unlike every sibling route. `video-download-controller.ts:9` reads `script`/`orientation`/`source` straight from `req.body`. `social-download/process` at `:114` IS validated — the asymmetry is the tell.
- **Fix:** add a Zod body schema enum-validating `orientation`/`source`; if a URL is ever included, run `isSafeUrl`.

### 7. `get_asset_preview` MCP tool `readFileSync` with no guard
- `src/adapters/mcp/register-agentic-tools.ts:188-189`. If `c.localPath` is a directory/symlink, `fs.readFileSync` throws synchronously inside the `registerTool` handler -> aborts the tool. Also defaults unknown extensions to `image/jpeg`.
- **Fix:** `try/catch`; check `fs.statSync(c.localPath).isFile()`; return an error response otherwise.

### 8. `/files/:videoId/*` `sendFile` of a stored path never re-rooted-asserted
- `src/adapters/http/file-routes.ts:13` `res.type('video/mp4').sendFile(video.videoPath)` (and `:26`/`:35`). The `videoIdParamsSchema` regex (`[a-zA-Z0-9_-]+`) blocks traversal on the *id*, but `video.videoPath` is a stored record field; if any upstream input influences it, the server serves arbitrary files.
- **Fix:** re-assert `path.relative(servedRoot, path.resolve(video.videoPath))` is in-bounds (not a string-prefix `startsWith`, which is bypassable) before `sendFile`.

## Hypotheses checked and cleared (do not re-flag)
- `viewFile` range check `end >= stat.size` (`local-filesystem.ts:198`): correct for inclusive byte ranges — NOT a bug.
- `deleteAsset` / `listFiles` routing: `assetFilenameParamsSchema` (`api.schemas.ts:143`) IS applied at `api-routes.ts:149` — safe.
- Display redaction `***` on `Authorization` lines: confirmed a tooling mask, not a literal (per the SKILL.md display-artifact pitfalls); no missing-`Bearer` bug.

## Verification contract observed
- Every item is `code-path analysis` (Express/MCP control flow traced to the line) except #5, which was `REPRODUCED` via `node -e "console.log('image_s5_c2'.split(/_s|_c/))"` -> `["image","5","2"]`.
- Express 4.22.2 confirmed (`node -e "require('express/package.json').version"`); `axios` default `maxRedirects` confirmed undefined -> follows redirects.
- Report-only: no source edited, `git diff` clean on in-scope paths.
