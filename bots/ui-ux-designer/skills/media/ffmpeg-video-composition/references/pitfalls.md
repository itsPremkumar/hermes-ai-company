# ffmpeg-video-composition — Pitfalls (reproductions + fixes)

Condensed from a real debug session building the Automated-Video-Generator
`compose` mode (Node/TS + ffmpeg-static 6.1.1 on Windows). All fixes verified.

## P1 — `fontcolor=0xwhite` breaks drawtext
**Symptom:** overlay ffmpeg step fails; the whole burned-text `-vf` chain is rejected.
**Cause:** code did `const c = color.startsWith('#') ? color : 0x${color.replace('#','')}`.
For `fontColor: "white"` (CSS name) this produced `fontcolor=0xwhite` → invalid.
**Fix:** detect hex vs name:
```ts
const isHex = color.startsWith('#') || /^0x?[0-9a-fA-F]{6}$/.test(color);
const c = isHex ? (color.startsWith('#') ? `0x${color.slice(1)}` : color) : color;
```
Pass CSS names (`white`, `yellow`) directly; only hex gets the `0x` prefix.

## P2 — `enable='gte(t,TB-3)'` invalid
**Symptom:** `Error when evaluating the expression 'gte(t,T-3)' for enable` → filter
graph init fails, no output video.
**Cause:** `TB` (total duration) is NOT a valid variable inside a drawtext `enable`
expression. (Using `T` alone is also unreliable in enable context.)
**Fix:** either drop `enable` for end-screen CTAs (show for whole duration), or
compute the video duration up front and use `gte(t,DUR-3)`.

## P3 — concat `duration` ignored → 1-frame video
**Symptom:** `base.mp4` Duration 00:00:00.04 (1 frame @ 25fps) even though each
image should hold 3s. Downstream GIF/contact-sheet empty.
**Cause:** concat demuxer list with `duration 3` per image — the LAST `duration`
line is silently ignored, and a single-image list becomes 1 frame.
**Fix:** pre-generate a clip per scene (`-loop 1 -i img -t 3 ...libx264`), then
concat the clips with `-c copy`:
```ts
execFileSync(ff, ['-y','-loop','1','-i', img,'-t','3',
  '-vf', `scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H}`,
  '-r','25','-pix_fmt','yuv420p','-c:v','libx264','-preset','veryfast', clip]);
// then: concat list of scene_N.mp4 with -f concat -c copy
```

## P4 — empty audio input crashes amix
**Symptom:** `final.mp4` never written; audio-mix step fails.
**Cause:** a 0-byte `voice_concat.aac` (Edge-TTS fallback produced no file) was
still pushed as an `-i` to `amix` → ffmpeg errors "Invalid data found".
**Fix:** only push inputs that exist AND have size > 0; for a single real audio
input, map it directly instead of the `anullsrc` trick:
```ts
const validVoices = audios.filter(a => a && fs.existsSync(a) && fs.statSync(a).size > 0);
// push normMusic / sfx only if fs.statSync().size > 0
const amix = filterParts.length === 1
  ? `[${ai-1}:a]anullsrc=channels=2:duration=0.1[a]`   // fragile; prefer ≥2 real inputs
  : `${filterParts.join('')}amix=inputs=${filterParts.length}:duration=longest[a]`;
```

## P5 — swallowed subprocess errors
**Symptom:** feature "video failed" with no root cause.
**Cause:** `execFileSync(..., { stdio: 'ignore' })` swallowed ffmpeg stderr.
**Fix:** in catch, log `String(e?.stderr ?? e?.message).slice(0,400)`. This is how
P1–P4 were actually surfaced.

