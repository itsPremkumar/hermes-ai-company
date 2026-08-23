---
name: offline-asset-generation
description: Produce REAL local image/video assets with zero network and zero new dependencies, using ffmpeg-static lavfi sources (gradients/color/anullsrc/zoompan). Use when a pipeline needs an offline fallback, placeholder, or test fixture that must be a genuine non-empty .jpg/.mp4/.png on disk — NOT a stub, NOT a fake path. Covers the Node 22 + TS-strict (NodeNext/CommonJS) gotchas that break naive implementations.
---

# offline-asset-generation

Generate genuine, non-empty media files **entirely offline** using `ffmpeg-static`
(already a production dependency in most Node media projects). No network calls,
no API keys, no new packages. Output is a real decodable asset, so tests that
assert `fs.existsSync(path) && statSync(path).size > 0` actually pass.

This is the technique used to fix `generateFallbackVisual` in the
Automated-Video-Generator (`src/agentic/pipeline/acquire.ts`), which had been
broken for months because it `require()`d a non-existent `asset-creator` module
and silently returned `null`.

## When to use
- A "fallback" / "placeholder" asset must be real on disk (test contract checks
  existence + byte size > 0, and `source`/`localPath`/extension).
- Offline-only constraint: NO network in the asset path.
- You want to avoid pulling in heavy native deps (sharp/canvas) just for a
  placeholder.
- Generating deterministic fixtures for integration tests.

## Core recipes (sync, offline, ffmpeg-static)

`ffmpeg-static` ships a static `ffmpeg.exe`/`ffmpeg` binary. Resolve its path
with `require('ffmpeg-static')` (CommonJS) or
`createRequire(import.meta.url)('ffmpeg-static')` (ESM-only contexts — see
pitfalls). Then drive it with `execFileSync(ffmpegPath, [...args], {stdio:'pipe'})`.

### Image — branded gradient placeholder (real .jpg)
```
-f lavfi -i gradients=s=720x1280:c0=0x1e3a8a:c1=0x0f172a:x0=0:y0=0:x1=0:y1=720:nb_colors=2
-frames:v 1 out.jpg
```
Produces a real ~14 KB JPEG. Works synchronously, zero deps beyond ffmpeg.

### Video — Ken Burns zoompan over silent audio (real .mp4)
```
-f lavfi -i gradients=s=720x1280:c0=0x1e3a8a:c1=0x0f172a:x0=0:y0=0:x1=0:y1=720:nb_colors=2
-f lavfi -i anullsrc=r=44100:cl=stereo
-filter_complex "[0:v]scale=1440:2560,zoompan=z=1.15:d=100:s=720x1280:fps=25,format=yuv420p[v]"
-map [v] -map 1:a -c:v libx264 -c:a aac -t 4 -shortest out.mp4
```
`zoompan=z=1.15` gives a slow 1.15x zoom ("Ken Burns" feel). The
`scale=1440:2560` overscan prevents black edges during the zoom. `anullsrc`
supplies a silent audio track so the mp4 has a stream for players that need it.
Real ~17 KB mp4 produced.

### Solid-color image/video
Swap `gradients=...` for `color=c=0x1e3a8a:s=720x1280:d=4` (video) — works for a
flat fill, but `gradients` is more visually useful as a placeholder.

## Backward-compat signature pattern
Keep the producer function **synchronous** if callers/tests expect a synchronous
return (`FetchedVisual | null`). `execFileSync` is synchronous, so a pure-ffmpeg
implementation preserves the contract with no `await`.

## Pitfalls (this is where naive versions fail)

1. **`import.meta` is ILLEGAL in CommonJS output.**
   If the file compiles to CJS (no `"type":"module"` in package.json, or
   `tsconfig` `module: NodeNext` without ESM), `createRequire(import.meta.url)`
   errors: `TS1470: The 'import.meta' meta-property is not allowed in files which
   will build into CommonJS output.` → use plain `require('ffmpeg-static')`
   instead (with an eslint `@typescript-eslint/no-var-requires` disable comment).

2. **sharp is async; `execFileSync` is sync.** If you reach for `sharp` to make
   the source image, `.toBuffer()` / `.toFile()` return Promises. There is no
   synchronous sharp call — do NOT try `await` inside a sync function, and do NOT
   reach for `deasync` (not installed, adds a native build dep). Prefer ffmpeg
   lavfi sources so the whole thing stays synchronous.

3. **ffmpeg cannot DECODE SVG in the gyan.dev "essentials" build.**
   `ffmpeg -i foo.svg out.jpg` fails with "no decoder found for: svg". So
   SVG→JPG via ffmpeg is a dead end. Generate the image with the `gradients`/
   `color` lavfi sources instead. (If you truly need SVG text rendered, use
   sharp's async API — but then make the whole function async.)

4. **ffmpeg path lives in node_modules; resolve it, don't hardcode.**
   `require('ffmpeg-static')` returns the absolute binary path. Always delete a
   stale `out` first (`fs.rmSync(out,{force:true})`) so a partial previous run
   doesn't poison the size check.

5. **Final guard:** after the ffmpeg call, verify
   `fs.existsSync(out) && fs.statSync(out).size > 0` before returning, else
   return null. A truncated/empty file will otherwise pass `ok(fb)` but fail a
   downstream `size > 0` assertion.

## Verification
After writing, prove the asset is real:
```
node --import tsx --test <path-to-test>   # both tests pass
# and/or a probe script that prints statSync(path).size (>0) and the extension.
```

## References
- `references/ffmpeg-lavfi-recipes.md` — copy-paste arg lists for image/video,
  with the exact commands proven to produce >0-byte assets on ffmpeg 6.1.1
  (gyan.dev essentials build) under Node 22.
