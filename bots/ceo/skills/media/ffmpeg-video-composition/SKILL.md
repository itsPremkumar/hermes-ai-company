---
name: ffmpeg-video-composition
description: Build/compose real videos from images, clips, audio, SFX, voice, and burned overlays using ffmpeg-static in a Node/TypeScript project. Covers the slideshow→overlays→audio-mix→export pipeline, the drawtext burned-text pitfalls, concat timing traps, and the "verify with one real composed artifact" discipline. Use whenever a task needs to assemble a video (slideshow, social clip, GIF/thumbnail/contact-sheet export, or bake editor signals into a file) from the Automated-Video-Generator or any ffmpeg-static setup.
---

# ffmpeg-video-composition

Pattern for composing videos entirely with `ffmpeg-static` (zero-cost, no API keys) in a Node/TS project. All examples assume `import ffmpegPath from 'ffmpeg-static'` and `import { execFileSync } from 'child_process'`. Prefer **array args** (`execFileSync(ff, [..])`), never shell-string concatenation — array args avoid quoting hell with `:` and spaces in drawtext.

## Pipeline shape (the reliable one)
1. **Per-scene clips first.** Generate one clip per scene, then concat — do NOT rely on the concat demuxer `duration` line.
2. **Overlays** via `drawtext` (burned text) — see pitfalls.
: 3. **Audio mix** — voice + music + sfx via `amix`, guarding empty inputs.
: P6. **`stabilize` is a TWO-PASS filter** — `vidstabdetect`
must run ALONE (writes a `.trf`), then `vidstabtransform=input=...trf`
is chained. Chaining `vidstabdetect` into the SAME single-pass
filter list as setpts/format/boxblur does NOTHING (no transform reads
the `.trf`). See references/pitfalls.md P6.
: P7. **Declared FX fields must be CALLED from compose** — a field in
`cli-job.ts` + an exported `apply*()` is NOT enough; grep that the
`apply*()` is actually invoked in the per-scene map. `kenBurns` and
`chromaKey` were once declared-but-dead. See references/pitfalls.md P7.
**The silent 100%-dead ones found this session** (all parsed into
`ScenePlan` by script-parser but NEVER consumed by `compose.ts`):
- **Per-scene BURNED CAPTION** — `compose.ts` burned only titleCard /
  lowerThird / endCta / emoji; it never burned `scenes[i].voiceoverText`
  (the spoken line). So `captions:'burned'` shipped silent, textless
  clips. FIX: in the overlay block, `scenes.forEach` → burn
  `captionText ?? voiceoverText` per scene with an `enable='gte(t,start)*lte(t,end)'`
  window from `cumStart[i]+durations[i]`.
- **`[Transition:]` inline tag + `job.transition`** — parsed into
  `ScenePlan.transition` but `buildSlideshow` only did `-c copy` hard cuts.
  FIX: build an `xfade` filterchain (per-scene type: fade/slide/zoomblur/cut).
- **`captionTheme`** — declared but ignored; overlays now resolves a
  `{color,weight,shadow}` preset (neon/softCard/highContrast/minimal/bold)
  applied to ALL burned captions; `drawTextFilter` gained a `shadow` option.
Discipline: after adding ANY field, grep the per-scene map in compose.ts
to confirm it is actually wired — that is exactly where these three hid.
4. **Export artifacts** — GIF / poster / contact-sheet from the final mp4.

### Build per-scene clips (IMAGES)
```
execFileSync(ff, ['-y','-loop','1','-i', img, '-t','3',
  '-vf', `scale=W:H:force_original_aspect_ratio=increase,crop=W:H`,
  '-r','25','-pix_fmt','yuv420p','-c:v','libx264','-preset','veryfast', clip]);
```
### Build per-scene clips (VIDEO)
Re-encode to target size/rate so concat `-c copy` is clean:
```
execFileSync(ff, ['-y','-i', vid, '-vf', `scale=W:H:force_original_aspect_ratio=increase,crop=W:H`,
  '-r','25','-c:v','libx264','-preset','veryfast', clip]);
```
### Concat clips
```
// write slideshow_list.txt: file 'scene_0.mp4' \n file 'scene_1.mp4' ...
execFileSync(ff, ['-y','-f','concat','-safe','0','-i', list, '-c','copy', out]);
```

