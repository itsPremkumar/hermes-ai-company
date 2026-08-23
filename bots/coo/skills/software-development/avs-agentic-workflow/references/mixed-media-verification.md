# Mixed-Media Video — End-to-End Verification & Pitfall Bank

Lifecycle proven 2026-07-27 in `C:\one\Automated-Video-Generator`:
**download (Pexels) + generate (Remotion codegen) + capture (browser screenshot) + photo → compose → verify.**

All file paths stay inside project root (input/visuals, output, workspace) — never system TEMP.

---

## 1. Acquire downloaded assets (Pexels)

Use `src/lib/visual-fetcher/index.ts` `searchVideos`/`searchImages` — they return
`MediaAsset[]` with DIRECT downloadable URLs.

**CRITICAL gotcha:** only `src/mcp-server.ts` auto-loads `.env`. A standalone
`.mts` driver run via `node --import tsx` MUST call `dotenv.config({ path: '.env' })`
itself, or Pexels silently falls back to free sources ("No API key set" may NOT even print).

**downloadMedia helper is BROKEN** (returns `undefined` error on real Pexels URLs;
empty error field). Use native fetch instead:
```ts
const r = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0' } });
fs.writeFileSync(dest, Buffer.from(await r.arrayBuffer()));
```
Verify: video files should be 5–20 MB; photos 1–5 MB. <100 KB ⇒ error page saved.

---

## 2. Generate Remotion motion (autonomous codegen)

```ts
const { runRemotionController } =
  await import('./src/agentic/media/hermes-remotion-controller.ts');
const res = await runRemotionController(
  [{ index: 0, kind: 'infographic', text: 'Market Growth',
     data: [20,45,70,95], labels: ['Q1','Q2','Q3','Q4'],
     palette: ['#0a0a14','#7c3aed','#22d3ee'], durationInFrames: 120 }],
  { jobId: 'batch', maxRetries: 4, fps: 30 });
// -> input/visuals/<jobId>_s<index>.mp4
```
Via pipeline JSON: `[GenMotion: dark analytics dashboard with animated bar chart]`
or `[Motion: BarChartInfographic]` per scene.

**Headless render pitfalls (all fixed in remotion-sequence.ts — keep in mind for new code):**
- `slide`/`wipe` must import from subpaths: `@remotion/transitions/slide`,
  `@remotion/transitions/wipe`. Main entry only has `TransitionSeries, linearTiming,
  crossZoom, filmBurn, linearBlur`.
- Shader/canvas transitions (crossZoom, filmBurn, linearBlur, wipe, dissolve) **HANG**
  under headless Chrome without a GPU. Only `slide` (pure CSS) is safe by default;
  others need `allowShaderTransitions: true` on a GPU machine.
- `renderStill` needs the Composition `durationInFrames` > the requested frame
  (else "frame N invalid").
- Multi-scene `<TransitionSeries>` headless render takes ~2–3 min. Background runners
  with short kill windows murder it mid-render and report bogus failures. Run foreground
  with `timeout 280`.

---

## 3. Capture website screenshots (browser)

1. `browser_navigate` to target (e.g. sproutern.com, a GitHub repo page).
2. `browser_vision` saves a PNG to the agent cache dir.
3. `cp <cache>/browser_screenshot_*.png input/visuals/s0.png`

**CRITICAL — screenshots are NOT photos.** Full-page captures are extremely tall
(e.g. 1920×8000). Fit-inside + pad → unreadable thin vertical strip with giant
black bars (caught by vision verification, NOT by ffprobe).

**Landscape scroll-pan (looks like a screen recording):**
```bash
ffmpeg -y -loop 1 -i s0.png -t 4 \
  -vf "scale=1920:-2,crop=1920:1080:0:'min(t*60,ih-1080)',fps=30" \
  -r 30 -c:v libx264 -pix_fmt yuv420p seg.mp4
```
(scale to full 1920 width, crop a 1080-high viewport, pan down 60px/sec.)

---

## 4. Normalize every asset to a uniform segment (ffmpeg)

