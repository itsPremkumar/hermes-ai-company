# Intro/Outro + J-cut ffmpeg wiring (AVG agentic pipeline)

Proven-correct pattern for weaving branded title cards into a slideshow render
and applying a J-cut, in `src/agentic/orchestrate.ts` `renderAgenticSlideshow`.

## The single bug that breaks the whole chain
The xfade `offset` for the i-th transition must be the PICTURE-START of clip `i`
in the *ordered* list (intro -> scenes -> outro), accumulated with xfade overlap.
Using `offsetFor(visuals, i, xf)` (scenes only) drifts once >=3 transitions exist
-> `[Parsed_xfade_N] Failed to configure output pad` -> render dies with
`Error reinitializing filters`. Fix = accumulate over the real ordered list.

## Correct offset accumulation
```ts
const clips = [
  ...(introClip ? [{ tag: 'vintro', dur: opts.intro!.durationSec ?? 2.5 }] : []),
  ...visuals.map((a, i) => ({ tag: `v${i}`, dur: a.durationSec ?? 4 })),
  ...(outroClip ? [{ tag: 'voutro', dur: opts.outro!.durationSec ?? 3 }] : []),
];
let acc = 0;
for (let i = 1; i < clips.length; i++) {
  const cur = clips[i], prev = clips[i - 1];
  const off = acc;
  const isCard = cur.tag === 'vintro' || cur.tag === 'voutro';
  const tk = isCard ? 'fade' : (stylePlan.scenes[i - (introClip ? 1 : 0)]?.transitionIn ?? 'fade');
  const outTag = i === clips.length - 1 ? 'vout' : 'vx' + i;
  if (tk === 'cut') {
    sceneFilters.push(`[${prev.tag}][${cur.tag}]concat=n=2:v=1:a=0[${outTag}]`);
  } else {
    const xname = xfadeName(tk);
    sceneFilters.push(`[${prev.tag}][${cur.tag}]xfade=transition=${xname}:duration=${xf}:offset=${off}[${outTag}]`);
  }
  acc += prev.dur - xf;
}
videoChain = clips.length === 1 ? `[${clips[0].tag}]` : '[vout]';
```

## Input index math (critical)
Intro/outro clips are appended AFTER scene stills AND after audio inputs:
```ts
if (introClip) videoInputs.push('-i', introClip);
if (outroClip) videoInputs.push('-i', outroClip);
const introInputIdx = introClip ? visuals.length : -1;
const outroInputIdx = outroClip ? visuals.length + (introClip ? 1 : 0) : -1;
sceneFilters.push(`[${introInputIdx}:v]trim=duration=${dur},setpts=PTS-STARTPTS,format=yuv420p[vintro]`);
```
Audio inputs appended AFTER all video inputs, so audio base index =
`visuals.length + (introClip?1:0) + (outroClip?1:0)`.

## J-cut audio (audio leads picture by jCutSec)
```ts
const videoInputCount = visuals.length + (introClip ? 1 : 0) + (outroClip ? 1 : 0);
const base = videoInputCount;
const introDur = introClip ? (opts.intro!.durationSec ?? 2.5) : 0;
const delayed: string[] = [];
voScenes.forEach((_, i) => {
  const picStart = introDur + offsetFor(visuals, i, xf);
  const audioStart = Math.max(0, picStart - (i === 0 ? 0 : jCut));
  delayed.push(`[${base + i}:a]adelay=delays=${(audioStart * 1000).toFixed(0)}:all=1[a${i}]`);
});
const mix = delayed.map((_, i) => `[a${i}]`).join('') + `amix=inputs=${voScenes.length}:duration=longest:normalize=0[aout]`;
audioFilter = [...delayed, mix].join(';');
```
`normalize=0` keeps VO at full volume. Final mux uses `-shortest` to trim
trailing J-cut silence.

## Verification
- `applyProEdits` (hook-first/variable-pacing) is PURE -> unit-test in `plan.test.ts`.
- Intro/outro + J-cut are filtergraph-only -> ONLY a live render proves them.
  Run with `--max-attempts 1 --no-sfx` (P24) and assert X7-X15 pass. The render
  failure mode is a hard `Error reinitializing filters`, not a gate false-positive.