### Burned overlays (drawtext)
Pass text in single quotes; escape apostrophes as `'\''`. Color: pass CSS names (`white`,`yellow`) **directly**; only prefix `0x` when the value is hex (`#RRGGBB` → `0xRRGGBB`). Do NOT prepend `0x` to a name like `white` (produces `0xwhite` → filter fails).
```
drawtext=fontfile='C\:\\Windows\\Fonts\\arial.ttf':text='Mountain Facts':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=h/2-40:box=1:boxcolor=black@0.4:boxborderw=6
```
Chain multiple overlays with `,`. Emoji text works (needs fontconfig; Windows arial.ttf is fine).

### Animated progress bar (drawbox — the safe recipe)
A thin bar pinned to the bottom that grows left→right over the clip. The `drawbox` filter does NOT accept `H`/`W` (capital) for `x`/`y`/`w`/`h` — it needs `iw`/`ih`. And `enable=` with a comma splits the `-vf` filterchain, so DON'T use it; the `min()` expression already clamps the width.
```ts
// dur = total clip duration in seconds (e.g. sceneCount * 3)
const dur = Math.max(1, fxVisuals.length * 3);
// grow: width = min(full width, full * t/dur). y pinned to bottom edge.
vf.push(`drawbox=x=0:y=ih-8:w='min(iw,iw*(t/${dur}))':h=8:color=white@0.9:t=fill`);
```
- `y=ih-8` (NOT `H-8`) — `drawbox` errors "Undefined constant or missing '(' in 'H-8'" otherwise.
- `w='min(iw,iw*(t/${dur}))'` — single quotes around the expression are REQUIRED so `:` inside isn't read as a filter separator.
- No `enable=` — at `t=0` the bar is 0px (invisible), at `t=dur` it's full width. The `min()` clamps automatically, so no cut-off logic needed.
- Verified visually: at t=2s/9s the bar is ~22% filled; grows to full by end. Vision-verify with `C:\` path (cf. agentic-dev pitfall re: MSYS paths).

### Audio mix (voice + music + sfx)
- **Guard empty inputs.** A 0-byte or missing audio file passed to `amix` makes the whole filter fail → no output video. Only push inputs that `fs.existsSync && statSync().size > 0`.
- `amix=inputs=N:duration=longest` for N≥2. For exactly 1 real audio input, just `-map` it (the `anullsrc` trick is fragile).
```
// amixInputs = ['-i', video, '-i', music, '-i', sfx1, '-i', sfx2]
// filterParts = ['[1:a]','[2:a]','[3:a]']
amix = filterParts.join('') + `amix=inputs=${filterParts.length}:duration=longest[a]`
execFileSync(ff, [...amixInputs, '-filter_complex', amix, '-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-shortest', final]);
```

### Export artifacts
- **GIF**: `ffmpeg -i final.mp4 -vf fps=12,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse out.gif`
- **Poster**: `ffmpeg -ss <sec> -i final.mp4 -frames:v 1 out.jpg`
- **Contact sheet**: `ffmpeg -i final.mp4 -vf "select=...,scale=320:-1,tile=Nx1" -frames:v 1 sheet.jpg`
- **WebM**: `-c:v libvpx-vp9 -c:a libopus`

### Output dimensions: resolve ONCE from orientation+aspect (the silent squash bug)
When a pipeline computes W×H from `orientation` ALONE, an explicit `aspect:"1:1"` (square) silently falls back to portrait (e.g. 720×1280) — the asset looks squashed and you only catch it via `ffprobe`/vision. **Resolve W/H ONCE** from BOTH signals and reuse that single pair everywhere (FX, slideshow, overlays, export) so all stages stay in sync:
```ts
const PORT = 720, LAND = 1280;
let outW, outH;
const asp = job.aspect;
if (asp === '1:1')        { outW = PORT; outH = PORT; }
else if (asp === '16:9') { outW = LAND; outH = Math.round(LAND * 9/16); }
else if (asp === '9:16') { outW = PORT; outH = Math.round(PORT * 16/9); }
else if (job.orientation === 'landscape') { outW = LAND; outH = Math.round(LAND * 9/16); }
else { outW = PORT; outH = Math.round(PORT * 16/9); } // portrait default
```
This ALSO prevents the Ken-Burns-vs-portrait mismatch: thread `outW/outH` into the `zoompan s=WxH` so a portrait job isn't forced to 1280×720. (Real AVS bug: `compose.ts` ignored `aspect`; fixed with this exact block — a square job went 720×1280 → verified 720×720.)


1. **Feed a SINGLE frame, NOT `-loop 1 -t N`.** `zoompan=...:d=frames` emits
   `d` output frames PER input frame. With `-loop 1 -t 3` you feed ~90 input
   frames and get 90×d frames → runaway render (multi-GB, appears to "hang",
   moov-atom-not-found if you kill it). Correct: `ffmpeg -i still.jpg -vf
   "scale=W:H:force_original_aspect_ratio=increase,crop=W:H,zoompan=z='min(zoom+0.0012,1.18)':d=FRAMES:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=WxH:fps=FPS"
   -t HOLD out.mp4` where FRAMES=round(HOLD*FPS). No `-loop`. Zoom-out variant:
   `z='if(eq(on,0),1.18,max(zoom-0.0012,1.0))'`.
2. **zoompan `s=WxH` sets the OUTPUT size — must match target orientation.** A
   hardcoded `s=1280x720` silently forces landscape and squashes portrait/reel
   (1080x1920) output even when the rest of the pipeline is portrait. Always
   thread the job's real W×H (and fps) into the zoompan string; default landscape
   only as a documented fallback. (Real AVS bug: `kenBurnsFilter` hardcoded
   1280x720 → fixed to take width/height/fps params + orientation-aware call site.)

### Vertical / Instagram-reel recipe (verified end-to-end)
- Canvas 1080x1920 @30fps. Per-asset fit: stock photo → cover-crop + Ken Burns;
  website screenshot → `scale=W:-1,pad=W:H:(ow-iw)/2:(oh-ih)/2:color=0x0a0e1a`
  (fit, no crop, on brand bg); logo → `scale=560:560:force_original_aspect_ratio=decrease,pad=...`.
- Per-scene duration = probed voiceover length + ~0.35s tail. Attach each VO to
  its scene clip, concat `-c copy`, then `amix` a music bed under the whole reel
  (`[1:a]volume=0.5,afade=out...[bg];[0:a][bg]amix=inputs=2:duration=first`).
- Captions: bottom scrim `drawbox=x=0:y=H-560:w=W:h=560:color=black@0.5:t=fill`
  then drawtext with `shadowcolor=black@0.8:shadowx=3:shadowy=3`. Pure-color
  subtitle text (e.g. 0xf5d0fe) NEEDS the shadow or it reads low-contrast on busy
  photos — vision-verify legibility, aim ≥9/10.
- Voiceover (zero-cost): bundled `edge-tts.exe --voice en-US-AriaNeural --rate +8%
  --text "…" --write-media out.mp3`. Rate flag is `--rate +8%` (SPACE, not `=`;
  `--rate=+8%` fails silently). Music bed: layered `sine`+`tremolo`+`afade` pad.
- Site-asset collection: browser screenshot per section, but DISMISS the PWA/app-
  install banner first (click its Dismiss ref on a fresh load) or it overlays the
  hero. curl the logo/opengraph.jpg directly. Stock VIDEO fetch is slow without a
  proxy — prefer `--kind image` and animate stills with Ken Burns instead.

### Per-scene BURNED CAPTIONS (the silent gap — was 100% missing)
`compose.ts` historically burned ONLY titleCard / lowerThird / endCta / emoji —
**never the scene's own spoken line**. So `captions:'burned'` produced silent,
textless clips. FIX: in the overlay block, iterate `scenes` and burn
`captionText ?? voiceoverText` per scene, themed, with an `enable` window from
`cumStart[i]` + `durations[i]`. Pull the caption from the SAME `ScenePlan` the
voice came from, so it stays in sync after scene reorder.
```ts
scenes.forEach((sc, i) => {
  if (!sc) return;
  const cap = (sc.captionText?.trim()) ? sc.captionText : (sc.voiceoverText ?? '').trim();
  if (!cap) return;
  const start = cumStart[i] ?? 0;
  const end = start + (durations[i] ?? DEFAULT_SCENE_SEC);
  // KINETIC: word-by-word highlight when overlay.kineticText is set
  if (overlay.kineticText && cap.split(/\s+/).length > 1) {
    const words = cap.split(/\s+/);
    const step = Math.max(0.05, (end - start) / words.length);
    words.forEach((w, wi) => {
      const ws = (start + wi*step).toFixed(2), we = (start+(wi+1)*step).toFixed(2);
      const full = words.map((x,k)=> k===wi ? x.toUpperCase() : x.toLowerCase()).join(' ');
      vf.push(drawTextFilter(full, '(w-text_w)/2', 'H-th-120', 40, overlay.font.color,
        { enable: `gte(t,${ws})*lte(t,${we})`, shadow: overlay.font.shadow }));
    });
  } else {
    vf.push(txt(cap, '(w-text_w)/2', 'H-th-120', 40, overlay.font.color,
      { enable: `gte(t,${start.toFixed(2)})*lte(t,${end.toFixed(2)})` }));
  }
});
```
PITFALL: the `enable` window contains a **comma** (`gte(t,a)*lte(t,b)`). In a
`-vf` string the comma is read as a filterchain SEPARATOR → the whole chain
dies silently (no text burns). Escape it as `\,` via `escExpr(e)=e.replace(/,/g,'\\,')`
before embedding in `enable=`. Verify with a frame at the mid-window — the
highlighted word should read correctly; for static captions the full line shows.

### SCENE TRANSITIONS (xfade chain) — the silent `[Transition:]` gap
`[Transition: fade|slide|zoomblur|cut]` was parsed into `ScenePlan.transition`
but `buildSlideshow` only did `-c copy` hard cuts. FIX: when ≥2 clips and any
transition ≠ 'cut', build an `xfade` filterchain:
```ts
// offset_i = sum(dur_0..dur_{i-1}) - i*T_DUR  (overlapping fades); T_DUR = 0.4
const tDur = 0.4; let offset = 0;
for (let i=1; i<clips.length; i++) {
  const kind = transitions?.[i-1] ?? defaultTransition ?? 'fade';
  const ttype = kind==='slide' ? 'slideleft' : kind==='zoomblur' ? 'zoomin' : 'fade';
  if (kind==='cut') segs.push(`[${i}:v][${i-1}:v]xfade=transition=fade:duration=0.001:offset=${offset.toFixed(3)}[v${i}]`);
  else segs.push(`[${i}:v][${i-1}:v]xfade=transition=${ttype}:duration=${tDur}:offset=${offset.toFixed(3)}[v${i}]`);
  offset += durOf(i-1) - tDur;
}
const last = clips.length - 1;
const filter = `[0:v]format=yuv420p,${segs.join(',')}`;  // ← map [v${last}], NOT [0:v]
// trim each clip to its exact hold first so xfade offsets line up
```
PITFALL: the xfade chain references input `[k:v]` = `trimmed[k]`; the FINAL
output label must be `[v${last}]` (not `[0:v]`). A 'cut' seam = xfade with
`duration=0.001` to keep the graph valid. Fallback to plain concat if xfade
fails, so a hard-cut still ships. Verify visually: a frame at a scene seam
should show BOTH scenes blended (crossfade), not a hard switch.

## VERIFICATION DISCIPLINE (critical)
Config-reachable + isolated unit tests is NOT proof the feature works. **Bake every signal into ONE real artifact and assert on its properties**: Duration > 0, 2 streams (video+audio) present, output file size > 0, GIF bytes > 0. In the agentic pipeline this is the `compose` mode: a single job spec drives plan → fetch → voice → compose → export, and the test checks `final.mp4` has video+audio and the GIF/poster/sheet exist. See `references/pitfalls.md`.

## Pitfalls (condensed — full detail in references/pitfalls.md)
0. **NEVER ship a lavfi `testsrc`/`testsrc2`/`color` output as a "sample video".** Those are SYNTHETIC encoder test patterns (animated color bars) — a user who asks for a "sample video" expects real content and will (rightly) call out "only colors" (verified 2026-07-31: exactly this complaint after a testsrc2 "sample"). If you use one for an encoder/pipe test, say so explicitly and label it as a test pattern. For a user-facing demo use REAL content: stock clips, or local images animated with zoompan/Ken Burns (below), or the AVS pipeline with local assets (`MEDIA_VERIFICATION_ENABLED=false` + `[Visual: localfile.png]` scenes — zero network, see avs-ffmpeg-pipeline).
1. `fontcolor=0xwhite` — CSS name + `0x` prefix breaks drawtext. Pass names raw.
2. `enable='gte(t,TB-3)'` — `TB` is NOT valid in ffmpeg enable expressions; whole `-vf` chain fails. Use a computed end time or drop `enable` for end-screen CTAs.
3. Concat `duration` line — the LAST `duration` entry is ignored by the concat demuxer; a single-image concat yields 1 frame (0.04s). Pre-generate per-scene 3s clips instead.
4. Empty/0-byte audio input to `amix` → silent failure, no output video. Guard sizes.
5. `stdio:'ignore'` on failure hides the real ffmpeg error for a full debug cycle — capture `e.stderr` and log it.
6. **`drawbox` uses `iw`/`ih`, NOT `H`/`W`** — `drawbox=...:y=H-8` fails with "Undefined constant in 'H-8'". Use `y=ih-8` (and `w=min(iw, iw*(t/D))`). drawtext/scale accept `W`/`H`; drawbox does not.
7. **Comma inside `enable='...'` breaks `-vf`** — `enable='gte(t,1)*lte(t,4)'` is read as a filterchain separator. Escape the comma as `\,` (helper `escExpr`). Same trap in drawtext `enable`.
8. **`fontweight` is NOT a drawtext option** — ffmpeg rejects `Option 'fontweight' not found`. Bold = point `fontfile` at the bold variant (`arialbd.ttf`, `georgiab.ttf`); wrap in a `resolveFontFile(family, weight)` helper that falls back to a file that exists on the box (Windows lacks `georgia.ttf` on some installs).
9. **Composite `-vf` fails at the FIRST bad filter** — when a multi-overlay chain errors, reconstruct the EXACT joined string (`filters.join(',')`) in a standalone probe to find the real culprit (ffmpeg reports the break downstream). See references/pitfalls.md P8–P11.
10. **`paletteFilter` real impl** — compute dominant color via `scale=1:1`→`rawvideo rgb24`, accept iff `colorDistance < ~110` vs a hue-target map. Declared-but-unapplied = no-op (cf. P7). Verified: blue image (97,130,176)→dist 82 kept; red rejected.
11. **`drawTextFilter` shadow + `captionTheme`** — add `:shadowcolor=black@0.85:shadowx=3:shadowy=3` to drawtext so captions survive busy backgrounds; resolve `captionTheme` (neon/softCard/highContrast/minimal/bold) to `{color,weight,shadow}` and apply to ALL burned captions (theme wins over `fontColor`).
12. **Per-scene caption / `[Transition:]` / `captionTheme` were 100% dead** — `compose.ts` burned only title/lowerThird/CTA/emoji (never `scenes[i].voiceoverText`), did hard cuts (`-c copy`, ignoring `ScenePlan.transition`), and ignored `captionTheme`. Result: `captions:'burned'` shipped silent clips, no transitions, default-white text. FIX: burn `captionText ?? voiceoverText` per scene with `enable` window (escape the comma!); xfade chain for transitions; theme preset for colors. Grep the per-scene map to confirm wiring after ANY new field.
