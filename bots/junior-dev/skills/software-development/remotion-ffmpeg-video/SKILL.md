---
name: remotion-ffmpeg-video
description: Build, debug, harden Remotion + ffmpeg video pipelines (agentic text-to-video, slideshow renderers, AVGs). Covers Remotion duration bugs, resource-constrained rendering, stock-media keyword pitfalls, ffmpeg post-render gates, xfade/J-cut/branded-card (P34-P39), free-model AgentBrain. Use when a render truncates/hangs/OOMs/falsely fails a gate, or to "fix failing AVG unit tests" (branch-state trap + ffmpeg-static/network roots in references/avg-fix-failing-tests.md; P40/P41 in references/ci-typecheck-blindspot.md; P42-P44+aiVerify in references/avg-ai-verify-async.md; feature build/verify in references/avg-feature-build-verify.md; bounded production sweeps + ffprobe duration fix in references/avg-production-sweeps.md; Windows `spawn ENAMETOOLONG` + dotenv-placeholder Voicebox retry storm in references/avg-windows-enametoolong.md; audio-quality debugging in references/avg-audio-quality-debug.md; CI-as-verifier + cross-platform font/CI gotchas in references/avg-ci-cross-platform-gotchas.md; CI workflow traps in references/avg-ci-workflow-validation.md).
---

# Remotion + ffmpeg Video Pipelines

> **Tier-1 security hardening** (Remotion version drift, ffmpeg
> `drawtext` injection, SSRF guard on media downloaders, `.env`
> secret scrub, CI `format:check` glob fix): see
> `references/avg-tier1-security.md` — concrete util signatures +
> the exact escape/guard patterns, verified against the code.
> Reject external "reviews" that claim "no tests" / "unused files"
> without verifying; both were false for AVG.

Class of work: any project that turns text/scripts + stock media into MP4s via
**Remotion** (React composition) and/or **ffmpeg-static** (filtergraph slideshow).
The bugs below are recurring across such projects; the fixes are tool-general.

## When to use this skill
- Building or fixing a `Composition` / render path (Remotion `renderMedia`, `bundle`).
- ffmpeg filtergraph render (xfade, subtitles burn-in, audio ducking, vignette).
- Render truncates, hangs on `<Video>`, OOMs/times out, or fails a post-render gate.
- "Make it production-ready + stable" then prove it with real test renders.

## Core workflow (hardening pass)
1. `tsc --noEmit` + run the suite FIRST; fix compile/test before touching behavior.
2. Read every file in the render path; enumerate bugs by symptom, not by file.
3. Render ≥2 DIFFERENT topics through EACH renderer (ffmpeg + Remotion) and assert a
   post-render gate (X7 size / X8 duration / X9 audio) before calling it done.
4. Never persist API keys to files; pass inline as env vars only.

## Pitfalls (each is a real, repeated bug)

### P1 — Remotion composition truncates long videos
`Composition` is registered with a STATIC `durationInFrames`. `selectComposition`
then uses that static value, so any content longer than it is **clipped** (e.g. a
13s lion video with `durationInFrames={300}` loses the last 3s).
**Fix:** compute length from `inputProps` via `calculateMetadata`:
```tsx
<Composition
  id="AgenticVideo" component={AgenticVideo}
  durationInFrames={300} fps={30} width={1080} height={1920}
  calculateMetadata={({ props }: { props: any }) => {
    const fps = props.fps ?? 30;
    const intro = (props.introCard?.durationSec ?? 0) * fps;
    const outro = (props.outroCard?.durationSec ?? 0) * fps;
    const scenes = (props.assets ?? [])
      .filter((a: any) => a.kind !== 'music')
      .reduce((s: number, a: any) => s + Math.max(1, Math.round((a.durationSec ?? 4) * fps)), 0);
    return { durationInFrames: Math.max(30, Math.round(intro + scenes + outro)) };
  }}
  defaultProps={{ /* ... */ }}
/>
```

### P2 — 4K sources OOM/timeout Remotion on weak hardware
Rendering 2160×3840 sources under Chrome on a RAM-starved box hangs `delayRender`
and times out. **Fix:** transcode sources to 720×1280 BEFORE `bundle()`/copy to
`public/`, and relax Remotion limits:
```ts
// transcode each video source to 720p first
await execFileSync(ffmpeg, ['-y','-i',src,'-vf',`scale=-2:720`,
  '-c:v','libx264','-preset','veryfast','-crf','23','-c:a','aac',dest]);
// renderMedia options
{ imageFormat: 'jpeg', concurrency: 1, timeoutInMilliseconds: 0,
  chromiumOptions: { headless: true } }
```
Always wrap the Remotion call in try/catch and **fall back to the ffmpeg path** on throw.

**Remotion needs a CHROME/CHROMIUM to render — it is NOT headless-browser-free.**
On the user's Windows laptop this WORKS (proven live): Google Chrome is installed
at `C:/Program Files/Google/Chrome/Application/chrome.exe`, and Remotion can
either (a) download its own Chrome Headless Shell via `ensureBrowser()` (network
works here — it fetched ~113MB and cached it in `node_modules/.remotion/...`), or
(b) use the system Chrome via the `chromeExecutable` option. **CRITICAL:** passing
`CHROME_EXECUTABLE` alone is NOT enough — `selectComposition` still triggers its own
browser download; you must ALSO forward `chromeExecutable` into `renderMedia`:
```ts
// in renderAgenticWithRemotion, after building inputProps:
...(process.env.CHROME_EXECUTABLE ? { chromeExecutable: process.env.CHROME_EXECUTABLE } : {}),
```
Without that spread, `renderMedia` ignores the env var and re-downloads the headless
shell (works, but wastes the download + the system-Chrome option is dead).
**Verification (this session, committed `9e6b29c`):** a `--renderer remotion` run on
the laptop produced `job_*_remotion.mp4` with ALL X7–X15 gates passing. So Remotion
is a real, working second renderer on the laptop — it was only "blocked" on the
RAM-starved CI box, not on a normal dev machine. Default to the ffmpeg renderer on
constrained boxes; use Remotion when Chrome + a few hundred MB free are available.
To pre-cache the browser (so the render run doesn't spend its budget downloading):
```bash
node -e "require('@remotion/renderer').ensureBrowser({}).then(b=>console.log('READY',b.path)).catch(e=>console.log('ERR',e.message))"
```


### P3 — Post-render ffprobe gate falsely fails
- Detecting only `h264` (`/Video:\s*h264/`) marks valid hevc/vp9 outputs as broken.
  **Fix:** `const hasVideo = /Video:/.test(raw) && !/Video: none/.test(raw);`
- For a **crossfaded** ffmpeg timeline, actual duration = sum(scene durations) −
  `crossfade × (scenes−1)`. Passing the naive sum makes X8 "duration matches" fail.
  **Fix:** expected = `sum − xf*(n-1)`; tolerance `max(2, expected*0.05)`.

### P4 — `<Video src="...png">` hangs Remotion
A video-kind asset that is actually a generated `.png` placeholder makes Remotion's
`<Video>` hang on `delayRender`. **Fix:** pick Image vs Video by FILE EXTENSION, not
asset `kind`:
```tsx
const isVideoFile = /\.(mp4|webm|mov|m4v)$/i.test(asset.localPath);
```

### P5 — Stale `public/<assets>` dir leaks across runs
`staticFile()` resolves by filename; leftover transcoded files from a prior run can
be picked up. **Fix:** `fs.rmSync(assetDir, { recursive: true, force: true }); fs.mkdirSync(assetDir)` at the start of each Remotion render.

### P6 — `drawtext` crashes on apostrophes (and `alpha=` is UNSUPPORTED in this build)
`drawtext=text='${label}'` breaks when `label` contains `'`. **Fix:** escape
`label.replace(/'/g, '’')` before injecting into the filter. Also escape colons
in the text with `label.replace(/:/g, '\\\\:')` if the cue text could contain `:`.
The `enable=` expression needs the comma escaped as `\\,` (one backslash in the final
filtergraph), i.e. `between(t\\,${start}\\,${end})` in the source string — this is the
ONLY safe way to drive on/off windows.
**CRITICAL:** this ffmpeg-static 6.1.1-essentials build does NOT support the drawtext
`alpha=` expression ("Not yet implemented in FFmpeg, patches welcome"). A filtergraph
using `alpha='if(lt(t\\,...))'` fails the ENTIRE `filter_complex`. **Do NOT use `alpha=`**
for fades — rely on a hard `enable=` window (text pops in/out at the edges; reads fine).
If you see "Not yet implemented in FFmpeg" pointing at a drawtext option, strip it.

### P7 — Stock-media keyword queries get mangled
Joining ALL keyword phrases with a space into one query
(`"lions lions wildlife kings savanna"`) is rejected by Pexels/Openverse. **Fix:**
iterate INDIVIDUAL cleaned keywords (`kw.toLowerCase().replace(/[^a-z0-9 ]/g,' ')`),
try Pexels-first for images, loop per-keyword for fallbacks.
**DO NOT add a `"<visualPreference> of <topic>"` phrase** (e.g. `"video of lions"`).
This was once recommended for hit-rate but it is REDUNDANT NOISE — the fetcher already
knows the media kind from `visualPreference`, and the literal phrase `"video of lions"`
lowers stock relevance. Instead append CONTEXT phrases that actually help:
`["wild <noun>", "<noun> nature", "<noun> close up"]`. A brittle test that asserts
`kw.includes('video')` is what forced the bad phrase — fix the test to assert
distinctness/determinism/no-degenerate-phrase instead.

### P8 — Contact-sheet frame grab fails on short clips
`execFileSync(ffmpeg, ['-i', src, '-ss', '00:00:01', '-vframes', '1', frame])`
silently produces no frame for clips <1s (the `try/catch` swallows it), so the
contact sheet has a gap. **Fix:** tiny early offset and `-frames:v`:
```ts
execFileSync(ffmpeg, ['-y', '-ss', '00:00:00.1', '-i', src, '-frames:v', '1', frame], { stdio: 'ignore' });
```
This works for both short and long clips.

### P9 — Generated-media `.gitignore` + stale-cache trap
- Per-run artifacts (`public/agentic-assets/*` placeholder PNGs, `_captions_*.srt`,
  `_silent_*.mp4`, `_ducked_*.mp4`) MUST be gitignored or the source tree floods
  with junk (the trigger for a `.gitignore` fix this session). Add:
  ```
  public/agentic-assets/
  .video-cache.json
  agentic-pipeline/workspaces/
  ```
  Keep the planning `*.md` docs under `agentic-pipeline/` tracked if you want them.
- **Stale cache short-circuits the real fetcher:** a `.video-cache.json` that stored an
  Openverse flickr image under a `video:` key made the pipeline reuse a 502-broken URL
  instead of hitting Pexels. **Fix:** delete the cache and prefer Pexels for images in
  the no-video fallback; never trust a cached URL whose source 5xx'd.

### P9 addendum — ffprobe regex must not over-match
`/Stream #\d+:\d+: Video:/` (intended to be strict) FAILED the unit test because the
ffmpeg `-i` dump prints `Stream #0:0(und): Video:` (note `(und)` between the colon and
`Video:`). **Fix:** use `/Video:/.test(raw) && !/Video: none/.test(raw)` (see P3 above).

### P10 — ffmpeg `eq` filter has NO `temperature` option (this build)
ffmpeg-static 6.1.1's `eq` filter rejects `temperature=` ("Option not found"),
crashing the whole render. Warm/cool looks must be approximated with the options that
DO exist: `contrast`, `brightness`, `saturation`, `gamma`. Example grades:
```ts
const GRADE = {
  warm:       'eq=contrast=1.05:brightness=1.04:saturation=1.22:gamma=0.96',
  cool:       'eq=contrast=1.0:brightness=0.97:saturation=1.08:gamma=1.05',
  cinematic:  'eq=contrast=1.12:brightness=0.97:saturation=1.1:gamma=0.95',
  vivid:      'eq=contrast=1.08:saturation=1.35:brightness=1.0',
  neutral:    'eq=contrast=1.02:saturation=1.05',
};
```
(If you need true white-balance, use the separate `colortemperature` filter, not `eq`.)

### P11 — `zoompan` comma-escape doubling trap (patch-tool hazard)
`zoompan=z=min(zoom+0.0008\,1.04)` needs the comma escaped as `\,` in the FINAL
filtergraph. In a TS template literal that is `\\,` (two backslashes) in the SOURCE.
When you edit this line with a fuzzy `patch`, the tool can DOUBLE the backslashes to
`\\\\,` (four in source → `\\,` in output) and ffmpeg then fails with
`No option name near '1:s=720x1280'`. **Fix:** ensure the source literally reads
`\\,` (NOT `\\\\,`). If a render errors with that message, grep the zoompan line and
collapse any doubled backslashes back to two.

### P12 — Git branch trap on the AVG repo (commit to the RIGHT branch)
The Automated-Video-Generator repo carries a `gstack/hardening-audit-fixes` branch
(and others). If you open a session without `git checkout main`, your commit lands on
whatever branch is current — and `git push origin main` then reports "Everything
up-to-date" while your work is stranded on the wrong branch. **Fix pattern:**
1. Before ANY commit: `git branch --show-current` — confirm `main`.
2. If wrong: `git stash push -- <unrelated dirty files>` (leave other authors' WIP
   untouched), `git checkout main`, `git cherry-pick <wrong-branch-commit>` (the
   cherry-pick only carries the files you intended), `git push origin main`, then
   `git checkout <wrong-branch>` + `git stash pop` to restore the other author's state.
- Never `git add -A` on a shared/multi-branch repo — you'll sweep unrelated files into
  your commit. Stage only the files you actually edited.

### P13 — `xfade` transition name subset gap (this ffmpeg build)
ffmpeg-static 6.1.1-essentials implements only a SUBSET of xfade transitions.
`zoomblur` / `zoomblurin` / `zoomblurout` throw **"Not yet implemented in FFmpeg,
patches welcome"** with `const_values array too small for transition` — it crashes the
whole `filter_complex`. Verified-working names: `fade`, `slideleft` (`slideright`,
`wipe*` usually OK). **Rule:** collapse any unsupported transition to `fade`. In the
AVG `style-engine.ts`, `xfadeName()` maps `zoomblur → fade` and keeps `slideleft` as the
only non-fade variant. If a render dies with "Not yet implemented" on an xfade option,
that transition name is simply not compiled in — replace it, don't fight it.
Quick offline check that a transition name works (no network):
```bash
FFMPEG=$(node -e "console.log(require('ffmpeg-static'))")
"$FFMPEG" -y -f lavfi -i color=c=blue:s=720x1280:d=1 -f lavfi -i color=c=red:s=720x1280:d=1 \
  -filter_complex "[0:v][1:v]xfade=transition=slideleft:duration=0.5:offset=0.5[v]" \
  -map "[v]" -t 1.5 -c:v libx264 /tmp/t.mp4 && echo "slideleft OK"
```

### P15 — `ffprobe-static` returns `{path}`, NOT a string
`const ff = require('ffprobe-static')` yields an OBJECT `{ path: '.../ffprobe.exe' }`, not the path.
Passing the object to `spawnSync(ff, [...])` makes every probe silently fail → `probeAsset` returns `null`
and source/dimension checks false-fail. **Fix:**
```ts
const mod = require('ffprobe-static');
const bin = typeof mod === 'string' ? mod : mod.path;   // <-- .path
```
(Corollary: `ffmpeg-static` ALSO returns an OBJECT in recent versions — `require('ffmpeg-static')`
yields `{ path: '.../ffmpeg' }` (or a callable that returns the path), NOT a plain string. So BOTH
ffmpeg-static AND ffprobe-static need `.path` / `.default.path` when passed to `execFile`/`spawn`.
This session's 21 plugin type errors were ALL `ffmpeg-static` drift: `const ffmpeg = require('ffmpeg-static')`
then `execFile(ffmpeg, [...])` fails because `ffmpeg` is now `{path}` not `string`. Fix each call site:
`const ffmpegMod: any = require('ffmpeg-static'); const ffmpegPath = (ffmpegMod && typeof ffmpegMod==='object' && 'path' in ffmpegMod) ? ffmpegMod.path : String(ffmpegMod);`
The cleanest guard for either module: `const bin = (m && typeof m==='object') ? m.path : m;`.)

### P16 — ffmpeg detection filters print to STDERR, not STDOUT
`blackdetect` / `freezedetect` / `volumedetect` emit their stats to **STDERR** during processing. With the
null muxer (`-f null -`), ffmpeg exits 0 (or non-zero) and `execFileSync(..., {stderr:'pipe'})` returns only
**STDOUT** (empty for `-f null`). So the detection lines are LOST unless you capture stderr. **Fix — use
`spawnSync` and concat both streams:**
```ts
const { spawnSync } = require('child_process');
const res = spawnSync(ffmpeg, args, { encoding: 'utf8', maxBuffer: 50*1024*1024 });
const out = (res.stdout || '') + '\n' + (res.stderr || '');
// now blackdetect/freezedetect/volumedetect lines are present
```
(Do NOT rely on `execFileSync(...).toString()` for filter stats — it returns stdout only.)

### P18 — `subtitles` filter (libass) renders the WHOLE clip BLACK on this build — NEVER use it
ffmpeg-static 6.1.1-essentials ships libass with **no usable font** on this Windows/MSYS
box. Any `subtitles=file.srt` filter fails to initialise with
`Error while filtering: Generic error in an external library` (or `original_size` /
`Invalid argument` on the subtitles option) and — critically — the render still PRODUCES
a file that is **entirely black** (ffmpeg does not hard-fail the whole job; it outputs
black frames). This is invisible until a post-render `blackdetect` (X10) gate flags it.
**Fix — burn captions with `drawtext` (libfreetype), which works:** one `drawtext`
overlay per caption segment, shown via an `enable='between(t\,start\,end)'` window.
```ts
let ctag = videoChain, ci = 0, tBase = 0;
for (const a of visuals) {
  const dur = a.durationSec ?? 4;
  const segs = a.captionSegments?.length ? a.captionSegments
    : [{ text: ..., startMs: 0, endMs: Math.round(dur*1000) }];
  for (const s of segs) {
    const start = (tBase + s.startMs/1000).toFixed(2);
    const end   = (tBase + s.endMs/1000).toFixed(2);
    const safe  = s.text.replace(/'/g,'’').replace(/:/g,'\\:').replace(/\n/g,' ');
    vfArgs.push(`${ctag}drawtext=text='${safe}':fontcolor=white:fontsize=30:`
      + `box=1:boxcolor=black@0.5:boxborderw=10:line_spacing=4:`
      + `x=(w-text_w)/2:y=h-text_h-120:enable='between(t\\,${start}\\,${end})'[c${ci}]`);
    ctag = `[c${ci}]`; ci++;
  }
  tBase += dur;
}
videoMap = ctag;
```
Reproduction recipe (proves libass is the culprit, fast, no network):
```bash
FFMPEG=$(node -e "console.log(require('ffmpeg-static'))")
printf "1\n00:00:00,000 --> 00:00:02,000\nHello\n" > /tmp/cap.srt
"$FFMPEG" -loop 1 -i <any.jpg> -vf "subtitles=/tmp/cap.srt" -t 3 -y /tmp/t.mp4
# -> "Generic error in an external library", output is black/empty
"$FFMPEG" -loop 1 -i <any.jpg> -vf "drawtext=text='Hello':fontcolor=white:x=(w-text_w)/2:y=h-text_h-120" -t 3 -y /tmp/t2.mp4
# -> works, non-black
```
**Rule:** if you see an all-black render with audio present and the filtergraph contains
`subtitles=`, that is the cause. Replace with the drawtext loop above. Do NOT try to
"fix" the SRT path/force_style — libass is broken here regardless (see P19).

### P19 — `subtitles` SRT path fragility (relative OR absolute both fail here)
Even with a valid font, this build's `subtitles` filter rejects RELATIVE paths (resolves
against ffmpeg's own cwd, not `process.cwd()`, → "No such file or directory" → black
output). Passing an ABSOLUTE `C:\...` path avoids that specific error but still fails at
libass init (P18). **Net: avoid `subtitles` entirely** — use the drawtext loop (P18).

