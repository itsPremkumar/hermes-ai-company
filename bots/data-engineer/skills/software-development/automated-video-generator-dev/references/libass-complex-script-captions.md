# Complex-script captions must use libass, not drawtext (AVS)

## Problem
`drawtext` (libfreetype) cannot OPEN-TYPE SHAPE complex scripts. Tamil,
Devanagari, Arabic, Myanmar, Khmer render as empty/tofu boxes even when the
correct glyphs exist in the font (NotoSansTamil etc.). Reproduced 2026-08-03:
libass rendered Tamil correctly; drawtext produced tofu.

Latin and CJK need NO shaping → keep them on the lighter `drawtext` path
(CJK tested/working via msyh/Noto CJK; Latin via Arial/DejaVu).

## Solution pattern (implemented 2026-08-03)
- `needsComplexScriptShaping(text)` — regex over Tamil/Devanagari/Arabic/
  Myanmar/Khmer ranges. Do NOT use surrogate-pair ranges (e.g. `[锭-𝇿]`) —
  they break the regex literal under TS/ESLint `no-misleading-character-class`
  / parse errors. Use BMP ranges only.
- `buildLibassCaptionFilter(text, {size,color,workDir,idx,pos})` (compose.ts):
  writes a timed `.ass` to `workDir`, returns
  `subtitles='<ass>':fontsdir='<bundled-fonts>':force_style='FontName=...,FontSize=...,PrimaryColour=...'`.
- `render.ts` `libassCaption({text,start,end,size,color,fontFile,workDir,idx})`:
  same but with per-line `start`/`end` timestamps (HH:MM:SS.cc) so the caption
  appears only during its scene window.
- Route BOTH caption paths to libass for complex scripts:
  - `applyTextOverlay` (compose.ts) — explicit text overlays.
  - `render.ts` per-scene `segCaptionArg` + kinetic `kin` pushes.

## Headless / Windows correctness
Point `fontsdir` at the BUNDLED fonts dir (`assets/fonts`), NOT system
fontconfig/DirectWrite. `resolveCaptionFont(text)` picks the right bundled
font (NotoSansTamil / NotoSansDevanagari / NotoSansArabic). Avoids "font not
found" on headless Linux and the Windows DirectWrite path.

## libass availability
ffmpeg must be built with `--enable-libass`. The AVS Windows ffmpeg-static
build HAS libass (verified rendering Tamil successfully). Always verify with a
real ffmpeg render + frame inspection, not just that the filter string builds.

## Test
`tests/agentic/operations/libass-caption.test.ts` — asserts the ASS file is
written with correct UTF-8 Tamil text and `fontsdir` on the bundled Tamil
font.