## P6 — `stabilize`: vidstabdetect must run ALONE first
**Symptom:** shaky-footage stabilization produces no effect (or a broken/empty clip). The `vidstabdetect` filter and `vidstabtransform` are a TWO-PASS pair — they cannot be chained in one `-vf`.
**Cause:** code put `vidstabdetect=...` into the SAME single-pass filter list as `setpts`/`format`/`boxblur`. `vidstabdetect` writes a `.trf` transform file (and produces no visible stabilize on its own); chaining it with other filters in one pass means the `.trf` is never read by a transform pass.
**Fix:** run detect as a standalone pass that writes `result=<file>.trf`, THEN push `vidstabtransform=input=<file>.trf` into the real filter chain only if the `.trf` exists:
```ts
const trf = path.join(workDir, `fx_${i}_stab.trf`);
execFileSync(ff(), ['-y','-i', clipPath, '-vf', `vidstabdetect=shakiness=5:accuracy=15:result=${trf}`,
  '-an','-f','null','-'], { stdio:'ignore' });
if (fs.existsSync(trf)) filters.push(`vidstabtransform=smoothing=30:input=${trf}`);
```
**Verify:** a `fx_<i>_stab.trf` file is written AND the downstream clip gets the `vidstabtransform` filter applied (confirm via ffprobe -vf or just that the output clip differs / no error).

## P7 — declared FX fields must be CALLED from the compose path
**Symptom:** a feature shows in the `cli-job.ts` schema and the `FxJob` interface, but produces ZERO effect in the output video.
**Cause:** the apply function (e.g. `kenBurnsFilter()`, `applyChromaKey()`) was written and exported but NEVER invoked from `compose.ts`'s `applySceneFx` call / loop. The signal is "reachable" (typecheck passes) but dead at runtime.
**Fix / discipline:** for every new advanced field, grep that the matching `apply*()` is actually called inside the per-scene map in compose. Quick check after adding a field:
```ts
// in compose.ts applySceneFx call, pass the new field:
let out = applySceneFx(v, i, {
  clipSpeedByScene, stabilizeScenes, chromaKeyScenes,
  filterByScene, blurScenes,
  kenBurns: job.kenBurns,   // ← was MISSING; field existed, call wasn't
}, outDir);
out = applyChromaKey(out, i, { chromaKeyScenes }, outDir);
```
**Verify:** after compose, `ls` the per-scene dir for the expected artifact (`fx_0_kb.mp4` for kenBurns, `fx_1_key.mp4` for chromaKey, etc.) — presence of the file proves the call path is live, not just declared.

## P8 — drawbox uses `iw`/`ih`, NOT `H`/`W` (and the comma-in-`enable` trap)
**Symptom:** `Error when evaluating the expression 'H-8'` → filter graph init fails,
no output. Whole overlay `-vf` chain rejected.
**Cause:** `drawbox` (unlike `drawtext`/`scale`) does NOT accept the uppercase
`W`/`H` media variables in its geometry expressions; it expects `iw`/`ih` (input
width/height). Also: any `enable='...'` value containing a **comma** (e.g.
`enable='gte(t,1)*lte(t,4)'`) is parsed by the `-vf` shorthand as a *filterchain
separator*, breaking the chain. `drawtext` `enable` has the same comma problem.
**Fix:**
```ts
// progress bar pinned to bottom — use ih, not H
vf.push(`drawbox=x=0:y=ih-8:w='min(iw,iw*(t/${dur}))':h=8:color=white@0.9:t=fill`);
// escape commas inside an enable expression:
const escExpr = (e: string) => e.replace(/,/g, '\\,');
const en = opts?.enable ? `:enable='${escExpr(opts.enable)}'` : '';
```
Verify: run the composite `-vf` in isolation (all filters joined by `,`) against a
known-good clip; the FIRST filter to fail is the culprit (ffmpeg reports
`No such filter: 'some)'` or `Undefined constant ... in 'H-8'` pointing at it).

