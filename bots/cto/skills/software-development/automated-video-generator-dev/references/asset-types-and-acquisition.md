# AVS asset types & media-kind control — knowledge bank

Session 2026-08-01: swept every asset-type combination through the agentic
pipeline (generated video / generated image / downloaded video / downloaded
image / mixed). All facts below empirically verified; every output video passed
frame QA (blackdetect + freezedetect = 0).

## Forcing image vs video per scene

- `defaultVisual: "image" | "video"` (job field) is a HINT to the planner, NOT a
  hard kind lock. Verified: a job with `defaultVisual: "image"` still fetched
  VIDEOS because the planner's motion heuristics (verbs like "roll", "frame",
  "crash" in the narration) overrode it and set `visualPreference: 'video'`.
- The planner picks kind per scene from narration keywords (motion → video,
  static → image). This is the ONLY per-scene kind mechanism.
- Only per-scene tag that exists: `[KenBurns: on|off]`. There is NO
  `[Still:]` / `[Image:]` / `[Video:]` kind tag in script-parser.ts.
- To FORCE an exact asset + kind: bind a local file with
  `[Visual: <file>.jpg]` or `[Visual: <file>.mp4]` (file lives in
  `input/visuals/`) → scene gets `localAsset` → acquire uses it directly.
- MIXED kinds in ONE job work through the NORMAL acquire path (no
  `--no-acquire` needed): `[Visual: file]` scenes bind local, keyword scenes
  fetch stock with the planner's per-scene kind. Verified: "Mashup" job =
  2 AI images + 2 stock videos in a single 15s video (manifest showed
  `2 kind:image + 2 kind:video + 1 kind:music`).

## Free image generation (no key): Pollinations

```
curl -sL --max-time 90 "https://image.pollinations.ai/prompt/<url-encoded prompt>?width=1280&height=720&nologo=true&seed=7" -o input/visuals/ai_x.jpg
```
- Free, no signup. Backend model is `sana` (visible in the JPEG Exif
  `manufacturer=sana`). Output ~1024×576 JPEG; the URL w/h params are a
  request, not guaranteed.
- Verify with `file x.jpg` before relying on it.

## Direct stock image download: Pexels Photos API

- Key: `PEXELS_API_KEY` in `.env` (also `PIXABAY_API_KEY` populated as
  alternative). Never print the value; `source .env` and use the var.
- Search: `curl -sL -H "Authorization: $PEXELS_API_KEY" "https://api.pexels.com/v1/search?query=<q>&per_page=3&orientation=landscape"`
  → pick `photos[0].src.original` → download. Originals are huge
  (5000×3500+); Ken Burns handles them fine (scale/crop path).
- Reusable helper: `scripts/fetch-stock-images.sh` (sources `.env`, fetches
  one query per call, writes `input/visuals/stock_*.jpg`).

## Motion-graphics job fields (job level, all additive)

`kenBurns: true` (zoompan on images), `kineticText: true` (animated
lower-third text), `captions: true` (burned subtitles), `vignette: true`,
`sfx: true` (transition sound effects). Per-scene extras: `filter`
(bw|vintage|sepia|blur), `grade`, `transition` (fade|slide|zoomblur|cut),
`speed`, `keyframes: [{t,z,x?,y?}]` (multi-point zoom path).

## Verified asset matrix (all 1280×720 h264+aac, QA clean)

| job id | assets used | notes |
|---|---|---|
| stock_images "Still Frames" | 2 stock VIDEOS | `defaultVisual:image` overridden — proof of the hint-vs-lock pitfall |
| stock_videos "Wild Motion" | 2 stock videos + sfx | |
| ai_canvas "AI Canvas" | 2 Pollinations images | kenBurns + kineticText + vignette |
| mashup "Mashup" | 2 AI images + 2 stock videos | mixed kinds, one video, 4 chapters |
| downloaded_images "Downloaded Frames" | 2 Pexels photos | kenBurns + kineticText |

Reusable job files: `input/scripts/asset-sweep.json`, `stock-images-sweep.json`.

## Pitfall — big Pexels video downloads look like a hang

Stock video "original" files (Pexels) can be 100–300MB; at ~1.8MB/s a single
scene takes 10+ minutes and the pipeline downloads 2 candidates per scene
sequentially. Don't kill it. Check real progress with
`stat -c "%s bytes, %y" workspace/jobs/<id>/assets/videos/<scene>/candidate_1.mp4.part`
twice ~8–10s apart (growing = fine). Note: MSYS `ls -la` col 5 is the UID, not
size — use `stat -c %s` (see windows-msys-tooling skill).

## Related

- FLUX 3 generated VIDEO clips: `references/flux3-integration.md`
  (bridge, quota, fallback, per-job no-acquire).
- Frame QA recipe (blackdetect/freezedetect commands): flux3-integration.md §E2E.
