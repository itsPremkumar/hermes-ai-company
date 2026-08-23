# AVS visual re-verification discipline

## The re-verify rule (most important lesson)
When you fix a render bug found by visual QA, the combination matrix you rendered
*before* the fix is **stale evidence**. It proves the OLD code was broken, NOT that
the NEW code is correct. Two failure modes this causes:
- You declare "verified" using pre-fix frames → the fix is actually untested.
- You re-render the same matrix but forget → you're re-proving the bug, not the fix.

**Always re-run the full combinatorial batch AFTER the fix lands** so the same
matrix exercises the fixed code. In the July-2026 AVS sweep this bit twice:
the 47-combo batch was rendered once *before* commit `058c1a7` (orientation +
watermark fixes), then had to be re-run *after* to produce valid evidence.

Concrete loop (also encoded in `scripts/avs-combo-render.ts`):
1. Generate batch: perspectives(10) × orientations(3) × captions(3) × music,
   + multi-language all-tags STRESS job + control-surface dryRun.
2. Render `npm run generate:agentic` end-to-end (local assets, bundled music).
3. Assert ffprobe W×H per orientation (portrait 720×1280, landscape 1280×720,
   square 1080×1080) — this is the automated gate; it is NECESSARY but not sufficient.
4. Extract a late frame per orientation (`ffmpeg -ss 3.0 -i out.mp4 -frames:v 1
   -vf scale=480:-1 frame.png`) and `vision_analyze` it.
5. Fix any defect, then GOTO 2 (re-render the whole batch on the fixed code).

## Vision spot-check question bank
Ask these EXACT classes of questions per frame — they are what caught the two
July-2026 defects (a portrait fallback + an opaque-logo black box that both passed
every ffprobe/codec/blackframe gate):

Orientation (landscape):
- "Is the image WIDE (wider than tall, filling the frame edge-to-edge, no big black
  bars)?"  — catches the 720×1280-portrait-fallback bug.
- "Do you see the perspective gradient image filling the frame?"

Orientation (square):
- "Is the image a SQUARE aspect (equal width and height, filling frame)?"

Orientation (portrait):
- "Is it tall portrait (9:16)?"

Watermark (the trap): ask on EVERY frame regardless of orientation:
- "Is there a grey/dark square box in the bottom-right corner? (There should be NONE
  unless a transparent logo was explicitly opted in via `brand`.)"
  → opaque-logo (`rgb24`, no alpha) watermark stamps this box. Code now SKIPS opaque
  logos with a warning and gates on `opts.brand` (commit 058c1a7).
- "Do you see a clean brand logo (gear+play, cyan-purple) in the corner? (Only if brand
  was set AND the logo has an alpha channel.)"

Captions:
- burned/none: "Is there burned subtitle text? (Should be NONE for captions=none.)"
- karaoke: "Is karaoke caption text visible and legible?"

Generic:
- "Any glitches/artifacts/distortion/black frames?"

## Why codec/ffprobe gates are not enough (recap)
Both July-2026 defects produced valid, playable MP4s with correct codec/duration/audio
and correct ffprobe W×H. They ONLY surfaced in a vision pass:
- Orientation-ignored: landscape requested → 720×1280 reported by ffprobe, played
  fine, but a vision frame showed it was taller-than-wide. The dimension assert in
  step 3 catches it; the vision question confirms it *looks* right.
- Watermark black-box: ffprobe/Duration/blackframe all clean; vision saw a solid black
  square in the corner.

Run the dimension assert (step 3) for the FAIL-FAST automated signal, but keep the
vision questions (step 4) as the authoritative "does it actually look right" check.
