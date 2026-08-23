# P18/P19/P20/P21 — ffmpeg caption + zoompan + blackdetect pitfalls (AVG black-frame root cause)

## Symptom
A render completes (has audio, passes X7 size / X8 duration / X9 audio) but the
post-render `blackdetect` (X10) reports ~the entire duration black
(e.g. "X10:black 16.24s" of a 16.32s clip). The video LOOKS unwatchable.

## Root cause — TWO independent bugs (know which one you hit)
1. **P18/P19/P20 — the RENDER produces black frames** (libass subtitles broken, or
   zoompan d=1). Real black output.
2. **P21 — the X10 GATE false-positives on a perfectly valid clip.** THE decisive bug
   this session. The render was NEVER black; `detectBlackFrames` used an invalid
   `pic_th` blackdetect option that this ffmpeg build mis-parses, flagging the WHOLE
   clip as black. See "THE decisive root cause" below.

**Always disambiguate first:** run the signalstats + blackdetect A/B test in P21
BEFORE touching the render. A valid clip has `YAVG` well above ~10 and yields ZERO
`black_start` lines with `pix_th=0.15`. If it's genuinely black (YAVG≈0), go to P18.

## THE decisive root cause this session: X10 GATE false-positive (NOT the render)
The render was **never black**. The whole "black video" panic was a **false-positive in
the verification gate** (`src/agentic/video-analyzer.ts` `detectBlackFrames`), not the
ffmpeg pipeline. Symptom looked identical: X10 reports ~entire duration black, render
"fails". But the produced MP4 is valid (audio + bright video).

**Bug:** the blackdetect call used `blackdetect=d=0.3:pic_th=0.10:pix_th=0.15`.
`pic_th` is an **INVALID option on ffmpeg-static 6.1.1** (this build rejects it). When
present, ffmpeg mis-parses and flags the **ENTIRE clip** as black
(`black_start:0 black_end:13.84 black_duration:13.84`) — a false positive. The render
pipeline (xfade + drawtext + kinetic + vignette) was producing a perfect 720×1280 H.264
the whole time (proven: `signalstats YAVG=87` = bright; 1.1 MB PNG frame extracts).

**Definitive A/B test (run it — settles any "is it black?" debate):**
```bash
FFMPEG=$(node -e "console.log(require('ffmpeg-static'))")
F=agentic-pipeline/workspaces/job_*/render/job_*.mp4   # any rendered clip
# WRONG: pic_th present -> falsely flags whole clip black
"$FFMPEG" -i "$F" -filter:v "blackdetect=d=0.3:picture_black_ratio_th=0.10:pix_th=0.15" -f null - 2>&1 | grep -i "black_start"
#   -> black_start:0 black_end:13.84 black_duration:13.84   (FALSE POSITIVE)
# RIGHT: pix_th only -> correctly reports NO black on a valid clip
"$FFMPEG" -i "$F" -filter:v "blackdetect=d=0.3:pix_th=0.15" -f null - 2>&1 | grep -i "black_start"
#   -> (no line) = clip is NOT black
```
**Fix:** `detectBlackFrames` now uses `blackdetect=d=${minDur}:pix_th=0.15` (removed
`pic_th`/`picture_black_ratio_th`). A TRULY black clip is still caught (test 33 passes).

**Lesson / workflow:** when X10 says "black", FIRST confirm with the signalstats +
blackdetect A/B above BEFORE assuming the render is broken. A valid clip has
`YAVG` well above ~10 and yields zero `black_start` lines with `pix_th=0.15`. Chasing
the render (subtitles/drawtext escaping, zoompan) was a red herring here — the spike in
the QA gate was the actual defect.

**Stale-test trap:** tests that asserted `testsrc` (thin black BORDERS, bright center)
should trigger X10 were encoding the bug. After the fix, `testsrc` correctly does NOT
register as fully-black (only X7 size fails). Update such assertions to expect
`failed === ['X7']` (or `[]` for the generated-mp4 test), not `['X10']`.

## Fast reproduction of P18 (libass broken, no network)
```bash
FFMPEG=$(node -e "console.log(require('ffmpeg-static'))")
printf "1\n00:00:00,000 --> 00:00:02,000\nHello\n" > /tmp/cap.srt
IMG=$(ls agentic-pipeline/workspaces/job_*/assets/images/scene_01/candidate_1.jpeg | head -1)
# libass fails -> black/empty output:
"$FFMPEG" -loop 1 -i "$IMG" -vf "subtitles=/tmp/cap.srt" -t 3 -y /tmp/t_sub.mp4
# drawtext works -> non-black:
"$FFMPEG" -loop 1 -i "$IMG" -vf "drawtext=text='Hello':fontcolor=white:fontsize=30:box=1:boxcolor=black@0.5:x=(w-text_w)/2:y=h-text_h-120" -t 3 -y /tmp/t_draw.mp4
# confirm NOT black (use pix_th=0.15, NOT pic_th):
"$FFMPEG" -i /tmp/t_draw.mp4 -vf "blackdetect=d=0.1:pix_th=0.15" -f null - 2>&1 | grep -i blackdetect
# (no line printed = NOT black)
```

## The fix for P18 — burn captions with `drawtext`, not `subtitles`
Replace the `if (captionFile) { vfArgs.push(\`...subtitles=...\`); videoMap='[vcap]'; }`
block with a per-segment drawtext loop. Exact, copy-paste (TS template literal — note
the `\\,` inside `enable=` is TWO backslashes in source = one `\,` in the filtergraph):

```ts
if (captionFile) {
  let ctag = videoChain, ci = 0, tBase = 0;
  for (const a of visuals) {
    const dur = a.durationSec ?? 4;
    const segs = a.captionSegments?.length ? a.captionSegments
      : [{ text: res.plan.scenes[a.sceneIndex]?.voiceoverText ?? '', startMs: 0, endMs: Math.round(dur * 1000) }];
    for (const s of segs) {
      const start = (tBase + s.startMs / 1000).toFixed(2);
      const end   = (tBase + s.endMs / 1000).toFixed(2);
      const safe  = s.text.replace(/'/g, '’').replace(/:/g, '\\:').replace(/\n/g, ' ');
      vfArgs.push(`${ctag}drawtext=text='${safe}':fontcolor=white:fontsize=30:`
        + `box=1:boxcolor=black@0.5:boxborderw=10:line_spacing=4:`
        + `x=(w-text_w)/2:y=h-text_h-120:enable='between(t\\,${start}\\,${end})'[c${ci}]`);
      ctag = `[c${ci}]`; ci++;
    }
    tBase += dur;
  }
  videoMap = ctag;
}
```

## Editing trap (applies to both P18 fix and P21 diagnosis)
**Never hand-edit ffmpeg backslash escapes with the fuzzy `patch` tool.** A `replace_all`
on a `between(t\\,..\\,..)` clause will also match the kinetic-lowerthird line (same
tail) and corrupt it; the tool also doubles/mangles backslash counts so the final line
can end up with NO backslashes (`between(t,..,..)`). Use a `node -e` exact-replace
script on a unique non-backslash anchor (e.g. `line_spacing=4`) instead, then re-run
`tsc` + a 1-scene render + `blackdetect` (with `pix_th=0.15`!) to confirm.
