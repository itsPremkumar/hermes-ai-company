# Remotion + ffmpeg Video Pitfalls — concrete recipes

Companion to SKILL.md. Each item records the exact fix applied during the
Automated-Video-Generator hardening pass (2026-07-15). Reuse the patterns.

## P1 — Remotion duration truncation (Root.tsx)
Symptom: `Composition durationInFrames={300}` (10s) clips longer videos.
`selectComposition` reads the static value, so content past 300 frames is lost.
Fix: `calculateMetadata` deriving frames from `inputProps` — see SKILL.md P1 block.
Key: sum scene `durationSec×fps` + intro/outro frames, `Math.max(30, …)`.

## P2 — 4K OOM/timeout (orchestrate.ts)
Weak-hardware render of 2160×3840 sources hangs `delayRender`, `RUN=124` timeout.
Fix recipe (transcode to 720p before `bundle()`):
```ts
const dest = videoRel; fs.mkdirSync(path.dirname(outAbs), { recursive: true });
execFileSync(ffmpeg, ['-y','-i',src,'-vf',`scale=-2:${targetH}`,
  '-c:v','libx264','-preset','veryfast','-crf','23','-c:a','aac',outAbs],
  { stdio: 'ignore' });
```
targetH = 720 (draft/medium) or 1080 (high). Then `renderMedia` with:
`{ imageFormat:'jpeg', concurrency:1, timeoutInMilliseconds:0 }`.
Always try/catch → fallback `renderAgenticSlideshow(res, {...})`.

## P3 — post-render ffprobe gate (gate.ts verifyRenderedVideo)
1) Video detection too strict:
   BAD:  `const hasVideo = /Video:\s*h264/.test(raw);`
   GOOD: `const hasVideo = /Video:/.test(raw) && !/Video: none/.test(raw);`
2) Crossfade duration mismatch for ffmpeg path:
```ts
const xf = 0.5; // crossfadeSec
const xfDur = xf * Math.max(0, visuals.length - 1);
const expectedDur = Math.max(0.1,
  visuals.reduce((s,a)=>s+(a.durationSec??4),0) - xfDur);
res.postRender = verifyRenderedVideo(out, expectedDur);
```
Tolerance in verifyRenderedVideo: `Math.abs(dur - expected) <= Math.max(2, expected*0.05)`.

## P4 — <Video> placeholder hang (AgenticVideo.tsx)
SceneCard: `const isVideoFile = /\.(mp4|webm|mov|m4v)$/i.test(asset.localPath);`
then render `<Video>` only when `isVideoFile`, else `<KenBurnsImage>`. Robust to a
video-kind asset that is actually a generated `.png` placeholder offline.

## P5 — stale public/ assets (orchestrate.ts renderAgenticWithRemotion)
At render start:
```ts
fs.rmSync(assetDir, { recursive: true, force: true });
fs.mkdirSync(assetDir, { recursive: true });
```

## P6 — drawtext apostrophe crash (orchestrate.ts makePlaceholder)
`const label2 = label.replace(/'/g, '’');` then `drawtext=text='${label2}'`.

## P7 — stock keyword mangling (visual-fetcher.ts + agent.ts)
- `expandKeywordsHeuristic`: emit clean individual phrases. **Do NOT add a
  `"<visualPreference> of <topic>"` phrase** (e.g. `"video of lions"`) — it is
  REDUNDANT NOISE (fetcher already knows the kind from `visualPreference`) and
  LOWERS stock relevance. Append CONTEXT phrases instead:
  `["wild <noun>", "<noun> nature", "<noun> close up"]`.
  A brittle test asserting `kw.some(k => k.includes('video'))` forced the bad
  phrase — fix the test to assert distinctness / determinism / no-degenerate-phrase.
- `fetchVisualsForScene`: iterate individual cleaned keywords (NOT `keywords.join(' ')`);
  try Pexels first for images; Openverse image fallback loops per keyword.
- Stale cache bug: a `.video-cache.json` storing an Openverse flickr URL under a
  `video:` key short-circuits Pexels. Fix = delete cache + prefer Pexels images.

## P10 — `eq` filter rejects `temperature` (style-engine.ts gradeFilter)
ffmpeg-static 6.1.1 `eq` has no `temperature` option → render dies with
`Error applying option 'temperature' to filter 'eq': Option not found`.
Use only `contrast/brightness/saturation/gamma`:
```ts
case 'warm':  return 'eq=contrast=1.05:brightness=1.04:saturation=1.22:gamma=0.96';
case 'cool':  return 'eq=contrast=1.0:brightness=0.97:saturation=1.08:gamma=1.05';
case 'cinematic': return 'eq=contrast=1.12:brightness=0.97:saturation=1.1:gamma=0.95';
case 'vivid': return 'eq=contrast=1.08:saturation=1.35:brightness=1.0';
case 'neutral': return 'eq=contrast=1.02:saturation=1.05';
```
(White-balance → separate `colortemperature` filter, not `eq`.)

## P11 — `zoompan` comma-escape doubling (orchestrate.ts sceneFilters)
Correct source form (TWO backslashes → one `\,` in the filtergraph):
```ts
const zoom = a.kind === 'image'
  ? `,zoompan=z=min(zoom+0.0008\\,1.04):d=1:s=${W}x${H}` : '';
```
If a fuzzy `patch` doubles it to `\\\\,`, ffmpeg errors
`No option name near '1:s=720x1280'`. Grep the line; collapse to `\\,`.

## P12 — git branch trap on AVG repo (commit discipline)
Repo has `gstack/hardening-audit-fixes` + others. Without `git checkout main`,
commits strand on the current branch and `git push origin main` says
"Everything up-to-date". Recovery:
```bash
git branch --show-current            # confirm 'main' BEFORE committing
git stash push -- <other author's dirty files>   # protect unrelated WIP
git checkout main
git cherry-pick <wrong-branch-commit>             # carries only your files
git push origin main
git checkout <wrong-branch> && git stash pop     # restore their state
```
Never `git add -A` on this multi-branch repo — stage only edited files.

## Render-proof checklist (run before "done")
- 2+ DIFFERENT topics per renderer (ffmpeg + Remotion).
- Assert X7 (>100KB), X8 (duration within tolerance), X9 (audio present).
- Contact-sheet.png + decisions-report.txt written (visibility).
- API keys passed inline only: `PEXELS_API_KEY=*** npx tsx bin/run.ts …`.