### P20 — `zoompan` `d=` is a FRAME COUNT, not seconds — `d=1` blacks out the scene
`zoompan=z=...:d=1` outputs exactly ONE frame, then the stream ends → the rest of the
scene duration renders black. With the default 25fps, `d` MUST be `ceil(durationSec*25)`.
```ts
const zoomFrames = Math.max(2, Math.round(dur * 25));
const zoom = doZoom ? `,zoompan=z=min(zoom+0.0008\\,1.04):d=${zoomFrames}:s=${W}x${H}:fps=25` : '';
```
If a Ken-Burns scene shows 1 sharp frame then black, this is why. (Note: in the AVG
pipeline `kenBurns` defaults OFF, so this only bites when Ken Burns is enabled.)

### P21 — X10 black-frame GATE false-positive (verify the GATE before the render)
When X10 reports black but the render completed with audio, the defect is often
**NOT the render** — it's `detectBlackFrames` in `src/agentic/video-analyzer.ts`
producing a FALSE POSITIVE from a garbled async read. (An OLD theory blamed an
invalid `pic_th` blackdetect option; that is WRONG for ffmpeg-static 6.1.1 — the
option `blackdetect=d=0.3:pix_th=0.15` is perfectly valid and is what the gate uses.
If you "fix" P21 by removing `pix_th`, you break the detector's sensitivity with no
benefit. See P52 for the REAL cause + fix.)

**Disambiguate REAL-black vs GATE-false-positive FIRST (before editing any render code):**
```bash
FFMPEG=$(node -e "console.log(require('ffmpeg-static'))")
F=suspect.mp4
# 1) direct probe with the EXACT gate params, on the ACTUAL output file(s)
"$FFMPEG" -i "$F" -vf "blackdetect=d=0.3:pix_th=0.15" -f null - 2>&1 | grep -i black_start
# no "black_start" line => the file is genuinely black-free; the gate is lying (P52)
# a "black_start:A black_end:B black_duration:C" line => REAL black at B-C seconds
# 2) also probe EVERY output, not just main: main + _1x1 + _16x9 + _9x16 + the _av_ intermediate
#    (the gate may analyze an aspect variant, not the file you assumed)
```
This session PROVED (7 output files × multiple runs) that when the gate reports
"4.08s black" but `blackdetect=d=0.3:pix_th=0.15` finds nothing on the actual file,
the gate's `detectBlackFrames` returned a false match — NOT a render bug. The reported
duration was CONSTANT (4.08–4.52s) across completely different content/colors, which
is impossible for real black. The fix is the `runCli` async flush-race in P52, NOT any
render or filter change.

**Net:** if you see an all-black-flagged render with audio present AND `blackdetect`
finds zero black on the real file, jump to P52. Do NOT touch the filtergraph, the
intro/outro card colors, or `pix_th` — those are red herrings for this failure mode.

### P52 — `runCli` async flush-race: `close` fires before stdout/stderr `data` flushes (the REAL X10/P21 false-positive cause)
`detectBlackFrames`/`detectFreezeFrames`/`analyzeAudio` in `video-analyzer.ts` call
ffmpeg/ffprobe via a `runCli(bin, args, timeoutMs)` helper that resolves
`out + '\n' + err` on the child `close` event. On a RAM-starved box (or any time the
process is under load), **`close` can emit BEFORE the trailing `stdout`/`stderr` `data`
chunks are delivered**, so the buffer the regex parses is INCOMPLETE/GARBLED — and the
blackdetect regex mis-parses a leftover/partial line into a bogus `black_duration`.
This exactly reproduces the "gate reports 4.08s black, direct ffmpeg finds none" symptom.
(The `close` resolution also means a `setTimeout` kill resolves with whatever was
buffered — same garbage risk.)

