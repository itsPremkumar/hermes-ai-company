# AVG production-readiness feature backlog — verified patterns

Code-level recipes from the "implement all useful things" hardening pass on
`itsPremkumar/Automated-Video-Generator` (agentic pipeline). All shipped
uncommitted; verified with `tsc -p tsconfig.json --noEmit` (0 errors) + per-module
`node:test` runs under `npx tsx --test`.

## The non-obvious API traps (cost real fix cycles — read first)

### `@remotion/captions` `parseSrt` signature
WRONG (compile error TS2740 / TS2345):
```ts
captions = parseSrt(fs.readFileSync(src, 'utf8'));      // expects a string
```
RIGHT:
```ts
const parsed = parseSrt({ input: fs.readFileSync(src, 'utf8') });
captions = parsed.captions as Caption[];
```
Also `Caption` uses `startMs` / `endMs` (NOT `start` / `end`). A `serializeSrtLocal`
helper built against `c.start`/`c.end` will silently break with `TS2339: Property
'start' does not exist`. Reuse the library's `serializeSrt` instead:
```ts
import { serializeSrt } from '@remotion/captions';
fs.writeFileSync(out, serializeSrt({ lines: translated.map((c) => [c]) }));
```

### `tsx` test files: DO NOT `fs.mkdirSync(tmp)` at module top level
Under `npx tsx --test`, code that does `const tmp = ...; fs.mkdirSync(tmp)` at the
top of the file, then writes fake fixture files there, then later reads them inside
a `test()` block, intermittently fails with `ENOENT: no such file or directory,
scandir '<tmp>'` — the dir is not reliably present at test execution time (hit 3x
across asset-cache / localize / publish tests). FIX: call `fs.mkdirSync(tmp,
{recursive:true})` INSIDE each `test()` body (or a `setup()` helper invoked in the
test), never at module scope. The `fs.rmSync(tmp,...)` cleanup at end of file is fine.

## Feature recipes

### #6 Global disk-backed asset cache (src/lib/asset-cache.ts)
- Key = SHA-256 of the asset URL; value = stored bytes in a global `.asset-cache/`
  dir (gitignored). TTL optional.
- Wire at the TOP of every download fn: compute `getCached(url)` -> if hit,
  `fs.copyFileSync(cached, destPath); return {path,cached:true}`. Store after a
  successful write with `storeCached(url, destPath)`.
- Import in `visual-fetcher.ts` (`downloadMedia`) AND `free-music.ts`
  (`downloadTrack`) so repeated jobs across the fleet reuse bytes (free, zero network).

### #1 Template engine (already existed — extend, don't rebuild)
`VIDEO_TYPE_PROFILES: Record<VideoType, Partial<AgenticConfig>>` (7 genres:
facts/tutorial/explainer/story/news/review/listicle) is applied in `resolveConfig`
via layered merge: `preset -> videoType profile -> explicit user cfg`. Extend each
profile to also carry pro-edit fields (hookFirst, variablePacing, jCutSec, intro)
so a genre selects the *feel*, not just grade/transition. Add `listTemplates()` +
`TEMPLATE_LABELS` for discovery/docs. Test: assert `resolveConfig({videoType:'news'})`
overrides `transition`/`grade`.

### #2 Multi-language subtitle sidecars (src/agentic/localize.ts)
- `localizeSrtSidecars({srcSrtPath, outDir, baseName, languages, brain})` -> for each
  lang, `translateLine(text, lang, brain)` (brain.completeJSON when model enabled,
  else returns original text — graceful offline fallback), writes
  `<baseName>.<lang>.srt`.
- Wire into `writeOutputArtifacts` (pass `languages` from `opts.languages`, threaded
  from `autopilot.ts` `cfg.languages`). Call AFTER the native `.srt` sidecar is
  copied next to the video.

### #3 Offline word-timing (src/lib/captions.ts `syllableWordTimings`)
When a voice engine returns audio but NO word boundaries (non-Edge engine,
personalAudio, or tone fallback), produce word-by-word cues instead of one block:
estimate per-word duration from syllable count (~165ms/syllable, clamp [120,600]),
normalize weights so cues fill `durationMs`, 40ms inter-word gap, pin last cue end
to `durationMs`. Used in BOTH `tts.ts` fallback sites (real-engine-no-boundary +
`fillMissing` tone path). True forced-aligner (whisper.cpp) is the upgrade path but
needs a native binary — the heuristic is the zero-dep offline default. TEST:
monotonic non-overlapping cues, first startMs===0, last endMs>=dur-1, every word
preserved.

### #8 Publish adapter (src/agentic/publish.ts)
- `buildPublishManifest` / `writePublishManifest`: lists 5 platform targets
  (youtube 16:9, tiktok 9:16, instagram 1:1, reels 9:16, local 9:16), picks the
  best-aspect file (`<job>_16x9.mp4` etc., else `<job>.mp4`, else any mp4), lists
  subtitle sidecars (native + `<lang>`), NEVER blocks.
- YouTube: if `process.env.YOUTUBE_ACCESS_TOKEN` present -> draft upload pending; else
  write a ready `curl` upload script (`<job>_youtube_upload.sh`) + draft manifest.
  Zero-cost, free YouTube Data API v3, no paid service.
- Wire into `writeOutputArtifacts` after metadata block; compute title/desc/hashtags
  via `generateFreeMetadata(res.plan)`.

## Verification gate (run before commit)
```
npx tsc -p tsconfig.json --noEmit     # expect 0 errors
npx tsx --test "src/**/*.test.ts"     # expect all green (baseline 235 pass / 0 fail / 1 skip)
npx eslint . --quiet                   # 0 errors (warnings ok)
```
