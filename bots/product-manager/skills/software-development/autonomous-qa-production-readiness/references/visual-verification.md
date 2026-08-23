# Visual verification gate (PHASE 4)

The part most "make it production-ready" passes skip. A unit-test suite going
green does NOT prove the rendered artifact is correct. Do this on every media /
video / slideshow / image pipeline.

## 1. Produce a REAL artifact
Run the actual pipeline on a tiny 2-scene sample that uses LOCAL assets (no
network). For agentic video pipelines, reference local files via inline tags
(e.g. `[Visual: logo.png]`) and a zero-config voice (kokoro / Edge-TTS offline
fallback) so the render needs no API.

## 2. Stream/container checks (ffmpeg, NOT ffprobe)
The project's `ffmpeg-static` binary is `ffmpeg.exe` only — there is NO
`ffprobe`. Use `ffmpeg -i <file>` and parse the Stream lines:
```
Video: h264 ... 720x1280 [SAR 1:1 DAR 9:16]   # orientation correct?
Audio: aac (LC) ... 44100 Hz mono              # audio track present?
Duration: 00:00:07.93                          # non-zero, matches expectation
```
If you need JSON, `ffprobe` is a separate binary not shipped — don't assume it
exists; parse `ffmpeg -i` stderr instead.

## 3. Black-frame detection (the must-have check)
```
ffmpeg -v error -i <file> -vf blackdetect=d=0.3:pix_th=0.15 -f null -
```
- `d=0.3` = at least 0.3s of black to count (avoids single-frame noise)
- `pix_th=0.15` = 15% black pixels threshold
- Output contains "blackdetect" → FAIL (black frames present). No match → PASS.
NB: `blackdetect` prints to stderr; capture it.

## 4. Extract frames + vision-analyze (the proof)
Extract a few frames to a WINDOWS path (MSYS `/tmp/...` often fails to open in
the ffmpeg image2 muxer — use a repo-relative dir like `qa_frames/`):
```
mkdir qa_frames
ffmpeg -y -i <file> -vf fps=1/2 -vframes 3 qa_frames/frame_%02d.png
```
Then call `vision_analyze` on 3–5 frames and ask:
- "Is this a real rendered scene (not black/blank)?"
- "What image/text/caption is visible? Is the caption readable?"
Confirm: local assets actually appear, captions are burned/legible, no garbage
screens. This caught, in-session, that the modular CLI `voice` stage used the
Edge-TTS dispatcher instead of the kokoro controller — visible because the
rendered captions proved the pipeline ran but the voice path differed from the
orchestrator path.

## 5. Audio-sync sanity
Audio present (step 2) + duration ≈ video duration (step 2) ⇒ in-sync enough
for a smoke gate. Deep A/V sync needs waveform alignment — out of scope for a
smoke check.

## Gotchas
- `qa_frames/` is a temp artifact — add it to `.gitignore` so it's never committed.
- `workspace/jobs/<id>/` and `output/` are usually runtime/generated — confirm
  they're gitignored before committing; verify with `git check-ignore`.
- Rendering is RAM-heavy: run it AFTER the full test suite finishes, not
  concurrently (RAM discipline).