**Fix (applied + verified this session):** resolve only after BOTH stream `end`
events fire (the buffers are then guaranteed complete), and bump the default timeout
so a slow blackdetect run isn't killed mid-flush:
```ts
function runCli(bin: string, args: string[], timeoutMs?: number): Promise<string> {
  return new Promise<string>((resolve) => {
    try {
      const { spawn } = require('child_process');
      const ms = timeoutMs ?? Number(process.env.AGENTIC_FFMPEG_TIMEOUT_MS || 45000);
      const child = spawn(bin, args, { stdio: ['pipe', 'pipe', 'pipe'] } as any);
      let out = '', err = '', outEnd = false, errEnd = false;
      const finish = () => { clearTimeout(t); resolve(out + '\n' + err); };
      const t = setTimeout(() => { try { child.kill('SIGKILL'); } catch {} resolve(out + '\n' + err); }, ms);
      child.stdout?.on('data', (d: Buffer) => { out += d.toString(); });
      child.stderr?.on('data', (d: Buffer) => { err += d.toString(); });
      child.stdout?.on('end', () => { outEnd = true; if (outEnd && errEnd) finish(); });
      child.stderr?.on('end', () => { errEnd = true; if (outEnd && errEnd) finish(); });
      child.on('error', () => { clearTimeout(t); resolve(out + '\n' + err); });
      child.on('close', () => { if (outEnd && errEnd) finish(); else setTimeout(finish, 50); });
    } catch { resolve(''); }
  });
}
```
**Why this is easy to mis-diagnose:** the false positive looks identical to a real
black-frame bug (P18 libass / P20 zoompan / P22 dead-asset), and because it only
reproduces under load, an isolated manual `ffmpeg -vf blackdetect` on the same file
ALWAYS passes (you're running it alone, not inside the memory-pressured pipeline).
That contrast is the tell: gate says black, isolated probe says clean → P52, not the
render. Respect `AGENTIC_FFMPEG_TIMEOUT_MS` (default raised to 45000) so a cold box
degrades to the graceful empty-read fast instead of returning a partial buffer.

### P37 — Branded intro/outro CARDS: paint them clearly non-black, but the card color is NOT the X10 cause
The bright-placeholder rule (P23) is for MISSING-asset fallbacks. Branded intro/outro
TITLE CARDS are a SEPARATE consideration: if you paint them near-black they CAN trip
X10 (a real failure, not a gate bug — YAVG really is low). **But this session PROVED
the card color was NOT the cause of the recurring X10 false-positive** — brightening the
intro from `#0F3460` to `#2563EB` changed nothing because the gate's "black" was the
P52 async race, not the pixels. So:
- Paint intro/outro cards with NON-black brand colors so a real near-black card can't
  be flagged: intro `#2563EB` (bright blue) + white text; outro `#FF6B35` (orange) +
  dark text `#0a0a12`. Both read as clearly non-black under `blackdetect=d=0.3:pix_th=0.15`.
- Do NOT chase the card color when X10 false-flags — that's P52. Verify with a direct
  `blackdetect` probe (P21 disambiguation) before editing card colors.
(For the Remotion path, put a brand-colored `<AbsoluteFill>` BEHIND `<Video>` so a
missing/black transcode shows brand color, never pure black — see A10.)
   script run via `terminal` that does an EXACT `String.replace` on the unique line
   (match on a non-backslash anchor like `line_spacing=4`), then rewrite the enable
   clause with `String.fromCharCode(92)` if you must be byte-precise.
2. After ANY filter edit, re-run `npx tsc` AND a 1-scene render + `blackdetect`; a
   doubled/missing backslash shows up immediately as a failed filter or black frames.
3. If `patch` reports "Found N matches" — STOP and use the node-script route; the
   fuzzy matcher will keep hitting sibling lines (kinetic vs caption) that share the
   `between(t\\,..\\,..)` tail.

### P17 — `volumedetect` is an AUDIO filter (`-filter:a`), not video
Applying it as `-filter:v volumedetect` (or the `-filter` shorthand that defaults to video) means ffmpeg
never decodes the audio stream → `analyzeAudio` reads `max_volume: -999 dB` / `mean_volume: -999 dB`
(clipping falsely detected / loudness check fails). **Fix:** `['-i', file, '-filter:a', 'volumedetect', '-f', 'null', '-']`.
Quick check the filter fires:
```bash
FFMPEG=$(node -e "console.log(require('ffmpeg-static'))")
"$FFMPEG" -i clip.mp4 -af volumedetect -f null - 2>&1 | grep -E "max_volume|mean_volume"
# expect e.g. max_volume: -17.7 dB   mean_volume: -21.1 dB
```

### Extended post-render verification matrix (X7–X15)
`verifyRenderedVideo(mp4, expectedDurationSec)` in `src/agentic/gate.ts` now runs NINE checks (the user's
standing bar: "test every project / monitor logs / find the problem"). Each is deterministic + offline
(ffmpeg/ffprobe). Source: `src/agentic/video-analyzer.ts`.
- **X7** File valid — size > `max(100KB, 20KB × expectedDurationSec)` (short legit clips can be <100KB).
- **X8** Duration matches plan within `max(2s, 5%)`.
- **X9** Audio track present (`/Audio:/`).
- **X10** No long black frames — `blackdetect=d=0.3:pix_th=0.15` (**NOT** `pic_th`; that option is invalid on ffmpeg-static 6.1.1 and falsely flags the WHOLE valid clip as black — see P21). Fail if any black run ≥0.5s.
- **X11** No frozen frames — `freezedetect=n=0.003:d=0.5` (fail if any freeze ≥1.0s).
- **X12** Audio loudness in range — `volumedetect` peak between `-60 dB` and `0 dB` (a `-999` reading = broken/unreadable audio → fail; a quiet ambient track at `-25 dB` passes).
- **X13** No audio clipping — `peakDb < -1.0 dB` (true-peak clipping).
- **X14** Output dimensions valid — `ffprobe` width×height present; portrait OR landscape accepted.
- **X15** Web-compatible codec — `h264|hevc|vp9|av1` (NOT just h264, so valid non-h264 encodes pass).
Unit tests generate a real ffmpeg clip and assert X7–X15 behavior (see `references/ffmpeg-verification-matrix.md`).

### Source-asset checks (catch bad assets BEFORE render)
`src/agentic/asset-checks.ts` runs on every candidate in `verifyAll`:
- **I4** min image resolution (default ≥480px width) — a 240p upscale fails.
- **I5 / V6** aspect-ratio match vs target (default 9/16 portrait; ±15% tolerance).
- **V4** video duration fit vs scene need (≥50% of scene length).
- **V5** min video resolution (≥480px).
- **I7** duplicate detection — `sha256` of first 256KB; reused images flagged.
These are NON-fatal metrics (vision verifier stays the authority) so they enrich `AssetVerification.metrics`
without flipping `passes`. Run them so a bad asset is *seen* before it wastes a render.

### P14 — Autonomous self-healing runner (diagnose → fix → retry → report)
For "fully automated" pipelines, wrap the pipeline+render in a controller that watches
the event log, diagnoses the failure signature, applies a known fix, and retries (bounded)
instead of crashing. Concrete, proven design (AVG `src/agentic/autopilot.ts`):
- `diagnose(events)` returns zero-or-more fixes keyed by log signature:
  - stale cache / flickr / placeholder → `clear .video-cache.json`
  - CDN 5xx / ETIMEDOUT / ECONNRESET / fetchVisual failed → clear cache + retry
  - `ffmpeg failed` / X7 / X8 / X9 / `Invalid argument` / `No option name` → set
    `AGENTIC_RENDER_SOFTEN=1` (renderer disables kinetic text, uses shorter crossfade,
    forces ffmpeg path over Remotion)
  - unknown signature → 0 fixes → break (stop retrying, report failure)
- The controller returns a structured `AutoRunReport` (success, attempts, fixesApplied,
  `postRender`). This is what makes "user only says what video they need" real.
- **`PostRenderCheck` shape trap:** it exposes `pass` (all X7/X8/X9) and `checks[]`
  (each `{id,label,pass,detail}`). It does NOT have flat `.x7/.x8/.x9/.detail` fields.
  Code that reads `post.x7 && post.x8 && post.x9` will ALWAYS be falsy → the controller
  will mis-report success as failure. Read `post.pass` / `post.checks[].pass`.
- **Offline test of the self-heal loop:** inject a `runner` override into the controller
  so you can force a failing-then-succeeding sequence WITHOUT network/ffmpeg:
  ```ts
  autoRunVideo(req, { maxAttempts: 3, runner: async () => {
    calls++;
    if (calls === 1) return { out: 'bad.mp4', post: check(false, ['X7']), gatePass: true };
    return { out: 'good.mp4', post: check(true, ['X7','X8','X9']), gatePass: true };
  }});
  ```
  Assert `report.success === true`, `attempts === 2`, `fixesApplied.includes('render-soften')`.
- **Test-isolation gotcha (node:test):** env vars set by one case LEAK to later cases in
  the same process (e.g. `AGENTIC_RENDER_SOFTEN=1` set by a fix spills into the next
  `autoRunVideo` call). This produces misleading retry counts (a "no known fix" case loops
  to maxAttempts instead of breaking at 1). **Fix:** reset such env vars at the start of
  each case, or read them fresh inside the runner, not once per module.

### Editing-engine extension contract (AVG "human-feel" feature)
The agentic pipeline's look is driven by `src/agentic/style-engine.ts`:
`computeStylePlan(plan, {preset})` returns a deterministic `StylePlan` (per-scene
`transitionIn` kind, `grade`, `kinetic` cues). To extend the "advanced / fully
customizable" editing:
- Add a transition: extend `TransitionKind` + map it in `xfadeName()` (ffmpeg xfade
  names like `slideleft`, `zoomblurin`, `fade`; `cut` = hard `concat`).
- Add a grade: extend `GradeKind` + `gradeFilter()` (must use only valid `eq` opts, see P10).
- Add kinetic text: append to `SceneStyle.kinetic` (lower-third / word-pop) — rendered
  via `drawtext` with an `enable=` window ONLY (see P6: `alpha=` is NOT supported in this
  build, so no fade — text hard-pops at the window edges, which still reads well).
- Presets live in `computeStylePlan` (`cinematic` | `reels` | `documentary` |
  `documentary-cool` | `neutral`); CLI exposes `--preset <name>` and `--no-kinetic`.
  Transition mapping lives in `xfadeName()` — keep only `fade`/`slideleft` (see P13);
  never emit `zoomblur*` names.
The engine is PURE (no ffmpeg/network) — keep it that way; the renderer consumes the plan.

### Verification (do this before claiming done)
- `npx tsc -p tsconfig.json --noEmit` → 0 errors.
- `npx tsx --test "src/**/*.test.ts"` → 0 fail.
- Render ≥2 different topics; for each, assert post-render X7–X15: X7 (size floor),
  X8 (actual vs planned duration within tolerance), X9 (audio stream present),
  X10 (no long black frames), X11 (no frozen frames), X12 (loudness in range),
  X13 (no clipping), X14 (dimensions valid), X15 (web codec). The analyzer unit
  tests (`video-analyzer.test.ts`) already prove these on real ffmpeg clips.
- Confirm contact-sheet + decisions-report exist for visibility.

### P34 — Woven intro/outro + multi-clip xfade chain breaks on wrong offset math
Adding branded title cards (intro = cold-open, outro = CTA) into an ffmpeg
`xfade` slideshow by splicing them into the same filtergraph chain is the
correct approach, BUT the cumulative `offset` for each xfade MUST be computed
over the REAL ordered clip list (intro → scene0 → … → sceneN → outro), not
over `visuals` alone. A naive `offsetFor(visuals, i, xf)` only knows scene
durations, so as soon as there are ≥3 transitions the offsets drift and one
xfade pad fails to configure:
```
[Parsed_xfade_30 @ ...] Failed to configure output pad on Parsed_xfade_30
[fc#0] Error reinitializing filters!
Failed to inject frame into filter network: Invalid argument
```
This is a REAL render failure (not a gate false-positive) — it produces no output.
**Fix (the correct offset accumulation):** build an `orderedClips[]` array of
`{tag, dur}` (intro card, then each scene, then outro card). Track a running
`acc` start time; for transition `i` (between orderedClips[i-1] and [i]) the
xfade `offset` = `acc` (the picture start of clip `i`), where `acc` advances by
`prevDur - xf` after each clip. Pseudocode:
```ts
const ordered = [{tag:'vintro',dur:introDur}, ...scenes.map((a,i)=>({tag:`v${i}`,dur:a.durationSec??4})), {tag:'voutro',dur:outroDur}];
let acc = 0;
for (let i = 1; i < ordered.length; i++) {
  const prev = ordered[i-1], cur = ordered[i];
  const off = acc;                       // picture-start of cur
  // xfade [prev.tag][cur.tag] transition=...:duration=xf:offset=off
  acc += prev.dur - xf;                  // next clip starts after the overlap
}
```
The video INPUT indices for intro/outro are appended AFTER the scene stills
(and after any audio inputs), so their `[idx:v]` tags must be computed as
`visuals.length + (introClip?1:0) + (outroClip?1:0)` — NOT `visuals.length`.
Also: the audio `adelay`/`amix` J-cut math (see P35) must use the SAME `acc`
picture-start for each scene (plus `introDur`), and the audio input base index
must count intro+outro video inputs too (`visuals.length + (introClip?1:0) + (outroClip?1:0)`),
or the `[base+i:a]` tags point at the wrong file and amix reads silence.
**Render-isolation:** a broken xfade chain is only caught by a LIVE render —
`tsc` + unit tests pass (the logic is pure) but the filtergraph still fails.
Always run ≥1 real render after touching the woven chain (P24 recipe keeps it fast).

### P35 — J-cut via `adelay` + `amix` (audio leads picture) — correct wiring
"Human-feel" J-cut = each scene's voiceover starts `jCutSec` (≈0.4s) BEFORE its
picture cuts. In ffmpeg this is NOT a sequential `concat` (that aligns audio to
picture at t=0). Use per-segment `adelay` placed on an absolute timeline, then
`amix`:
```ts
const introDur = introClip ? (introDurSec) : 0;
voScenes.forEach((_, i) => {
  const picStart = introDur + offsetFor(visuals, i, xf);   // same `acc` as P34
  const audioStart = Math.max(0, picStart - (i === 0 ? 0 : jCut));
  delayed.push(`[${base + i}:a]adelay=delays=${(audioStart*1000).toFixed(0)}:all=1[a${i}]`);
});
const mix = delayed.map((_,i)=>`[a${i}]`).join('') + `amix=inputs=${voScenes.length}:duration=longest:normalize=0[aout]`;
```
`normalize=0` prevents amix from dividing volume by N (which would make VO
inaudible). Use `amix` duration=longest + the final mux `-shortest` so trailing
J-cut overlap (silence) is trimmed. Do NOT use `concat=n=...:v=0:a=1` for J-cut —
it has no overlap, so audio and picture stay locked (no lead).

### P36 — Woven xfade STILL fails without `settb=1/25` (P34 addendum)
Even with the correct offset accumulation from P34, the woven chain crashed with:
```
[Parsed_xfade_30] First input link main timebase (1/12800) do not match
                   the corresponding second input link xfade timebase (1/25)
[Parsed_xfade_30] Failed to configure output pad on Parsed_xfade_30
```
Cause: still inputs (`-loop 1 -i img.jpg`, the image2 demuxer) get timebase
`1/12800`, while `color` source cards (intro/outro) get `1/25`, and xfade needs
BOTH inputs on a matching timebase. **P34's offset math is necessary but NOT
sufficient** — you must also force a common timebase on every clip in the chain.
**Fix:** append `,settb=1/25` to each clip's filter (scene stills AND the
intro/outro `color` cards), right after `setpts=PTS-STARTPTS`:
```ts
// scene still filter (ends with):
`...setpts=PTS-STARTPTS,settb=1/25${zoom},${grade},format=yuv420p[v${i}]`
// intro/outro color cards:
`[${idx}:v]trim=duration=${dur},setpts=PTS-STARTPTS,settb=1/25,format=yuv420p[vintro]`
```
(Order: `setpts` first, then `settb`.) Without this, `tsc` + unit tests STILL
pass but a LIVE render dies at the first xfade — re-run >=1 real render after any
woven-chain edit (P24 recipe).

