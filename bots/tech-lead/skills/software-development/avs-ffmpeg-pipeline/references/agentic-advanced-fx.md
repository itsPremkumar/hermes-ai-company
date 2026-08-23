# AVS agentic per-scene advanced FX — render branch + chroma-key pitfalls

Condensed from a 2026-07 session that added `chromaKey`, `speed`, `stabilize`,
`filter` (bw/vintage/sepia), `blur`, `keyframes` as PER-SCENE fields driven from
these are the non-obvious failure modes
that cost hours and are NOT in the main SKILL.md pitfalls 1-22.

## 0. READ THIS FIRST — the chroma-key root cause (supersedes §2 and §3)
§2 (vignette) and §3 (color value) below were RED HERRINGS chased before the
real cause was found. THE actual fix: `colorkey`/`chromakey` only set matched
pixels to TRANSPARENT (alpha=0). Appending `format=yuv420p` DISCARDS the alpha
and reveals the original green underneath — so the key looks like a no-op. You
MUST composite the keyed (rgba) foreground over a background via `overlay`:
```
color=c=black:s=WxH:r=25:d=DUR,settb=1/25[bg];
[0:v]...scale/pad...,format=rgba,colorkey=0x00FF00:0.3:0.2[fg];
[bg][fg]overlay=shortest=1,format=yuv420p[,captions][,kin][v]
```
Also: NEVER judge a chroma key by output PNG byte size — a green frame and a
black frame with the same subject both compress to ~7-8 KB. `vision_analyze`
the frame and ask "black or green" explicitly. (Both lessons now in SKILL.md
pitfalls #29/#30.) With the overlay fix, similarity 0.3 keys fine; the higher
0.5 from §3 is not needed once you overlay.

## 1. The agentic (modular) CLI renders via the SEGMENT branch, not single-pass
`renderAgenticSlideshow` (src/agentic/orchestrator/render.ts) has TWO code paths:

- **Segment branch** (used by `agentic-modular.ts` pipeline): when
  `opts.segments` is set, each clip is rendered with a per-clip `vfChain`
  string (`[0:v]tpad=…[v]`) and concatenated. The advanced edits MUST be
  injected into `vfChain` (look up `res.plan.scenes[clip.idx]`).
- **Single-pass branch** (legacy `agentic-cli`/`compose`): builds `sceneFilters`
  (the `[i:v]…[v${i}]` map) → `vfArgs`. Edits here are DEAD in the modular CLI.

Symptom of editing the wrong branch: typecheck passes, render "succeeds", but
the FX are silently absent (output is unfiltered). Confirm by logging the
actual built filter string (`console.log('[SEG-ADV]', vfChain)`) and
re-rendering — the string must contain your filter (e.g. `colorkey=…`,
`format=gray`, `setpts=2*PTS`) for it to take effect. Put per-scene edits in
BOTH branches to stay safe.

## 2. `vignette=PI/5` re-injects a chroma-keyed background
`colorkey` makes the keyed area transparent (alpha). `vignette` fills that
alpha with the SOURCE green. Verified empirically:
- `colorkey+format=yuv420p` → black (correct)
- `colorkey+format=yuv420p+vignette` → GREEN (broken)
- `vignette+colorkey+format=yuv420p` → GREEN (broken)

Fix: skip the global vignette on chroma-keyed scenes:
```ts
const doVignette = opts.vignette !== false && !sp?.chromaKey;
```
Vignette is cosmetic; dropping it on a green-screen scene is harmless.

## 3. Chroma-key color must match the footage
- `colorkey=green` resolves to CSS `#008000` (DARK green).
- `colorkey=0x00FF00` is PURE green.
- A test clip made with lavfi `color=c=green` is `#008000` and will NOT be
  keyed by `0x00FF00`.
- Real green-screen footage is almost always `#00FF00`.

Fix: use a higher similarity so both shades key: `colorkey=0x00FF00:0.5:0.2`.
Always confirm by extracting a frame and `vision_analyze`-ing: green gone =
black background + foreground visible.

## 4. JSON object keys are strings
`agentic-scripts.json` `advanced: { "0": {...}, "1": {...} }` → keys are
STRINGS. Code doing `opts.advancedByScene[i]` with numeric `i` returns
`undefined` → FX silently skipped. Normalize:
```ts
const advRaw = opts.advancedByScene as Record<string, any>;
const adv = advRaw ? advRaw[i] ?? advRaw[String(i)] : undefined;
```

## 5. Speed + xfade timing caveat
`setpts=1/speed*PTS` extends playback time, but the scene-duration math in the
xfade offset loop uses the BASE `durationSec` (not the sped-up length). A
slow-mo scene can overlap the next scene's transition slightly. Functional but
needs a duration-scaling tweak for perfect timing if you care.

## 6. Local-only proof recipe (no stock download, no voice clone stall)
The full pipeline can STALL in VISUALS (Pexels download) or VOICE (chatterbox
clone 500 on CPU). For fast FX proof:
1. Generate local clips in `input/visuals/`:
   ```bash
   FFMPEG=$(node -e "console.log(require('ffmpeg-static'))")
   "$FFMPEG" -y -f lavfi -i "color=c=0x00FF00:s=720x1280:d=3,drawbox=x=260:y=500:w=200:h=200:color=red:t=fill" -t 3 -c:v libx264 -pix_fmt yuv420p input/visuals/greenscreen_pure.mp4
   # bw/scene: orange/blue cards similarly
   ```
2. Reference them in the job script: `[Visual: greenscreen_pure.mp4]` so
   `script-parser` binds LOCAL (no download).
3. Move `input/voices/sample_narrator.wav` aside (the voice stage auto-clones
   it and chatterbox_500 on CPU otherwise stalls the render).
4. Job `advanced` map drives the FX. Run:
   `npx tsx src/adapters/cli/agentic-modular.ts pipeline --file input/scripts/_adv_proof.json`
5. Extract frame: `ffmpeg -y -ss 0.5 -i "output/<job>/<title>.mp4" -frames:v 1 f.png`
   (if it errors "does not contain an image sequence pattern", add `-update 1`).
   Then `vision_analyze`.

## 7. `stabilize` (vidstab) status
`libvidstab` IS compiled into this box's ffmpeg-static 6.1.1 (`--enable-libvidstab`
present), so `vidstabdetect`+`vidstabtransform` two-pass is viable — unlike
some earlier assumptions. Not yet wired to per-scene signals in this session.