## P9 — `fontweight` is NOT a drawtext option (use a bold font FILE)
**Symptom:** `Option 'fontweight' not found` → drawtext fails, whole overlay chain dies.
**Cause:** ffmpeg `drawtext` has `fontfile`/`fontsize`/`fontcolor`/`text_shaping`
but NO `fontweight`. Bold is selected by pointing `fontfile` at the **bold variant
file** (`arialbd.ttf`, `georgiab.ttf`, `timesbd.ttf`, `courbd.ttf`), not by a
`fontweight` param.
**Fix:** map `(family, weight>=600)` → bold file; fall back to arialbd.ttf:
```ts
function resolveFontFile(family, weight) {
  const bold = (weight ?? 400) >= 600;
  const map = { 'arial':['arial.ttf','arialbd.ttf'], 'georgia, serif':['georgia.ttf','georgiab.ttf'], ... };
  const [reg, bld] = map[(family ?? 'arial').toLowerCase().trim()] ?? ['arial.ttf','arialbd.ttf'];
  return exists(join('C:\\Windows\\Fonts', bold ? bld : reg)) ? ... : arial.ttf;
}
```
Note: Windows ships `arial*.ttf`/`arialbd.ttf` but NOT `georgia.ttf` on every box —
`resolveFontFile` must fall back to a file that exists, else drawtext errors
"Cannot load font".

## P10 — composite `-vf` fails at the FIRST bad filter; reproduce the FULL chain
**Symptom:** a multi-overlay `-vf "drawtext...,drawtext...,drawbox..."` fails, but the
truncated error log shows only the first filter's start.
**Cause:** ffmpeg stops at the first filter it cannot parse; the reported filter is
often NOT the broken one — the break is downstream.
**Fix / discipline:** when an overlay `-vf` fails, reconstruct the EXACT joined
string (`filters.join(',')`) in a standalone `node`/`execFileSync` probe and run it
against `base.mp4`. The probe's full stderr names the real culprit (e.g. `H-8`,
`No such filter: '9)'`). Add a regression test that joins ALL overlay filters.

## P11 — `dominantColor`/`paletteFilter`: compute dominant color, match by distance
**Symptom:** `paletteFilter: 'blue'` accepted but had NO effect (no-op) — bulk fetch
kept off-palette images.
**Cause:** the field was parsed but never applied (declared-but-dead, cf. P7).
**Fix (real implementation):** after downloading each candidate, compute its dominant
color via `ffmpeg scale=1:1` → `rawvideo rgb24`, read 3 bytes; accept iff
`colorDistance(dom, PALETTE_TARGETS[hue]) < 110`, else delete the file:
```ts
function dominantColor(img) {
  const one = path.join(dir, `.dom_${basename(img)}.png`);
  execFileSync(ff, ['-y','-i',img,'-vf','scale=1:1','-frames:v','1',one], { stdio:'ignore' });
  const raw = path.join(dir, `.dom_${basename(img)}.raw`);
  execFileSync(ff, ['-y','-i',one,'-f','rawvideo','-pix_fmt','rgb24',raw], { stdio:'ignore' });
  const b = fs.readFileSync(raw); const c=[b[0],b[1],b[2]]; rmSync(one); rmSync(raw); return c;
}
```
Targets map: `blue:[30,90,200] red:[200,40,40] green:[40,170,70] ...`. Verified:
downloaded image dominant (97,130,176) → distance 82 → kept (within blue palette).
Use threshold ~110 (tune per strictness). Pair with a `wiring-fixes-test.ts` that
asserts a blue solid matches / a red solid is rejected.

## Reliable end-to-end check (what "done" looks like)
After `compose`, assert on `final.mp4`:
- `Duration: 00:00:03.xx` (≥ 3s for a 1-scene demo; scales with scene count)
- `Stream #0:0 ... Video: h264` AND `Stream #0:1 ... Audio: aac` (2 streams)
- `final.gif` bytes > 0, `final_poster_0s.jpg` exists, `final_contact_sheet.jpg` exists
In the agentic project this is covered by `tests/advanced-engine-test.ts` (8/8)
plus the live `agentic:mode:compose` run on job `adv_compose_demo`.
