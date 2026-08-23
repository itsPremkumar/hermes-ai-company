# Captions for complex scripts (Tamil / Devanagari / Arabic)

Empirically proven 2026-08-03 while closing the loop on a Tamil end-to-end video.

## Hard-won findings (verify-before-claim, do not guess)
- **Bundled fonts MUST be real, complete fonts.** The notofonts.github.io
  jsdelivr CDN served a 74 KB Tamil subset with 0 Tamil glyphs (a
  Latin-only fake). Verify with fonttools:
  `python -c "from fontTools.ttLib import TTFont; f=TTFont(p); print(len(f.getBestCmap()))"`
  and confirm codepoints map to real outlined glyphs
  (f['glyf'][f.getBestCmap()[0xB85]].numberOfContours > 0).
- **ffmpeg-static's drawtext CANNOT shape Indic glyphs even when the font is
  complete and HarfBuzz is enabled.** Proven: a static Tamil font with 72 real
  glyphs still rendered tofu via drawtext text='...' AND via textfile=
  (UTF-8 safe, ruling out shell encoding). Latin works (no shaping needed).
- **libass (subtitles filter) renders Indic correctly.** Proven: an ASS file
  with Tamil text + subtitles=file.ass produced real Tamil letterforms
  (vision-confirmed). ffmpeg-static ships --enable-libass and --enable-libharfbuzz.
- On Windows, libass picks the system font (DirectWrite, e.g. NirmalaUI)
  before bundled fonts. For headless Linux, force bundled fonts via fontsdir=
  plus an explicit Style: ... FontName=NotoSansTamil matching the font family.

## ffmpeg feature probe (one-liner)
FFMPEG=$(node -e "console.log(require('ffmpeg-static'))"); "$FFMPEG" -filters 2>/dev/null | grep -iE "libass|drawtext|harfbuzz"

## The correct fix (not yet implemented in compose.ts)
Route complex-script captions (Tamil/Devanagari/Arabic — detect via the same
regexes resolveCaptionFont already uses) through a generated .ass file +
subtitles= filter, keeping drawtext for the proven Latin/CJK/emoji path.
Scope it so the English (99% case) render is untouched.

## Font sourcing that works
- Google's google/fonts repo (ofl/notosanstamil/NotoSansTamil[wdth,wght].ttf)
  for variable fonts; instance to a static Regular with
  fontTools.varLib.instancer.instantiateVariableFont(f, {'wght':400}, inplace=True)
  and delete fvar so ffmpeg's freetype does not choke on the default instance.

## Caveat
AVS has NO Tamil/Indic TTS engine (Kokoro/Edge are English-only) — a Tamil
audio track is out of scope; captions are the deliverable for Indic scripts.