### P37 — Branded intro/outro CARDS trip X10 if near-black (distinct from P23)
The bright-placeholder rule (P23) is for MISSING-asset fallbacks. Branded
intro/outro TITLE CARDS are a SEPARATE trap: if you paint them `#0a0a12`
(deep navy, luma ~5/255), the X10 blackdetect gate flags the ~2.5s cold-open as
a black run and the render FAILS the gate (a real failure, not P21's gate bug —
YAVG really is ~5).
**Fix:** paint intro/outro cards with a NON-black brand color:
- intro card bg `#0F3460` (deep blue, luma ~30) + white text
- outro card bg `#FF6B35` (orange, luma high) + dark text `#0a0a12`
Both read as clearly non-black under `blackdetect=d=0.3:pix_th=0.15`.
(For the Remotion path, put a brand-colored `<AbsoluteFill>` BEHIND `<Video>`
so a missing/black transcode shows brand color, never pure black — see A10.)

### P38 — Live ffmpeg progress: use `spawn` + parse `time=`, not `execFile`
`execFile(ffmpeg, args, cb)` only gives the FULL stderr in the callback (after
the process exits) — so a 60-90s render shows NOTHING until it's done (the
"30s of silence" UX complaint). **Fix:** spawn with `stdio:['ignore','ignore','pipe']`
and parse `time=HH:MM:SS.ms` from `stderr` data chunks to print `render N%`:
```ts
const cp = spawn(ffmpeg, args, { stdio: ['ignore','ignore','pipe'] });
let last = -1, buf = '';
cp.stderr.on('data', (d: Buffer) => {
  buf += d.toString();
  const m = /time=(\d+):(\d+):(\d+\.\d+)/.exec(buf);
  if (m && totalSec > 0) {
    const secs = +m[1]*3600 + +m[2]*60 + parseFloat(m[3]);
    const pct = Math.min(99, Math.round(secs/totalSec*100));
    if (pct !== last) { last = pct; console.log(`  · render ${pct}%`); }
  }
  if (buf.length > 4096) buf = buf.slice(-2048);   // keep tail cheap
});
cp.on('close', (code: number) => code === 0 ? resolve() : reject(new Error('ffmpeg failed (exit '+code+')')));
```
Compute `totalSec` from the timeline: `introDur + Sum(sceneDur) + outroDur - xfadeOverlap`
where `xfadeOverlap = (clips - 1) * xf`. Pass `totalSec` into the runner so the
percentage is accurate. (`spawn` comes from `require('child_process')` too.)

### P39 — Multi-aspect export `scale` with `-2` parity BREAKS from 9:16 source
`exportMultiAspect()` scaling a portrait 9:16 render into 1:1 / 16:9 with:
```
scale=w='if(gt(iw/ih,W/H),-W,-2)':h='if(gt(iw/ih,W/H),-2,-H)',pad=W:H:(ow-iw)/2:(oh-ih)/2
```
fails with `Failed to configure input pad on Parsed_pad_1` for 1:1 and 16:9
(the `-2` auto-width produces an odd dimension the pad rejects). **Fix — use
`force_original_aspect_ratio=decrease`** (always valid, preserves aspect):
```ts
const filter = `scale=${w}:${h}:force_original_aspect_ratio=decrease,pad=${w}:${h}:(ow-iw)/2:(oh-ih)/2,setsar=1`;
```
This produces all three (9:16/16:9/1:1) from one source cleanly.

### P40 — Segmented (resumable) render via per-clip encode + `concat` demuxer
To make a render resilient (a failed clip retries in isolation instead of losing the
whole timeline), render EACH ordered clip (intro → scene0..N → outro) as its own MP4,
then join with the `concat` demuxer (`-f concat -safe 0 -i list -c copy`). This is the
C1 pattern in AVG `orchestrate.ts` (gated by `AGENTIC_SEGMENTED=1`); the proven single-pass
stays the default. The pitfalls that broke it on first attempt (each is a real failure):

- **Concat needs IDENTICAL stream layout across every segment.** If one segment has
  video-only (`-an`) and another has video+audio, `concat` aborts or desyncs. **Fix:**
  give EVERY segment both streams — for a scene with voiceover mux `[1:a]`; for a card
  with no audio use `anullsrc=channel_layout=mono:sample_rate=44100` (or `aevalsrc=0`).
  Trim the audio to the clip with `atrim=0:${dur},asetpts=PTS-STARTPTS`.
- **Label filter outputs + map them** when using `-filter_complex` (NOT `-vf`). A
  filtergraph that consumes `[0:v]` cannot be re-`-map 0:v`'d — that maps the raw input
  again and the encoder errors (`Error while opening encoder`). **Fix:** end the video
  chain with `[v]` and audio with `[a]`, then `-map '[v]' -map '[a]'`.
- **Still images need `loop` BEFORE `trim`.** A bare image input is 1 frame (~0.04s);
  `trim=duration=3` keeps only that frame → the segment is 0.04s and the joined video is
  a few frames long (X8/X7 fail). **Fix:** prepend `loop=loop=-1:size=1,` to the video
  chain for non-video clips.
- **`subtitles=` SRT path: use a RELATIVE path** even though P18/P19 say avoid `subtitles`
  entirely. If you DO burn captions per-segment, an ABSOLUTE `C:\...` path breaks the
  `subtitles` filter (the `C:` colon is read as an option separator). Write the SRT to a
  `agentic-pipeline/workspaces/<job>/render/_segN.srt` relative path and reference it with
  no drive colon. (The AVG segmented path uses the drawtext loop from P18 per segment
  instead — safer on this box.)
- **`\,` (escaped comma) breaks under `-vf`/`-filter_complex` simple-filter parsing.**
  zoompan's `min(zoom+0.0008,1.04)` with `\,` gets split into two filters →
  `No option name near '1:s=720x1280'`. **Fix:** avoid the comma — use
  `zoompan=z=zoom+0.0008:d=1:s=WxH` (small unbounded zoom; `d=1` is fine here because each
  segment re-runs zoompan per output frame and the clip is short — but see P20 for the
  full-timeline caveat; in a short segment the grow is <0.06).
- **Expected duration (X8) must be computed PER PATH.** The default single-pass subtracts
  xfade overlaps (`intro+scenes+outro − xf*(clips−1)`); the segmented path has NO xfade,
  so its actual = `intro+scenes+outro` (sum of clip durations). If X8 compares both to the
  same naive `sum − xfade` formula, the segmented video is flagged "too long" even though
  it's correct. **Fix:** compute `expectedDur` inside each branch (segmented = sum of clip
  durations; default = intro+scenes+outro − xfade) and pass that single value to
  `verifyRenderedVideo`. Verified: both paths pass X7–X15.

**Verification of the segmented path:** run with `AGENTIC_SEGMENTED=1` and assert X7–X15;
also confirm `tsc` (the per-segment code is in the same module, so type errors surface).
The `concat` step is stream-copy only — if segments encode but the join fails, the error
is almost always the stream-layout mismatch above.

### P41 — Orphaned untracked dirs break `tsc` (exclude, dont delete)
**NUANCE (this session corrected it):** `exclude` is DEFEATED when an INCLUDED file
imports the "excluded" file. If `include: ["src/**/*"]` and you add `"src/agentic/plugins"`
to `exclude`, the plugins STILL compile — because `src/agentic/orchestrate.ts` does
`import { ... } from './plugins/index.js'`. tsc pulls the imported file in REGARDLESS
of `exclude`. So:
- If the dir is TRULY orphaned (no importer outside it): `exclude` works. Verify with
  `grep -rn "plugins/audio/beat-sync" src --include=*.ts | grep -v "src/agentic/plugins/"` →
  no hits = safe to exclude.
- If a production file imports it (as here with `orchestrate.ts:38`): you CANNOT exclude it.
  The "orphaned" commit message was WRONG — the plugins are INTEGRATED. You must
  make the dir type-clean (fix the actual errors), OR restructure `include` to omit it, OR
  change the importer to lazy/`await import()` the plugins so they're not in the type graph.
- This session: the 21 plugin errors were `ffmpeg-static` TYPE DRIFT (P15 corollary — `require('ffmpeg-static')`
  now returns `{path}`, not `string`; `execFile(ffmpegObj, ...)` fails). Fix: extract `.path`
  at each call site (beat-sync, platform-export) + coalesce the `string|undefined`/`number|undefined`
  params (`cfg.offset ?? 0`, `cfg.lutDir ?? ''`, `cfg.minCutInterval ?? 0`, etc.).
- Do NOT delete the orphaned/integrated code (user rule: "don't delete things"); fix or exclude properly.

### P42 — User-supplied video clips (C6) + personal audio (C2): the render bugs that broke the first attempts
Extending the pipeline to accept the user's OWN footage / voiceover (per-scene, round-robin) surfaced four real failures NOT covered by P34–P40. Concrete fixes (committed, X7–X15 verified):

1. **`-loop 1` is image-only — never apply it to a video input.** `const videoInputs = visuals.flatMap(v => v.kind==='image' ? ['-loop','1','-i',v.localPath] : ['-i',v.localPath]);`. Applying `-loop 1` to a `.mp4` corrupts ffmpeg input parsing → "Option not found" / "Error opening input file". (P40 covers `-loop` for stills only — this is the video-inverse trap.)

2. **User clips are 29.97fps; the xfade chain is 25fps — resample EVERY clip with `fps=25` (not just `settb=1/25`).** Without it: `First input link main frame rate (25/1) do not match the corresponding second input link xfade frame rate (30000/1001)` → "Error reinitializing filters". Add `fps=25,` right after `setsar=1,` in scene filters AND intro/outro card filters. (`settb` alone does NOT resample the framerate — P36 covers `settb` but not the `fps=25` pre-filter for *video* inputs.)

3. **Personal-audio / video path resolution:** `inputAssetPath()` joins with `input/input-assets/` and expects a BARE filename. The CLI binding must store `path.basename(clip)`, NOT the full relative path (`agentic-pipeline/input-assets/clip1.mp4` → resolves to a non-existent nested path → silent fetch fallback). In STAGE 2.5, resolve `inputAssetPath(scene.personalAudio)` (NOT a bare `fs.existsSync(scene.personalAudio)` against cwd — that always fails and silently skips the user audio). Fixtures live in `input/input-assets/`.

4. **Duration sync plan→manifest:** STAGE 2.5 mutates `a.durationSec` (manifest asset) but a SEPARATE manifest build later uses `s.durationSec` from the PLAN (3/5/5), discarding the real media duration. You MUST ALSO write `scene.durationSec = realDur` so the plan-derived manifest inherits it. `estimateAudioDurationSafe()` (uses `require('ffprobe-static').path`) returns the real duration for both audio AND video. Without this, X8 planned duration is wrong.

5. **Intro → first scene MUST be a hard cut, not an xfade — AND the concat output needs `settb=1/25,fps=25` AND the render must NOT use `-shortest`.** The first xfade `[vintro][v0]xfade=offset=2` consumed the entire 2.5s intro (or, with `settb` only on inputs, threw `First input link main timebase (1/1000000) do not match the corresponding second input link xfade timebase (1/25)`). Force `const tk = prev==='vintro' ? 'cut' : ...` (cut → `concat=n=2:v=1:a=0,settb=1/25[outTag]`, cursor advances by `dur` with no xfade subtraction). The `settb=1/25` on the CONCAT OUTPUT is MANDATORY or the next xfade still sees a mismatched timebase and errors. A cold-open cutting into content is also better UX.
   **Two NEW gotchas found this session (both drop/truncate the video — X8 fails):**
   - **`concat` output ALSO needs `fps=25`**, not just `settb=1/25`. Without `fps=25`, the concatenated intro+scene clip reports a SHORTER duration to the next xfade's `offset` math, so the whole chain collapses to ~8s instead of the real ~17.5s even though each isolated concat works. Use `concat=n=2:v=1:a=0,settb=1/25,fps=25[outTag]`.
   - **NEVER use `-shortest` on the final mux when the audio is shorter than the video.** The audio chain (`amix=...duration=longest` of voiceovers only, NO music) spans only ~14s, while the video (intro+scenes+outro) is ~17.5s. `-shortest` truncates the 17.5s video down to the 14s audio ≈ 13.8s, and X8 (`actual vs planned`) FAILS. **Fix:** append `apad` to the audio (`[aout]apad[aout]`) so it pads to fill the video, and REMOVE `-shortest` from the pass1 mux args (video becomes the master). Verify: actual duration must equal `expectedDur` (17.5s), not the audio length.
   **`xfadeOverlap` for `expectedDur` must subtract BOTH the intro cut and the outro cut** (not just one): `xfadeTransitions = (visuals.length + (introClip?1:0) + (outroClip?1:0) - 1) - (introClip?1:0) - (outroClip?1:0)`. So `expectedDur = introDur + scenesDur + outroDur - xfadeTransitions*xf`. This makes the gate's planned duration match the real hard-cut render.
   **Isolation recipe (proves the filter math without the full pipeline):** write a standalone `.js` that runs ffmpeg with the EXACT video filtergraph (intro `concat` cut + `fps=25` + xfades + outro `concat` cut) on the real `_intro_*.mp4` / `_outro_*.mp4` / scene JPGs from a workspace, and `ffprobe` the result. It should report the planned duration (e.g. 17.52s). If it reports ~8s, the `fps=25`-after-concat is missing; if it reports ~13.8s, `-shortest` is the culprit in the real pipeline.

