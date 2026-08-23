# AVG Enhancement Pipeline — Phases 1–10 recipes & traps

Companion to `agentic-verification-gateway` SKILL.md. Captures the concrete
techniques added in the "Agentic Video Pipeline: Human-Editing-Quality
Enhancement Specification" pass. The goal was a *cinematic* agentic render with
verifiable, key-free logic.

> STATUS at capture: code for Phases 1.1–1.4, 2.3, 4.1, 7.2, 8.3, 8.4, 9.1, 10.2
> was written into `src/agentic/{orchestrate,agent,gate}.ts`,
> `remotion/{AgenticVideo,Root}.tsx`, `bin/agentic-run.ts`, and a new
> `src/agentic/enhancement.test.ts`. Final `tsc` + full `tsx --test` + one live
> `npm run agentic` run to assert X7–X9 must be re-run to confirm GREEN before
> claiming verified (session was cut off before that final pass).

## Phase 1 — Remotion composition + render path

Remotion IS installed in this repo (`remotion`, `@remotion/cli` resolve; a real
Chrome lives at `C:/Program Files/Google/Chrome/Application/chrome.exe`).

**Pattern (`renderAgenticWithRemotion` in `orchestrate.ts`):**
1. Copy each approved asset + its voiceover into `public/agentic-assets/` so
   Remotion's `staticFile()` can resolve them (Remotion CANNOT read arbitrary
   absolute paths at render time).
2. `const { bundle } = require('@remotion/bundler'); const { renderMedia,
   selectComposition } = require('@remotion/renderer');`
3. `const bundleLoc = await bundle(path.resolve(cwd,'remotion/index.ts'), ()=>{}, { webpackCacheDisabled:true });`
4. `const composition = await selectComposition({ serveUrl: bundleLoc, id:'AgenticVideo', inputProps });`
5. `await renderMedia({ composition, serveUrl: bundleLoc, codec:'h264', outputLocation, inputProps, crf, concurrency:1 });`
6. `res.postRender = verifyRenderedVideo(out, totalFrames/fps);`

**`AgenticVideo.tsx`** consumes `RenderManifest` assets: `KenBurnsImage`
(`scale(zoom) translateY(pan)` on `<Img objectFit=cover>` + gradient/vignette
`<AbsoluteFill>` overlay), `SubtitleOverlay` for karaoke captions, `<Sequence>`
per scene, `<Audio>` for per-scene voiceover + ducked music, and `IntroScene`/
`OutroScene` cards. Register in `Root.tsx` as `id="AgenticVideo"`
(`fps=30, 1080x1920`).

**Trap:** Remotion render needs Chrome + RAM. On the user's ~150 MB-free box it
can OOM/hang. The CLI (`--renderer remotion`) must `try/catch` and **fall back
to `renderAgenticSlideshow` (ffmpeg-static)** so the run always yields an MP4.

## Phase 2.3 — vignette + gradient overlay (ffmpeg, VERIFIED working)

Append to the video chain AFTER captions (no separate input needed):
```
vfArgs.push(`${videoMap}vignette=PI/5[vig]`);
videoMap = '[vig]';
```
The `vignette` filter is a safe chain append (unlike `xstack`, which broke).
Gradient overlay: prefer CSS in the Remotion path; for ffmpeg, a generated
transparent→black bottom gradient PNG overlay is the reliable route (not done
this pass — left to Remotion).

## Phase 4.1 — audio ducking (side-chain) ffmpeg expression

`buildDuckExpression(visuals, full, duck)` builds a per-frame volume curve so
music dips during speech. Builds:
```
0.18-0.120*gt(between(t\,0.000\,1.500)+between(t\,3.200\,4.800)+...,0)
```
KEY TRAPS:
- `between(t,s,e)` commas MUST be escaped `\,` inside the filtergraph
  (`between(t\\,0.000\\,1.500)` in TS source because the backslash is also a JS
  escape → double backslash).