`FF = ./node_modules/ffmpeg-static/ffmpeg.exe` (bundled, NOT on PATH).
All segments must be 1920×1080 @ 30fps h264 yuv420p for lossless `-c copy` concat.

**Video / Remotion clip (normalize + trim):**
```bash
$FF -y -i v0.mp4 -t 4 -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -r 30 -c:v libx264 -pix_fmt yuv420p -an seg.mp4
```
**Photo (ken-burns slow zoom):**
```bash
$FF -y -loop 1 -i i0.jpg -t 3 -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,zoompan=z='min(zoom+0.0008,1.25)':d=90:s=1920x1080:fps=30" -r 30 -c:v libx264 -pix_fmt yuv420p seg.mp4
```
**Screenshot:** see §3 scroll-pan recipe.

---

## 5. Concatenate (codec-identical ⇒ `-c copy`)

```bash
# list.txt: one "file 'C:/abs/seg.mp4'" per line (forward slashes)
$FF -y -f concat -safe 0 -i list.txt -c copy final.mp4
```
Any ordering of the four source types is valid (video-led, remotion-led,
screenshot-led, fully interleaved) — all were tested (90+ segment frames OK).

For native Remotion transitions between generated scenes instead of hard cuts, use
`renderSequence()` from `src/agentic/media/remotion-sequence.ts` (one bundle,
`<TransitionSeries>`, headless-safe `slide` default).

---

## 6. Verification gate (MANDATORY — the user insists on empirical proof)

1. **ffprobe** duration + 1920×1080 h264: `$FF -i final.mp4 2>&1 | grep -E "Duration|Stream"`
2. **Per-segment frame extraction** — middle of every segment. `-ss` AFTER `-i`
   for frame-accurate seeks on short files: `$FF -y -ss 6.5 -i final.mp4 -frames:v 1 frame.png`.
   A frame <~2 KB or missing ⇒ black/corrupt segment.
3. **Vision check** — run frames through vision analysis; confirm the SUBJECT matches
   the expected segment. This caught TWO real bugs this session:
   - screenshot rendered as unreadable thin strip (fixed with scroll-pan, §3)
   - wrong-direction `wipe` crash (valid values are `from-*`)

Keep a per-segment report line: `round|combo|seg|tag|type|desc|frame=OK`.

---

## 7. Pipeline (agentic-scripts.json) — proven end-to-end

A 6-scene `agentic-scripts.json` mixing ALL FOUR types (2× downloaded video,
1× photo, 2× `[GenMotion:]`, 1× screenshot) rendered via:
```bash
npm run agentic:batch          # reads input/scripts/agentic-scripts.json
```
→ `output/mixed_media_agentic_demo/_compose/final.mp4`, gate PASS, all segments
vision-verified. **`agentic:batch` does NOT take `--file`** (use `agentic:modular --file` for single-file jobs).

**Compose bug fixed 2026-07-27:** `src/agentic/operations/compose.ts` called
`resolveOutputName(job, finalVideo)` passing the FULL path as the base name; the
function re-joined it onto `outDir` → `ENOENT ... copyfile '…\final.mp4' ->
'…\C:\one\…\final.mp4'`. Symptom: batch summary says "1/1 completed" but the
final copy throws ENOENT. **Fix:** pass the base name only — `resolveOutputName(job, 'final.mp4')`.

## 8. Pitfall table (hard-won)

| Pitfall | Fix |
|---|---|
| Pexels "No API key" despite `.env` | standalone driver MUST call `dotenv.config()` |
| `downloadMedia` returns `undefined` error | download with native `fetch` + UA header |
| Screenshot unreadable thin strip | scroll-pan treatment (scale width, crop, pan) |
| Shader transitions hang headless | default `slide`; `allowShaderTransitions` for GPU |
| Background runner kills 2–3 min renders | run foreground with `timeout 280` |
| `wipe` direction `to-left` crashes | valid: `from-*` (e.g. `from-right`) |
| `renderStill` "frame N invalid" | Composition `durationInFrames` > target frame |
| Concat `-c copy` glitches | concat only codec-identical segments (§4 first) |
| `compose.ts` `resolveOutputName` doubled path | pass `'final.mp4'` base, not full path |
