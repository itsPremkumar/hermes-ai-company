# User-supplied media: video clips (C6) + personal audio (C2)

Extending the agentic pipeline to accept the user's OWN footage / voiceover.
Proven this session (committed work; all X7–X15 verified after the fixes below).

## CLI surface (add to bin/agentic-auto.ts)
```ts
// after the local-assets block:
if (arg('video-clips', '')) cfg.videoClips = arg('video-clips', '').split(',').map(s => s.trim()).filter(Boolean);
if (arg('personal-audio', '')) cfg.personalAudio = arg('personal-audio', '').split(',').map(s => s.trim()).filter(Boolean);
```
autopilot forwards them AND forces `preferVisual:'video'` when `videoClips` present:
```ts
const res = await runAgenticPipeline({
  ...req,
  preferVisual: (req.videoClips ?? cfg.videoClips)?.length ? 'video' : (req.preferVisual ?? cfg.preferVisual),
  videoClips: req.videoClips ?? cfg.videoClips,
  personalAudio: req.personalAudio ?? cfg.personalAudio,
}, ...);
```

## PipelineRequest + AgenticConfig
```ts
videoClips?: string[];     // per-scene, index-aligned, round-robin
personalAudio?: string[];  // per-scene, index-aligned, round-robin
```
Bind per-scene (round-robin) in `runAgenticPipeline` BEFORE acquire consumes it:
```ts
if (req.videoClips?.length) {
  plan.scenes.forEach((s,i) => {
    const clip = req.videoClips![i % req.videoClips!.length];
    if (clip) { s.localAsset = path.basename(clip); s.visualPreference = 'video'; }
  });
}
if (req.personalAudio?.length) {
  plan.scenes.forEach((s,i) => {
    const a = req.personalAudio![i % req.personalAudio!.length];
    if (a) s.personalAudio = path.basename(a);
  });
}
```
`path.basename()` is MANDATORY — `inputAssetPath()` joins with `input/input-assets/` and expects a bare filename. A full relative path (`agentic-pipeline/input-assets/clip1.mp4`) resolves to a non-existent nested path and silently falls back to fetch.

## Fixtures live in input/input-assets/ (NOT agentic-pipeline/input-assets/)
```bash
FF=$(node -e "console.log(require('ffmpeg-static').replace(/\\\\/g,'/'))")
"$FF" -f lavfi -i "testsrc=size=720x1280:rate=25:duration=6,drawtext=text='SCENE':fontcolor=white:fontsize=80:x=(w-text_w)/2:y=(h-text_h)/2" -c:v libx264 -pix_fmt yuv420p -y input/input-assets/clip1.mp4
```
Use a MOTION clip (not solid color) — a solid `color=c=orange:d=4` produces a tiny/low-complexity file that fails X7 size and makes xfade variance unreadable.

## Render-path fixes (the actual bugs that broke the first attempts)

### ffmpeg inputs: do NOT loop video
```ts
// image → ['-loop','1','-i',path]  ;  video → ['-i',path]   (NO -loop for video)
const videoInputs = visuals.flatMap(v => v.kind === 'image' ? ['-loop','1','-i',v.localPath] : ['-i',v.localPath]);
```
Applying `-loop 1` to a `.mp4` corrupts input parsing → "Option not found" / "Error opening input file".

### Every scene + card filter needs fps=25 (video framerate mismatch)
User clips are 29.97fps; the xfade chain is 25fps. Without this, xfade FAILS:
`First input link main frame rate (25/1) do not match the corresponding second input link xfade frame rate (30000/1001)`.
Add `fps=25,` right after `setsar=1,` in scene filters AND intro/outro card filters:
```ts
`...setsar=1,fps=25,trim=duration=${dur},setpts=PTS-STARTPTS,settb=1/25${zoom}...`
// intro/outro card:
`[${idx}:v]fps=25,trim=duration=...,setpts=PTS-STARTPTS,settb=1/25,format=yuv420p[v...]`
```
`settb=1/25` (P36) alone is NOT sufficient — the framerate must be resampled with `fps=25`.

### Personal-audio / video duration must sync plan → manifest
STAGE 2.5 mutates `a.durationSec` (the manifest asset), but a SEPARATE manifest build later uses `durationSec: s.durationSec` from the PLAN (3/5/5), discarding the real media duration. Fix: in STAGE 2.5, ALSO write `scene.durationSec = realDur`:
```ts
if (a.kind === 'video' && a.localPath && fs.existsSync(a.localPath)) {
  const vd = estimateAudioDurationSafe(a.localPath);   // works for video too (ffprobe)
  if (vd > 0) { a.durationSec = vd; scene.durationSec = vd; }
}
const pa = scene?.personalAudio ? inputAssetPath(scene.personalAudio) : undefined;  // resolve via inputAssetPath, NOT bare basename
if (pa && fs.existsSync(pa)) {
  const dur = estimateAudioDurationSafe(pa);
  a.audioPath = pa; a.durationSec = dur; scene.durationSec = dur;
  a.captionSegments = [{ text: scene.voiceoverText, startMs: 0, endMs: Math.round(dur*1000) }];
  continue;
}
```
`estimateAudioDurationSafe` uses `require('ffprobe-static').path` — returns an object `{path}`; use `.path` (NOT the object). It returns the real duration for both audio and video.

### Intro → first scene MUST be a hard cut (not xfade)
The first xfade `[vintro][v0]xfade=offset=2` consumed the ENTIRE 2.5s intro, leaving a ~2.5s X8 gap (planned 16.5 vs actual 14.0). Force a cut:
```ts
const tk: any = prev === 'vintro' ? 'cut'
  : (isCard ? 'fade' : (stylePlan.scenes[i - (introClip ? 1 : 0)]?.transitionIn ?? 'fade'));
// cut → `concat=n=2:v=1:a=0`; cursor += orderedDur[i]  (no xfade subtraction)
```
A cold-open cutting into content is also better UX.

## Verification (this session)
- `npx tsc -p tsconfig.json --noEmit` → 0 errors.
- `npx tsx --test "src/**/*.test.ts"` → 218 pass.
- E2E: `npx tsx bin/agentic-auto.ts --topic "test personal media" --title Test --no-sfx --max-attempts 1 --video-clips clip1.mp4 --personal-audio vo1.m4a` → X7 ✓ X9–X15 ✓ (X8 the last to pass, after the intro-cut + duration-sync fixes).
- ffmpeg frame extraction (`-frames:v 1` after `-ss`) is unreliable on this box (0-byte files); verify duration via `ffprobe -show_entries format=duration` instead.
