# AVS Variety-Video Generation (orchestrator path)

How to produce a **variety of sample videos** as post-audit / "verify all varieties"
proof-of-work, **offline**, by calling `renderAgenticSlideshow()` directly. This is
the fastest way to exercise the audit-hardened code (A3 voiceover guard, D1
music-mux on audio-less silent, E1 genpts concat) with real ffmpeg renders.

## Why not agentic-batch / agentic-cli?
Those run `runAgenticPipeline` = plan → acquire → verify → gate → render, which
**fetches stock visuals** and **times out on the offline box**. Driving
`renderAgenticSlideshow` with a hand-built `PipelineResult` + local `input/visuals/*.mp4`
assets skips the network entirely.

## The harness
`scripts/gen-variety.ts` (copy to the repo, run `npx tsx scripts/gen-variety.ts`).
It builds a minimal `PipelineResult`:
```ts
const res = {
  workspace: { root: OUT, jobId },
  plan: { scenes: clipNames.map((_, i) => ({ sceneIndex: i, durationSec: 4, voiceoverText: '' })) },
  manifest: { jobId, title: jobId, assets },   // assets = [{kind:'video',sceneIndex,localPath,durationSec}] (+ optional {kind:'music',localPath})
  gate: { pass: true },
} as any;
await renderAgenticSlideshow(res, { outPath, aspect: '9:16', music: true, kenBurns: true, transition: 'fade', sfx: false });
```
Matrix covered: portrait 9:16 / square 1:1 / landscape 16:9 × music-on / audio-less,
plus a 7-clip multi-scene and a truly-silent (`trulySilent:true`, no music asset)
variant. This directly stresses the audio-less crash class.

## Auto aspect-variant spawn (important)
A SINGLE `renderAgenticSlideshow` call does NOT just write `<id>.mp4` — it also
auto-spawns `<id>_16x9.mp4`, `<id>_1x1.mp4`, `<id>_9x16.mp4` (the `renderVariant`
function). So 6 variants → **24 deliverable mp4s**. Don't be surprised by the extra
files; they're the same render in 3 other aspect ratios.

## Verify the audio-less path actually exercised it
The truly-silent variant (`v6`) must NOT crash and must produce a valid video.
Confirm the audio track is genuinely silent (the D1 guard attached a silent track
rather than crashing):
```sh
ffmpeg -i output/variety/v6_audioless_silent_3clip.mp4 -af volumedetect -f null -
# expect: mean_volume: -91.0 dB   (digital silence = audio-less path worked)
```
A crash here with `Stream specifier ':a' matches no streams` would mean a regression
in the D1/A3 guards — but those are closed (see avs-audio-less-audit.md / G13).

## Visual gate (mandatory)
Extract a mid-frame per primary variant and `vision_analyze` it:
```sh
ffmpeg -y -v error -i output/variety/v1_portrait_9x16_3clip.mp4 -ss 6 -frames:v 1 workspace/tmp/frames/v1.jpg
# INPUT seek (-ss AFTER -i) — never output seek (G8: -ss before -i returns 0-byte on odd keyframes)
```
Ask: correct aspect framing? any corruption / black / distortion / concat seam?
This session's 6 variants all passed vision check (valid frames, correct 9:16/1:1/16:9,
no artifacts).

## G15 — RAM exhaustion → gyan.dev ffmpeg SEGFAULT (new gotcha)
Running several renders back-to-back on this ~800MB-RAM box, once free RAM drops
below ~400MB, ffmpeg exits with **3221225794 (0xC0000005 = STATUS_ACCESS_VIOLATION)**
— NOT a "matches no streams" logic error. Symptom: a run that worked alone fails with
that code when batched. Mitigations:
- Run variants in ISOLATION (one `npx tsx scripts/gen-variety.ts` per variant, or
  filter the `variants` array to one entry), letting RAM recover between runs.
- Kill stray `ffmpeg.exe` / `ffprobe.exe` (`taskkill /F /IM ffmpeg.exe`) before a run.
- This is distinct from G6 (x264 malloc OOM during a single encode). G15 is the
  whole-process segfault under cumulative RAM pressure across sequential renders.

## Containment
Outputs land under `output/variety/` (per AVS RAM/containment rules). Delete the
harness after use if you don't want it tracked (`rm scripts/gen-variety.ts`), or keep
it as a reusable generator. Temp frames go under `workspace/tmp/frames/`.