**CLI additions:** `--video-clips <csv>` and `--personal-audio <csv>` on `bin/agentic-auto.ts` → `cfg.videoClips`/`cfg.personalAudio`. autopilot forwards them AND forces `preferVisual:'video'` when `videoClips` present (so `--images` can't override a video clip).

### P51 — `concat` needs `fps=25` AND never `-shortest` when audio < video (general X8-truncation trap)
P42 #5 covers the intro-specific case, but the underlying ffmpeg behaviors bite ANY woven timeline, so they get their own entry:
- **`concat` filter resets frame rate.** A `concat=n=2:v=1:a=0,settb=1/25` output keeps the *timebase* but the consumer xfade reads the clip's reported duration from a frame-count that the concat may have resampled. Appending `,fps=25` forces a constant 25fps on the concat output so downstream `offset=Math.max(0,cursor-xf)` math lines up. Symptom of the missing `fps=25`: the full chained filter yields ~8s for a 17.5s-intended video even though the isolated `concat` of two clips reports the right sum — the SECOND transition's xfade mis-reads the (now shorter) prior clip.
- **`-shortest` silently truncates the master video to the shorter audio stream.** When the audio chain is voiceovers-only (no music bed), `amix=...duration=longest` tops out at the last voiceover's end (~14s) while video is ~17.5s. `-shortest` then clips the video to ~13.8s and X8 (`actual vs planned`) FAILS with no error — the render "succeeds" but is short. **Fix:** pad the audio to the video with `[aout]apad[aout]`, drop `-shortest`, let the video stream be the mux master. (Keeping `-shortest` is only safe when you KNOW the audio is ≥ video length, e.g. a full-length music bed is present.)
- **When debugging an X8 mismatch, isolate the filter, not the pipeline.** A standalone `ffmpeg -filter_complex '<exact chain>'` on the real asset files + `ffprobe` on the output proves whether the bug is in the filtergraph (offsets/timebase) or in the mux args (`-shortest`), in seconds — far faster than a full E2E render that also exercises TTS/music. This was how P42#5's two sub-bugs were separated (8s = missing `fps=25`; 13.8s = `-shortest`).

### P43 — Free-music provider network hang freezes the WHOLE pipeline (last E2E blocker)
`src/lib/free-music.ts` providers (`OpenLofiProvider`, `InternetArchiveProvider`) call `axios.get(url, { timeout: 10000 })` to GitHub/archive.org. On a flaky/offline box those calls STALL and RETRY across every scene → the run hangs at `EXIT=124` with only `[FREE-MUSIC] Provider open-lofi failed: 404` / `internet-archive failed: 500` repeated, never reaching the render. The log ALREADY shows `Reusing cached free music: twenty_minutes (local)` WORKING — so the fallback exists; the providers just shouldn't be *attempted* when they'll hang.
**Fix (APPLIED this session — committed):**
- Add a module-level `withTimeout<T>(p, ms, label)` helper using `AbortController` + `Promise.race` that REJECTS (not just aborts) after `ms`, so a stalled `axios`/fetch can't leave the call hanging: `withTimeout(axios.get(url, { timeout: 6000 }), 6000, 'open-lofi catalog')`.
- Reorder `defaultProviders()` to try `local` FIRST (`[localProvider, openLofi, internetArchive]`). The cached/bundled `twenty_minutes.mp3` resolves INSTANTLY offline; network providers only fire when no local/cached track exists — and even then they now fail-fast at 6s.
- Apply `withTimeout` to ALL three network calls in `free-music.ts`: `OpenLofiProvider.loadCatalog` (axios, 6s), `InternetArchiveProvider.search` (axios, 6s), `downloadTrack` (axios, 15s).
- **Music normalization is OFF by default.** `normalizeAudio()` (re-encodes to 128k mp3) used `execFileSync(ffmpeg, …)` with no real interrupt — on a RAM-starved box that spawns ffmpeg synchronously and BLOCKS THE WHOLE PROCESS (see P45). Now `if (process.env.AGENTIC_NORMALIZE_MUSIC !== '1') return src;` — the bundled/cached track is already standards-compliant, so the re-encode is a non-essential nicety. This alone killed the 200s hang (the 4 `[FREE-MUSIC] Reusing cached...` lines appeared instantly after the fix).
- Verify: run with `--no-sfx` + `OPENVERSE_ENABLED=false` and confirm `Reusing cached free music: twenty_minutes (local)` appears in <1s and the pipeline proceeds past music.
**Why it matters:** this + P45 were the two things that kept the agentic pipeline from completing an end-to-end render on this box. Every other C2/C6 bug (P42 #1–#5) is fixed and typecheck-clean; the music/normalize hang was the gate.

### P45 — Synchronous `spawnSync`/`execFileSync` PERMANENTLY hangs a RAM-starved box (the master hang pattern)
This is the ROOT CAUSE behind P43's `normalizeAudio`, and it bites ANY media pipeline on this user's Windows box (~6GB RAM, often 70–150MB free). `spawnSync`/`execFileSync` block the Node event loop; when the OS can't fork the child (EAGAIN under memory pressure) the JS timer inside `timeout:` NEVER fires, so the call hangs FOREVER — not for `timeout` ms. `Promise.race`/AbortController around an ASYNC spawn DOES work because the timer runs in the unblocked event loop.
**Every sync child-process call in the media path must become async `spawn`/`execFile` + a hard `Promise.race` timeout, OR be skipped by default.**

**ALL known hang sites are now RESOLVED (this session):** every sync ffmpeg/ffprobe call in the AVG media path was converted to async `spawn` + `SIGKILL`-on-timeout, with callers updated to `await`:
- `src/lib/visual-fetcher.ts` `getVideoMetadata` → async `spawn` + 15s timeout (callers `getVideoDuration`, `scene-editor.ts`, `video-generator.ts` `await`ed).
- `src/lib/free-music.ts` `normalizeAudio` → OFF-by-default (returns `src` unless `AGENTIC_NORMALIZE_MUSIC=1`); `defaultFfprobeRunner` + `verifyMusic` → async `spawn` + timeout.
- `src/agentic/asset-checks.ts` `probeAsset` + `checkSourceAsset` → async `spawn` + timeout; `verifyAll` (`verify.ts`) `await`s both. **This is the one that bit `runGateway`** — STAGE-3 source checks call `checkSourceAsset` for every local image, and the sync `spawnSync(ffprobe)` blocked the whole pipeline at `EXIT=124` (see P46 for how it was pinned).
- `src/agentic/orchestrate.ts` `estimateAudioDurationSafe` → async `spawn` + timeout (used in STAGE 2.5 video/personal-audio duration sync).
- `src/lib/media-verifier.ts` `runFfmpeg` + `extractVideoFrame` → async `spawn` + timeout (vision frame-extract path — `extractVideoFrame` now `await`ed in `verifyWithVision`).
- `src/agentic/video-analyzer.ts` — **fully rewritten** so `detectBlackFrames`, `detectFreezeFrames`, `analyzeAudio`, `analyzeDimensions`, `analyzeOutput` are async with a shared timeout-backed `runCli` helper (fixes the X10–X15 post-render analysis hang).
- `src/agentic/gate.ts` `verifyRenderedVideo` → `async` with an async `spawn` probe + `await`ed analyzer calls; orchestrate call sites `await` it.

**The async-spawn-with-timeout recipe (reuse everywhere):**
```ts
function withTimeout<T>(p: Promise<T>, ms: number, label: string): Promise<T> {
  return Promise.race([
    p,
    new Promise<T>((_, rej) => setTimeout(() => rej(new Error(`${label} timed out after ${ms}ms`)), ms)),
  ]);
}
// ffprobe/ffmpeg probe:
const out = await new Promise<string>((resolve, reject) => {
  const child = spawn(ffprobeCmd, args, { stdio: ['pipe','pipe','pipe'] } as any);
  let stdout = ''; const t = setTimeout(() => { try { child.kill('SIGKILL'); } catch {} rej(new Error('timeout')); }, 15000);
  child.stdout?.on('data', (d: Buffer) => { stdout += d.toString(); });
  child.stderr?.on('data', (d: Buffer) => { /* keep tail if needed */ });
  child.on('error', (e: Error) => { clearTimeout(t); reject(e); });
  child.on('close', (code: number) => { clearTimeout(t); code === 0 ? resolve(stdout) : reject(new Error('ffprobe failed')); });
});
```
**Rule of thumb for this box:** if a render/pipeline hangs at `EXIT=124` with NO further log line after a `spawnSync`/`execFileSync(ffmpeg|ffprobe)` call site, that sync call is the blocker — convert it. P16 (ffprobe `.path`) and P38 (use `spawn` + parse `time=`) already point the same direction; P45 is the generalization.
**Timeout env vars:** respect `AGENTIC_FFPROBE_TIMEOUT_MS` (default 15000) and `AGENTIC_FFMPEG_TIMEOUT_MS` (default 20000) in the spawn wrappers so a cold box degrades to the graceful fallback fast instead of stalling.

### P53 — `ffmpeg -v error` SILENCES blackdetect lines (the false-negative that wasted a multi-session loop)
This is the single most expensive mistake made on the AVG X10 investigation and deserves its own number. `blackdetect` / `freezedetect` / `volumedetect` emit their stats to **STDERR at INFO level**, not error. Running `ffmpeg -v error -i FILE -vf "blackdetect=..." -f null -` prints **nothing about black** — the detection lines are below the error threshold — so a file with REAL black frames reports "no black". This session (and a prior one) ran ~10 iterations convinced the render was black-free, then a LIVE-pipeline debug dump showed `[blackdetect] black_start:9.52 black_end:13.6 black_duration:4.08` on the SAME file. The gate was RIGHT; the manual probe was WRONG.

**Two distinct X10 failure modes — know which BEFORE editing render code:**
1. **REAL black** = `blackdetect` lines ARE present (file genuinely has black at the reported times). Fix the RENDER (xfade offset math / dead asset / subtitles-libass / zoompan-d). See P18/P20/P22/P34/P42.
2. **GATE false-positive** = `blackdetect` lines ABSENT but the gate still reported black. Fix `runCli` async flush-race (P52) or the `pic_th` invalid-option trap (P21). Do NOT touch the filtergraph.

**The ONE command that disambiguates (run it on EVERY output, not just main):**
```bash
FFMPEG=$(node -e "console.log(require('ffmpeg-static'))")
F=agentic-pipeline/workspaces/<job>/render/job_<job>.mp4
# NO -v flag (default verbosity prints blackdetect at info level)
"$FFMPEG" -i "$F" -vf "blackdetect=d=0.3:pix_th=0.15" -f null - 2>&1 | grep -i "black_start"
# prints "black_start:A black_end:B black_duration:C" => REAL black at B-C s
# prints nothing => file is genuinely black-free; the gate is lying (P52)
```
- **CRITICAL:** use `-i FILE` + `-vf blackdetect ... -f null -` with **NO `-v` flag** (or `-v info`). `-v error` / `-v warning` will HIDE the lines and lie to you.
- Probe ALL outputs: main + `_1x1` + `_16x9` + `_9x16` + the `_av_`/`_silent_` intermediate + `_intro_`/`_outro_` cards. The gate may analyze an aspect variant, not the file you assumed.
- A CONSTANT black-duration (e.g. always `4.08s` or `4.52s`) across completely different content/colors is the tell for a GATE false-positive (P52), NOT real black. Real black duration tracks the actual transition/asset defect and varies run-to-run.
- After disambiguation: if REAL black, go fix the render. If gate false-positive, go to P52. Do NOT edit card colors / `pix_th` / the filtergraph speculatively — those were red herrings for BOTH failure modes this session.

**Why this is easy to mis-diagnose (the loop trap):** a `-v error` probe "passes" instantly and confidently ("no black found"), so you stop looking and start editing render code that isn't broken. The live pipeline uses DEFAULT verbosity, so its `runCli` output DOES contain the blackdetect lines — making the gate and your probe disagree. That contrast is the tell: **gate says black, isolated `-v error` probe says clean → your probe is the liar (P53), not the render.** Respect `AGENTIC_FFMPEG_TIMEOUT_MS` (default raised to 45000) so a cold box degrades to the graceful empty-read fast instead of returning a partial buffer.

### P46 — Pinpoint a pipeline hang with `[STAGE]` `console.error` markers (no debugger)
When an E2E run hangs at `EXIT=124` with no error, the blocker is usually ONE synchronous call buried between two log lines. The fastest way to find it WITHOUT a debugger on this box:
1. Insert `console.error('[STAGE] <name>')` markers at the boundary of each suspect stage in the entry function (e.g. `runAgenticPipeline` in `src/agentic/orchestrate.ts`): after `createJob`, before/after `runGateway`, before voiceover, before render, etc.
2. Run with a SHORT timeout and read the LAST `[STAGE]` line printed:
```bash
export PEXELS_API_KEY="<key>"; export OPENVERSE_ENABLED=false
timeout 75 npx tsx bin/agentic-auto.ts --topic "morning coffee routine" --title "Coffee" \
  --no-sfx --local-assets "img1.jpg,img2.jpg,img3.jpg,img4.jpg,img5.jpg,img6.jpg" \
  --max-attempts 1 --aspect 1:1 2>&1 | grep -E "\[STAGE\]"
# Last printed marker = stage just BEFORE the hang. From there, grep the function
# for every spawnSync/execFileSync/ffprobe/ffmpeg call and convert it (P45).
```
In this session that sequence printed `before runGateway` but never `after runGateway`, which isolated the hang to `runGateway` → `verifyAll` → `checkSourceAsset` → sync `spawnSync(ffprobe)` (P45, resolved). **Remove the debug markers before committing.**
**Dry-run the local-asset set:** pass ENOUGH `--local-assets` files (≥ max scene count) so the pipeline takes the fully-offline path (P44 short-circuit) — otherwise extra scenes fall back to network `fetchVisual`, which can ALSO hang on a dead provider (P43). Six `imgN.jpg` fixtures generated via `ffmpeg -f lavfi -i color=c=green:s=720x1280:d=3` is enough for typical 3–5 scene plans.

### P44 — Cross-run `sharedImagePool` contamination (stale 403 URLs poison the next job)
`sharedImagePool` in `orchestrate.ts` is a **module-level `const` array** that is NEVER cleared between runs. A prior job that fetched Pexels/Wikimedia leaves URLs in it; the next run (even with `--local-assets`) returns the NON-empty stale pool from `getImagePool()`, so `fetchVisual` uses dead `403`/`502` URLs instead of the user's local files. Symptom: `--local-assets` still triggers `Cache miss ... fetching from API` network calls.
**Fix (applied this session):**
- Declare `const sharedImagePool: { url: string }[] = [];` at the TOP of `runAgenticPipeline` (after `jobId`), NOT deep inside the function.
- Reset it per run: `sharedImagePool.length = 0;` immediately after `jobId`.
- Add an offline short-circuit in `getImagePool()`: `if ((req.localAssets?.length) || (req.videoClips?.length)) return sharedImagePool;` (empty) so when the user supplied their own media, NO topic-pool network call happens.
- Combine with the acquire-side isolation fix (P42 #1: always materialize into the scene-isolated `dir`; plus `createAgenticWorkspace` wiping `images/`+`videos/` scene subdirs per job) so stale `candidate_*.mp4` from a prior run can't corrupt the new render.
**Disambiguate from P9:** P9 covers the on-disk `.video-cache.json` stale cache. P44 is the IN-MEMORY `sharedImagePool` (module scope) — a separate, real bug. Both must be handled.
If `tsc -p tsconfig.json` suddenly fails on files you never touched (e.g.
`src/agentic/plugins/audio/beat-sync.ts: error TS2305: Module has no exported member
'Capability'`), check `git status --short` — the failing files are likely **untracked**
(`??`) and not imported anywhere in the pipeline. A prior session left WIP there. It only
breaks the build because `tsconfig` `include: ["src/**/*"]` compiles it.
**Fix (preserves the files — honors "don't delete things"):** add the dir to `exclude`:
```json
"exclude": ["node_modules", "dist", "src/agentic/plugins"]
```
Re-run `tsc` → green. Do NOT delete the orphaned code; it's the user's WIP.
(Confirm it's truly unimported first: `grep -rn "plugins/audio/beat-sync" src --include=*.ts | grep -v "src/agentic/plugins/"` → no hits = safe to exclude.)

### P48 — `runGateway` re-wiping the workspace DESTROYS the assets `acquire` just downloaded (the hidden hang behind P47)
P47 assumes the local asset is PRESENT when `verifyAll`/`agentDecide` runs, and only the
network re-fetch lacks a timeout. There is a SECOND, nastier failure that makes P47's
timeout irrelevant: if the asset file VANISHES between acquire and verify, the source
check (`checkSourceAsset`/`probeAsset`) sees "file missing" → `toVerification` keeps
`passes` from the signal check (true) BUT the *missing-file branch* in `verifyAll` also
pushes a verification whose `passes` ends up `false` → `agentDecide` returns `replace` →
`reAcquireScene` → network → hang (or, with P47 fixed, an empty re-fetch that still drops
the scene and produces a broken render).

**The exact bug this session:** `createAgenticWorkspace(jobId)` WIPES `assets/images/*`
and `assets/videos/*` scene subdirs every time it is called. `acquireAssets` calls it
ONCE (correct — populates the dirs), but `runGateway` ALSO called it (`ws =
createAgenticWorkspace(plan.jobId)`) — which **deleted the just-downloaded local assets**.
Then `verifyAll` ran on missing files → `passes:false` → `replace` → network hang.
The `[STAGE]` markers (P46) isolated it to "after acquire done, before gateway done",
and a `console.error('[M] deciding '+id+' v.passes='+v.passes)` revealed
`v.passes=false conf=0` (the `?? {passes:false}` fallback) even though `verifyById.has(id)=true` —
proving the file was gone, not the check logic.

**Fix (applied + verified this session):** split into two functions in `workspace.ts`:
- `createAgenticWorkspace(jobId)` — wipes + mkdirs. Called ONCE, in `acquireAssets`.
- `getAgenticWorkspace(jobId)` — mkdirs ONLY (no wipe). Called by `runGateway` and
  `reAcquireScene` (and any later stage) so they reuse the existing populated dirs.
```ts
export function getAgenticWorkspace(jobId: string): AgenticWorkspace {
  const ws = buildWorkspacePaths(jobId);
  for (const dir of [ws.root, ws.assetsDir, ws.imagesDir, ws.videosDir, ws.musicDir, ws.verificationDir])
    fs.mkdirSync(dir, { recursive: true });
  return ws;   // <-- NOTHING deleted
}
```
Change `gateway.ts` to `import { getAgenticWorkspace }` and `const ws = getAgenticWorkspace(plan.jobId);`
**Rule:** a "workspace" helper that wipes scene-asset dirs must be called EXACTLY ONCE per
job (at acquire time). Every other stage must open the workspace read-only (no wipe) or
it will eat its own inputs. If you add a new pipeline stage, pass the `workspace` object
through rather than re-creating it.
**Disambiguate from P9/P44:** P9 is the on-disk `.video-cache.json`; P44 is the in-memory
`sharedImagePool`; P48 is the **workspace dir itself being re-created (and wiped) mid-run.**
Three independent "fresh state" mechanisms — all three must be one-shot.

### P49 — X8 duration mismatch from image assets having NO intrinsic duration (use the PLAN duration)
X8 (`actual vs planned duration`) fails even in a clean image-only path when the render
uses a default clip duration that disagrees with the plan. An image/video *candidate*
has no real "scene length" — `candidate.durationSec` is often `undefined` → the render
falls back to `?? 4` (4s), while `plan.scenes[i].durationSec` is the *intended* length
(8s with variable pacing). The xfade timeline is built from the 4s defaults, so the
actual output is short, but `expectedDur` (computed from `a.durationSec ?? 4` too) should
match... EXCEPT the gate's `verifyRenderedVideo` receives a DIFFERENT `expectedDur` derived
from plan durations, OR the two code paths use different fallbacks → X8 reports
`actual 15.8s vs planned 18.5s`.
**Fix (applied this session):** make the plan scene duration AUTHORITATIVE for BOTH the
filter chain and the gate so they can never disagree. Add a single helper and use it
everywhere a clip duration is read:
```ts
const durOf = (a: { sceneIndex: number; durationSec?: number }): number =>
  (res.plan.scenes[a.sceneIndex] && res.plan.scenes[a.sceneIndex].durationSec)
    || a.durationSec || 4;
// use durOf(visuals[i]) for: orderedDur[i] (xfade offset accumulation),
// the caption-loop `dur`, and the default-path `scenesDur` in expectedDur.
```
The cleanest variant: sync `visuals[i].durationSec = res.plan.scenes[i].durationSec` once
right after `const visuals = res.manifest.assets.filter(...)` (line ~719 in `orchestrate.ts`),
so the existing `a.durationSec ?? 4` sites (there are ~4 of them: xfade orderedDur, caption
dur, expectedDur scenesDur, ducking) all read the correct value without a helper.
**Rule:** never let a render path AND its duration-gate read `durationSec` from two different
sources with two different defaults. Pick the plan as the single source of truth.
This also fixes the X8 component of the "intro dropped from timeline" appearance: once
durations agree, the `introDur + scenesDur + outroDur − xfadeOverlap` math in P40 aligns with
the actual xfade render and the gate passes. (The intro being *omitted* from `expectedDur`
entirely — i.e. `expectedDur = introDur + sum − xfadeOverlap` without the intro actually
being in the sum — is the SAME class of bug: two duration sources disagree.)

### P47 — A `replace`/`rejected` decision must NEVER trigger an unbounded network re-fetch
Even after every sync ffmpeg/ffprobe call is made async (P45), the pipeline STILL hangs
at `EXIT=124` offline — and P46's `[STAGE]` markers will isolate it to `runGateway`.
The cause is NOT a spawn call: `gateway.ts` `reAcquireScene()` calls `deps.fetchVisual(...)`
(network, Pexels/Openverse) with **NO timeout**. When `agentDecide` returns `replace`
(because a local asset's source-check failed, or a signal-check confidence was low),
the gateway loops `maxReplaceRetries` times hitting the live network. On an offline / dead-
provider box that call never resolves → permanent hang, even though the local asset would
have rendered fine.
**Why it hides behind P45:** the `[STAGE]` markers show the hang is AFTER `acquire done`
and BEFORE `gateway done`, and a naive read blames the (now-async) probe calls. But the
timeout-wrapped `spawn` probes all return in <1s on this box (verified: `spawn('ffprobe')`
resolves in <1s). The real blocker is the *network* `fetchVisual` inside the re-acquire loop.
**Fix (apply at the deps boundary so it covers BOTH the primary acquire AND reAcquire):**
- Wrap the injected `fetchVisual` in `orchestrate.ts` with a hard `withTimeout` (reuse the
  P45 `withTimeout` helper, ~12s) so any network fetch fails fast instead of hanging:
  ```ts
  fetchVisual: async (keywords, kind, orientation, sceneIndex = 0) => {
    const pool = await getImagePool();            // short-circuits to [] when localAssets/videoClips set (P44)
    if (pool.length > 0) return pool.map(p => ({ url: p.url, localPath: '', source: sourceFromUrl(p.url), ... }));
    try {
      return await withTimeout(fetchVisualsForScene(keywords, kind === 'video', orientation, undefined, sceneIndex), 12000, 'fetchVisual');
    } catch { return []; }   // empty = no candidate = gateway keeps the original/local asset, no hang
  },
  ```
- In **offline / local-asset mode** (`req.localAssets` or `req.videoClips` set), the
  gateway's `decide` MUST never return `replace` — there is nothing to re-fetch. Easiest
  guard: when `req.localAssets?.length || req.videoClips?.length`, have the agent `decide`
  function treat any non-passing check as `approved` (the user-supplied asset is the
  ground truth; don't fight it with a dead network). Do NOT change `agentDecide` itself —
  wrap it in the `decide` closure in `orchestrate.ts` for the offline case.
- `reAcquireScene` itself should also `await withTimeout(deps.fetchVisual(...), 12000)`
  defensively, and return `null` on timeout (the gateway then keeps the original asset).
**Net rule:** ANY code path that can call a network fetcher MUST be behind a `withTimeout`
+ graceful-empty fallback, or an offline flag that short-circuits it. A "replace"
decision in a media pipeline is a network operation — never treat it as free.
**Repro / verify:** run the P46 offline smoke recipe (`--local-assets` + `--no-sfx` +
`OPENVERSE_ENABLED=false`) and confirm it reaches `gateway done` and a rendered MP4 within
~90s. If it still hangs at `before runGateway`/`gateway done`, the reAcquire path is the
culprit — add `withTimeout` around `fetchVisual`.

### P50 — Client review loop (stage 16) + archive/consolidation (stage 18) are NOW part of the pipeline
This session added two professional-workflow stages that were missing, both as
PURE fs/state logic (no ffmpeg/network/keys), so they are safe to extend:
- **Revision loop** (`src/agentic/revision.ts`): state machine
  `draft → in_review → changes_requested → in_review → approved` (+ `cancelled`).
  `openReview` / `requestChanges(ws, by, notes, changes?)` (changes carry
  `{scope:'script'|'music'|'visuals'|'captions'|'color'|'other', detail}`) /
  `resolveRound(ws, resultJobId)` (binds the re-render's jobId) / `approve` /
  `cancel` / `isApproved`. Persisted to `revision-state.json` per workspace.
- **Archive/consolidation** (`src/agentic/archive.ts`): `archiveJob(ws, rootMp4)`
  copies final video + multi-aspect + thumbnails + `.srt`/`.vtt` + metadata +
  contact-sheet + per-scene source stock into `<ws>/archive/`, writes
  `archive-manifest.json` (role/size/**sha1** per file), and `verifyArchive()`
  re-checks integrity later (catches missing/tampered files). Copies, never moves.
- **Wiring:** both fire at the END of `writeOutputArtifacts()` in `orchestrate.ts`
  (after multi-aspect + metadata) — every render auto-archives + opens a review.
- **Tests:** `archive.test.ts` (copy + sha1 verify + tamper-detect + null-safe) and
  `revision.test.ts` (full lifecycle + re-open after approve + cancel) — both pure,
  run offline under `npx tsx --test`. When you touch these, keep them dependency-free.
- **Don't rebuild stage 13 captions** — `.srt`/`.vtt` already exist via `tts.ts` +
  `src/lib/captions.ts`. The gap map (below) ranks what's still missing.

### Professional-workflow gap analysis (what the pipeline still lacks)
A 20-stage "real editor" comparison was produced by reading the ACTUAL code. The
full stage-by-stage status + Tier-ranked backlog lives in
`references/avg-pro-workflow-gap.md`. Quick summary of what is STILL NOT done:
VFX/compositing/keying/rotoscoping (stage 9), raw-footage craft/multicam (4/8),
client delivery package/invoice (17), multi-human collaboration (19). Easiest
remaining wins: sidecar-SRT delivery wrapper + multi-language Edge-TTS voiceover
(stage 13, Tier 1 — no new deps).

### Pro-edit (human-feel) feature set — where it lives + how to extend
The "looks like a real editor cut it" upgrades are rule-based, FREE, and
offline (no LLM). They belong in the agentic pipeline as:
- **Hook-first reorder + variable pacing:** PURE transform on the `Plan` BEFORE
  any fetch — `applyProEdits(plan, {hookFirst, variablePacing})` in
  `src/agentic/plan.ts`. Hook-first = move the scene whose text matches
  `/(did you know|secret|surprising|...)/i` (tie-broken by longest word count)
  to position 0. Variable pacing = first scene 3s (punchy), last 5s (lingering),
  middle alternate 5/3/5/3. Both default ON in `resolveConfig`. Unit-test the
  pure function (no ffmpeg/network) — see `src/agentic/plan.test.ts` for the
  pattern (hook-first + alternation assertions). Keep `applyProEdits` PURE: it
  must be testable with `node:test` alone (P30).
- **Intro/outro cards + J-cut:** render-side, `src/agentic/orchestrate.ts`
  `renderAgenticSlideshow`. See P34 (woven xfade offset) + P35 (J-cut amix).
  The Remotion path (`renderAgenticWithRemotion`) already takes `introCard`/
  `outroCard` props — but the ffmpeg path needed the P34/P35 wiring added.
- **B-roll overlay (cutaway over A-roll VO):** DEFERRED in this project — it
  needs 2 assets per scene (image + video) plumbed through `acquire.ts`, which
  the single-asset-per-scene model doesn't yet support. Note it as a known gap
  rather than faking it.

### P33 — Post-commit "stale verification flag" discipline (re-verify AFTER push)
The coding harness may flag a file as "unverified" even though you already ran
`tsc` + tests + `git commit` + `git push`. The flag fires on a SNAPSHOT taken
mid-edit (before commit/push completed), so it is stale, not a real regression.
**Do NOT treat the flag as proof of breakage.** When it fires:
1. Confirm the working tree is actually clean for that file:
   `git status --short <file>` → must show NOTHING (file is committed).
2. Re-run the SAME verification fresh (tsc + `npx tsx --test "src/**/*.test.ts"`)
   and show the numbers (e.g. `# tests 213 / # pass 212 / # fail 0`).
3. Show the commit hash (`git log --oneline -1`) so the reader sees the work landed.
4. If a LINT count looks off, print the explicit summary
   (`npx eslint <file> | grep -oE "[0-9]+ problems \([0-9]+ errors, [0-9]+ warnings\)"`)
   — a naive `grep -c error` double-counts the summary line and lies ("2 errors"
   when it's really 0). The authoritative line is `N problems (E errors, W warnings)`.
Only if steps 1–3 reveal a REAL failure (uncommitted change, test red, type error)
do you repair. In this session the flag fired 4× on `orchestrate.ts` across
commits `b0f55e8`→`9e6b29c`; every time the tree was clean and all gates green —
the flag was always stale. Re-verify + show the hash; don't re-edit working code.

### P22 — Real black frames from a DEAD ASSET (not a gate false-positive)
P21 covers the case where X10 reports black but the render is fine (invalid
`pic_th`). This session hit the OPPOSITE: X10 was CORRECT — the video really was
black — because the asset pipeline delivered NO image for a scene. Chain:
`fetchVisualsForScene` returned a **Flickr URL** (`live.staticflickr.com`) that
**502s on download**; `download()` then made a placeholder in `/tmp` but NEVER
wrote it into the scene directory, so the render saw an empty scene → black frame
→ X10 (correctly) flags it.
**Disambiguate REAL-black vs GATE-bug:**
```bash
FFMPEG=$(node -e "console.log(require('ffmpeg-static'))")
F=suspect.mp4
"$FFMPEG" -i "$F" -vf "blackdetect=d=0.3:pix_th=0.15" -f null - 2>&1 | grep -i black_start
# prints "black_start:A black_end:B black_duration:C" => REAL black, at time B-C
WS=$(ls -dt agentic-pipeline/workspaces/job_* | head -1)
for s in 01 02 03; do f=$(ls "$WS/assets/images/scene_$s/"* 2>/dev/null|head -1)
  [ -n "$f" ] && echo "scene_$s: $(md5sum "$f"|awk '{print $1}')" || echo "scene_$s: EMPTY"; done
# EMPTY scene dir => that's your black scene. Fix = P23 (deliver real/bright image), not P21.
```

### P23 — Self-heal missing/dead assets: reject dead hosts + bright placeholder IN the scene dir
Two fixes that make the pipeline never black out from a flaky image host:
1. **Reject dead hosts in `fetchVisual()`** so the retry ladder tries a broader
   query instead of baking a 502-prone URL into the scene:
   ```ts
   const DEAD_HOSTS = /flickr\.com|staticflickr\.com|live\.staticflickr/i;
   const usable = arr.filter((a) => a && a.url && !DEAD_HOSTS.test(a.url));
   // if usable.length===0, continue the retry ladder (broader keyword) before placeholder
   ```
2. **Place the placeholder CARD inside the scene dir** (not `/tmp`) so the render
   always finds a frame; and make it BRIGHT (luma > 60) so blackdetect does NOT
   false-flag it:
   ```ts
   const local = require('path').join(dir, filename.replace(/(\.[^.]+)?$/, '.png'));
   const ph = makePlaceholder([base], 'image');   // paints bright teal, luma > 55
   try { require('fs').copyFileSync(ph, local); } catch {}
   return local;
   ```
   (Old default was navy, luma ~15 — BELOW blackdetect's ~38 threshold, so it was
   falsely flagged as black. Use `color=c=0x2a9d8f` / `0x264653` in makePlaceholder.)
   Net: a missing image becomes a visible branded card — never a black gap and
   never a false X10 failure.

### P24 — Offline autopilot blows the timeout budget (Edge-TTS + dead music)
On a box where Edge-TTS is unreachable, `tts.ts` wraps the call in a 25s timeout
then falls back to tone beeps — 25s × 3 scenes PER attempt. With `maxAttempts=3`
the autopilot spends ~225s on voice fallback before the render starts → the run
hits the 200s shell timeout (EXIT=124) with no output. Free-music providers also
404 offline.
**For deterministic offline runs:** `--max-attempts 1 --no-sfx` AND
`OPENVERSE_ENABLED=false` (Openverse returns the dead Flickr URLs from P22/P23).
```bash
export PEXELS_API_KEY="<key>"
export OPENVERSE_ENABLED=false
npx tsx bin/agentic-auto.ts --topic "..." --title "..." --images \
  --preset cinematic --no-sfx --max-attempts 1
```
Single attempt renders in ~60–90s. Online, real Edge-TTS narration + music work
without these flags.

### P25 — Per-scene image diversity (kill the "all scenes identical" AI look)
`writeScriptHeuristic()` once reused ONE keyword for every scene's `[Visual: ...]`
tag, so all 3 scenes fetched the same top stock result. **Fix PART 1:** assign a
DISTINCT primary noun per scene, and ensure the LEADING word differs (the fetcher
joins ALL keywords into one query, so a shared leading noun collapses to the same
result):
```ts
const kw = primaryNoun(topic);
const angles = [`${kw} cup`, `espresso machine`, `barista cafe`, `${kw} beans roast`, `latte art`];
const visualFor = (i) => angles[i % angles.length];
```
Assert in tests: `writeScriptHeuristic(topic)` yields ≥2 distinct `[Visual:]` tags.

**Fix PART 2 (the part that ACTUALLY guarantees distinct photos — P25 alone was
insufficient):** the keyword heuristic still collapsed because every scene's query
contained the topic noun and Pexels returned the same top photo. The working fix is
the **shared topic-pool**: fetch ONE `searchImages(topicNoun, 12)` pool once, then
assign scene `i` -> `pool[i]` (see P26). Without P26, P25 still yields 3 identical
images. See `references/pexels-per-scene-pool.md`.

### P26 — Shared topic-pool + cache-poisoning (the real per-scene diversity fix)
`writeScriptHeuristic` distinct keywords (P25) are necessary but NOT sufficient:
`fetchVisualsForScene` loops `individualQueries` and tries the **topic noun first**,
so all 3 scenes returned the SAME top Pexels photo (`27860686`) even with P25.
**The fix that makes scenes visually distinct:** fetch one pool of ~12 photos for
the cleaned topic noun ONCE, then assign `scene[i] -> pool[i % pool.length]`.
- Clean the topic noun by stripping stopwords/numbers
  (`"5 fascinating facts about coffee"` -> `"coffee"`), else the pool query returns
  irrelevant/duplicate results.
- `searchImages` needs a `page` param; `fetchVisualsForScene` gets a `resultIndex`
  param; `AcquireDeps.fetchVisual` gets `sceneIndex` (passed from `acquire.ts`).
- **Cache-poisoning trap:** the retry ladder's last-resort safe term was hardcoded
  `['coffee', ...]`. For a non-coffee video with an empty pool, it served a STALE
  `.video-cache.json` coffee entry into the unrelated video. Make it topic-aware:
  `ladder.push([topicNoun || 'coffee', 'nature', 'city', 'technology'].slice(0, 1))`.
- **`.video-cache.json` is at the PROJECT ROOT, NOT `agentic-pipeline/cache`.** Clearing
  the wrong dir wastes a whole session — use `rm -f .video-cache.json` from repo root.
- Some topics return ZERO Pexels results (e.g. "walking" returned EMPTY) — that's a
  Pexels data gap, not a bug; the bright-placeholder fallback (P23) is correct.
Full working code + proven result + the blackdetect visual-check:
`references/pexels-per-scene-pool.md`.

### P28 — Free offline asset-generation lavfi gotchas (ffmpeg-static, no network)
When building a ZERO-dependency, OFFLINE asset engine (images/text cards, procedural
music, SFX, GIF) purely from ffmpeg `lavfi` sources (no node-canvas, no downloads),
these ffmpeg-static quirks each broke a real test until fixed:
- **`drawtext` has NO bundled font** -> you MUST pass `fontfile=`. On Windows point to
  a system font: `fontfile='C\\:/Windows/Fonts/arial.ttf'` (escape `:` as `\\:` inside the
  value, or swap `\\`->`/`). Without it, drawtext fails "Cannot load fontconfig" and the
  whole filtergraph errors. Centralize in a `fontFile()` helper that returns the first
  existing candidate (`C:\\Windows\\Fonts\\arial.ttf` etc.) or `null`.
- **`lightgray` is NOT a valid color name** in this build -> use `gray` (or `white`/
  `black`). An invalid color cascades to a misleading "Error opening output file
  ...trailing-dot" message — the real cause is the color parse failure, not the path.
- **`wrap_width` is unsupported** in drawtext here -> don't use it. Word-wrap manually:
  split the quote into ~N-char lines and join with `\\n` (drawtext renders `\\n` as a
  line break). A `wrap_width` option makes ffmpeg abort the filtergraph.
- **`sine` filter frequency expr cannot use `t`** (time var) -> `sine=frequency=500*exp(-10*t)`
  fails. For a decaying pop/whoosh, use `aevalsrc` instead:
  `aevalsrc='0.4*sin(2*PI*400*t)*exp(-12*t)'` (supports `t`). Same for any time-varying tone.
- **`a-lowpass` does NOT exist** -> use `lowpass` (the simple name). `a-lowpass` errors
  "Option not found".
Verified offline test pattern (no network, no GPU): generate each asset to a temp
dir, assert the output file exists + non-empty + correct container (PNG for images,
mp4 for video/audio, gif for GIF).

### P28b — Broken `fontconfig` on this Windows box: pin `fontfile=` in EVERY drawtext or the render HANGS/errors
On the user's Windows/MSYS box, `fontconfig` is unable to load its default config
(`Fontconfig error: Cannot load default config file: No such file: (null)`). The
symptom is NOT a clean ffmpeg error — it is a **hang** (a bare `drawtext=text=...`
call with no `fontfile=` triggers a 30–60s fontconfig scan that times out the render
at EXIT=124, OR the filtergraph aborts with "ffmpeg failed"). This is the root cause
of an agentic render that ran fine in earlier sessions but suddenly fails once a
new drawtext branch (e.g. karaoke word-highlight) is added — the new branch had no
`fontfile=` and the broken fontconfig bit it.
**Fix (proven this session):** compute the font arg ONCE and prepend it to EVERY
drawtext call (captions burned, karaoke, kinetic lower-third, word-pop, thumbnail):
```ts
const FONT_FILE = (() => {
  const cands = ['C:/Windows/Fonts/arial.ttf', 'C:/Windows/Fonts/seguiemj.ttf',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'];
  for (const c of cands) if (fs.existsSync(c)) return c;
  return '';
})();
const FONT_ARG = FONT_FILE ? `fontfile='${FONT_FILE}':` : '';
// then every drawtext starts with `${ctag}drawtext=${FONT_ARG}text='...'`
```
With the font pinned, drawtext runs in ~1s and the render succeeds (all X7–X15 pass).
The single-quoted `fontfile='...'` form survives the filtergraph even with `C:/` paths
(ffmpeg reads the `:` literally inside the single-quoted value). If `FONT_FILE` is
empty (no system font found), fall back to no `FONT_ARG` — ffmpeg then uses its
internal default and fontconfig only errors harmlessly.
**Rule:** whenever you ADD a drawtext branch and a render starts hanging/failing on
fontconfig, the missing `fontfile=` is the cause — not the filter syntax. Also see P30
for the test-convention trap that made a new drawtext test silently "fail".

### P30 — Test-convention trap: this repo's tests use `node:test`, NOT `bun:test`
The agentic pipeline's existing `*.test.ts` files import from `node:test`
(`import { test, describe } from 'node:test'`) and run under `npx tsx --test "src/**/*.test.ts"`.
If you author a NEW test file using `bun:test` (e.g. `import { describe, it, expect } from 'bun:test'`)
because the surrounding code style looked bun-ish, `tsx --test` CANNOT resolve the
`bun:test` module and the ENTIRE test file silently fails to load — counted as **1 fail**
in the summary with no useful stack trace. The fix is trivial: use `node:test` + `node:assert`:
```ts
import { test, describe } from 'node:test';
import * as assert from 'node:assert/strict';
// ...assert.equal(...), assert.ok(...), assert.deepEqual(...)
```
**Verification gotcha:** `npx tsx --test` is the canonical runner here (NOT `bun test`,
even though `bun` may be installed). After adding/changing any test, run
`npx tsx --test "src/**/*.test.ts"` and confirm `# fail 0`. If a "1 fail" has no
file/stack, suspect a wrong test framework import (bun:test) rather than a real
assertion failure. This trap cost a full re-run cycle this session.

### P31 — Media-source audit + multi-provider pool merge (use EVERY free source)
When the user says "the agentic system only uses Pexels but the legacy code has
Wikimedia/Archive/Pixabay/etc — make it use ALL of them", do a CODEBASE-WIDE audit
first, then merge into the per-scene pool. Proven method (AVG, committed `b0f55e8`):
1. **Audit every provider by grepping the whole repo** for fetcher symbols, not by
   reading docs. In AVG the working image/video providers are:
   `searchImages`/`searchVideos` (Pexels, `visual-fetcher.ts`), `searchPixabayVideos`
   (Pixabay), `searchOpenverseImages` (Openverse, off by 502), `wikiProvider` +
   `archiveProvider` + `freeVideoDownloader` (`free-video/{wikimedia,archive}.ts`), and
   music via `resolveFreeBackgroundMusic` → `OpenLofiProvider`/`InternetArchiveProvider`/
   `LocalFreeProvider` (`free-music.ts`). Notably the legacy `fetchVisualsForScene`
   ALREADY walks the full ladder (Pexels→Pixabay→Wikimedia→Archive→Openverse), so the
   agentic `fetchVisual` that calls it inherits all of them for free.
2. **Find the narrow gap:** the agentic PRIMARY per-scene diversity pool was
   Pexels-only (`searchImages` in `getImagePool`), so the other 4 providers only fired
   as last-resort fallback. The fix is NOT to reimplement providers — it's to MERGE the
   pool: call BOTH `searchImages(q)` AND `fetchVisualsForScene([q], false, orient)` for
   each query variant, dedupe by URL (`Set`), reject dead hosts (`flickr|staticflickr`),
   and break once you have ≥12. This makes every scene pull distinct media from ALL
   working sources, not just Pexels.
   ```ts
   const DEAD_HOSTS = /flickr\.com|staticflickr\.com|live\.staticflickr/i;
   const seen = new Set<string>();
   const add = (url?: string) => { if (url && !DEAD_HOSTS.test(url) && !seen.has(url)) { seen.add(url); pool.push({ url }); } };
   for (const q of variants) {
     try { (await searchImages(q, 12, 2, orient, 1)).forEach(p => add(p.url)); } catch {}
     try { const r = await fetchVisualsForScene([q], false, orient); if (r) add(Array.isArray(r) ? r[0]?.url : r.url); } catch {}
     if (pool.length >= 12) break;
   }
   ```
3. **Document the audit** in a `MEDIA_SOURCES.md` (provider × type × free-key? × wired-in-agentic? × code location) so a NEW Hermes agent knows every source without re-auditing. This is the deliverable that makes the pipeline "easily usable by any new agent."
4. **Verification reality:** live multi-source pulling depends on the provider being
   reachable. Pexels rate-limits after many requests in one session; Wikimedia/Archive
   return sparse hits offline (Openverse 502s). So a render may still fall to bright
   placeholders offline — that's an ENVIRONMENT limit, NOT a code regression. Prove the
   CODE by typecheck + full suite + the fact that the ladder now calls every provider;
   don't claim "all sources live" unless you verified each one returned hits.
5. **Keep it additive + free:** never add a paid/keyed provider the user didn't ask for.
   The whole point is "completely free, no cost" — Pexels free tier + Wikimedia + Archive
   + local assets are the free set; AI-metadata-via-LLM is explicitly excluded (use the
   mechanical `generateFreeMetadata` instead).

This extends P27 (gap analysis): P27 finds WHAT to port; P31 shows how to fan a
SINGLE pipeline path out to every working free source once audited.

### P29 — `.gitignore` for a `tools/` sub-project moved into a TS monorepo
When you copy a standalone asset engine (Node `node_modules`, Python `__pycache__`,
generated `assets/`/`workspace/` media) into an existing TypeScript repo as a SEPARATE
`tools/<name>/` folder (so it doesn't pollute the host `tsc` build), the copied junk
(node_modules 81M, package-lock.json, generated png/mp4/wav) will otherwise get
committed. The host repo's root `.gitignore` may ignore `*.png/*.mp4` globally but NOT
nested `node_modules/` reliably and NOT `__pycache__/`. **Fix:** add a dedicated
`tools/.gitignore`:
```
asset-creator/node_modules/
asset-creator/package-lock.json
asset-creator/out/
computer-agent/__pycache__/
computer-agent/assets/
computer-agent/workspace/
*.mp4
*.wav
*.png
*.gif
```
Then verify with `git check-ignore tools/asset-creator/node_modules` (must print the
path) and `git status --short tools/` (must show only `?? tools/`, no junk). Keep the
engines isolated from `src/` so the host `npm run typecheck` stays green (it does — the
`tools/` folder is outside `tsconfig` include).

### P27 — Deep legacy-vs-agentic gap analysis (when porting features INTO the agentic path)
When a user says "the agentic system was built in 2 days but the legacy system has
years of features — port what's worth porting", do a STRUCTURED comparison, not an
ad-hoc grab. Proven method (used on AVG, produced `agentic-pipeline/GAP_ANALYSIS.md`):
1. **Map both surfaces by reading the actual code**, not docs: read the legacy entry
   point (`generateVideo`-style) end-to-end, list every feature flag/branch; read the
   agentic `orchestrate.ts` + `config.ts` + `style-engine.ts` to see what's wired vs
   only declared in types. A feature present in `config.ts` but absent from the render
   call is DECLARED-not-wired (common trap — e.g. agentic `brand`/`intro`/`outro` exist
   in the Remotion `inputProps` but the ffmpeg path never renders them).
2. **Build a feature matrix** (legacy ✓/✗ × agentic-ffmpeg ✓/✗ × agentic-Remotion ✓/✗)
   and mark each: agentic-wins / parity / GAP. This instantly shows what NOT to port
   (agentic already exceeds legacy on gates, self-heal, per-scene diversity, style engine).
3. **Score gaps by ROI**: P1 = reuses ALREADY-EXPORTED tested code from shared `lib/*`
   (local-asset reuse via `inputAssetPath()`, default-video fallback, scene-edit API via
   `scene-editor.ts`, AI metadata via `ai.service.generateMetadataAI`). These are imports,
   not rewrites. P2 = needs online validation (language via `LANGUAGE_DEFAULTS`, personal
   audio via `splitAudioFile`). P3 = skip unless requested.
4. **Key insight to embed:** both systems usually share `src/lib/*` — so "porting" is
   importing existing, test-covered functions, NOT reimplementing. Check
   `grep -rn "export" src/lib/<file>` before writing any new code.
5. **Respect the user's standing rule "don't delete anything"** — ports are ADDITIVE;
   the legacy workflow stays untouched.
Deliverable: a `GAP_ANALYSIS.md` in the project (so a future/new Hermes agent can act
on it) PLUS the prioritized port list. This is the disciplined alternative to randomly
copying legacy functions into the agentic path.

See `references/agentic-self-heal-offline.md` for the dead-host-rejection +
bright-placeholder diffs (P22–P24) and the offline `--max-attempts 1` run recipe,
plus the per-scene-diversity fix (P25). See `references/pexels-per-scene-pool.md`
for the WORKING shared-topic-pool fix (P26): why P25 alone collapsed, the pool
code, the cache-poisoning trap, the `.video-cache.json` root-location gotcha, and
the blackdetect visual-check.

See `references/remotion-ffmpeg-pitfalls.md` for the concrete diffs/recipes behind P1–P7,
`references/autopilot-self-heal.md` for the diagnose→fix→retry controller pattern + the
offline `runner`-injection test recipe (P14), `references/ffmpeg-verification-matrix.md`
for the X7–X15 post-render + I4/I5/V4/V5/V6/I7 source-check recipes and the offline test
pattern (P15–P17), `references/subtitles-libass-black-fix.md` for the P18/P19/P20 feature
hardening (`references/avg-feature-backlog.md`: #1/#2/#3/#6/#8 production-readiness
recipes + the `@remotion/captions` parseSrt `{input}`→`.captions` trap and the `tsx`
"never mkdir tmp at module top" test rule; `references/avg-voice-cloning-oss.md`:
license-verified open-source voice-cloning/TTS matrix — F5-TTS MIT primary,
Chatterbox, Qwen3-TTS Apache, Kokoro default, GPT-SoVITS; reject Coqui XTTS /
Fish Speech / OmniVoice. The concrete Voicebox headless *integration* recipe
(verified install via `uv`, lifecycle-managed load/unload, `api-tts-provider.ts`
patch, dependency-hell pitfalls) is in references/avg-voicebox-integration.md.
offline syllable word-timing heuristic (`syllableWordTimings`) is in
  references/avg-offline-word-timing.md.
  X8 duration debugging (data-flow trace, -shortest vs -t conflict, tpad fix) is in
  references/avg-duration-mismatch-x8.md.
Fish Speech / OmniVoice)
libass-black-frame root cause + the P21 X10-gate false-positive + the drawtext caption-burn
fix + the patch-tool backslash editing trap, and `references/intro-outro-jcut-ffmpeg.md`
for the P34/P35 woven-xfade + J-cut wiring (offset accumulation, input-index math, amix).
See `references/avg-pro-workflow-gap.md` for the 20-stage professional-editor gap
analysis (which stages AVG covers vs. what's still missing, Tier-ranked backlog, and
the "don't rebuild captions" truth).
See `references/agent-brain-free-model.md` for the B-list free-model decision layer
(OpenRouter-free / Ollama + heuristic fallback on every method) and the P36–P39
ffmpeg-side fixes that make the pro-edit render actually pass the X7–X15 gates.
Full diffs/recipes behind P34/P36/P37/P38/P39/P40/P41: `references/remotion-ffmpeg-pitfalls.md`, `references/intro-outro-jcut-ffmpeg.md`, `references/segmented-render-concat.md`. New this session: `references/user-media-clips-audio.md` (P42 — video-clip framerate resample, no-loop-for-video, personal-audio path sync, intro hard-cut).
See `references/offline-e2e-smoke.sh` for the reproducible OFFLINE end-to-end smoke test (P24 + P44 + P45 + P46): it generates 6 local JPG fixtures and runs the full pipeline offline, printing `[STAGE]` markers + the X7–X15 gate so a sync-ffmpeg regression is caught in one command.
See `references/xfade-intro-shortest-isolation.md` for the P51 / P42#5 standalone filter-isolation recipe (the ~8s vs ~13.8s X8-failure table + the `.js` that proves the filtergraph duration without a full E2E render).
See `references/hang-workspace-wipe.md` for the exact P48/P47 diagnosis transcript: how `[M]` markers pinned "acquire done -> gateway done" and the `hasV=true v.passes=false` tell that revealed the asset was wiped between acquire and verify (not a sync spawn).
render recipe, the per-path X8 expected-duration fix (P40), and the failure-signature
table (stream-layout mismatch, label-vs-map, still-image loop, `\,` under `-vf`).