- The whole expression goes in `volume=eval=frame:volume='<expr>'`.
- Only duck when caption segments exist; otherwise return `null` and use a flat
  `volume=0.18`.
Pass-2 mux: `[1:a]${volFilter}[a];[0:a][a]amix=inputs=2:duration=shortest[aout]`.

## Phase 7.2 — smart caption chunking (`chunkCues`, VERIFIED logic)

Pure function, no ffmpeg. Rules:
1. Merge sub-100 ms OR <3-char micro-segments into the next segment.
2. Enforce a minimum 500 ms display (else `endMs = startMs+500`).
3. Split any segment >8 words into two balanced chunks at the midpoint.
Apply before writing the SRT so burned captions don't flicker.

## Phase 8.3 — progress events (`onProgress`)

`runAgenticPipeline(req, onProgress?)` emits `PipelineProgress`
`{stage, percent, message, sceneIndex?, candidateIndex?}` at each stage
(plan/acquire/verify/decide/gate/voiceover/render). CLI prints a single-line
`\r` progress. Decide emits per-asset `[s${i} c${j}] approved` live.

## Phase 8.4 — post-render verification (`verifyRenderedVideo`, ffprobe recipe)

```ts
const raw = execFileSync(ffmpeg, ['-i', mp4Path], {stderr:'pipe'}).toString();
// catch block: ffmpeg -i prints stream info to STDERR, not stdout
const hasVideo = /Video:\s*h264/.test(raw);
const hasAudio = /Audio:/.test(raw);
const dur = raw.match(/Duration:\s*([\d:.]+)/) → seconds;
```
Checks:
- **X7** `Output file valid`: exists && size > 100 KB.
- **X8** `Duration matches plan`: `|dur - expected| ≤ max(2, expected*0.05)`.
- **X9** `Audio track present`: `/Audio:/` matched.
Returns `PostRenderCheck` attached to `res.postRender`. CLI prints the 3 checks.
TRAP: there is NO `ffprobe-static` here — reuse `ffmpeg-static`'s `-i` stderr
parse (it prints the same stream info).

## Phase 9.1 — pick-best-candidate scoring (`scoreCandidate`, VERIFIED logic)

Score EVERY passing candidate per scene (not first-wins):
```
totalScore = confidence*0.5 + resolutionScore + fileSizeScore
            + relevanceBoost - diversityPenalty
```
- `resolutionScore`: parse `WxH` from path/URL; <0.2 MP → 1, >4 MP → 4, else 6.
- `fileSizeScore`: <50 KB → 1, 50 KB–3 MB → 6, >3 MB → 4 (avoid thumbnails &
  bloated files). Uses `fs.statSync(localPath).size`.
- `relevanceBoost`: +1 if any keyword appears in `source`/`license` metadata.
- `diversityPenalty`: reserved for gate X10 hue comparison (not wired this pass).
Attached to the approval rationale so the decisions report shows the score.

## CLI flags added (`bin/agentic-run.ts`, Phase 1.4 / 10.2)
`--renderer ffmpeg|remotion`, `--quality draft|medium|high`,
`--intro none|auto|custom`, `--outro none|auto|custom`, `--transition auto|…`,
`--sfx`, `--no-ducking` (sets empty `AUDIO_DUCK_LEVEL` → ducking skipped),
`--no-ken-burns`. Renderer defaults to `ffmpeg`; `remotion` falls back on error.

## Verification gate (re-run to confirm GREEN)
- `npx tsc -p tsconfig.json --noEmit` → EXIT 0.
- `npx tsx --test "src/**/*.test.ts"` → 0 fail (new `enhancement.test.ts` covers
  scoreCandidate, buildDuckExpression, chunkCues, verifyRenderedVideo).
- LIVE: `npm run agentic -- --topic "5 healthy breakfast ideas" --backend agent
  --orientation portrait --images` → expect contact-sheet PNG + decisions report
  + MP4 + printed X7/X8/X9 PASS.
