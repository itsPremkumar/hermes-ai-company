# Captions: bundled fonts, i18n, headless, and the injection non-issue

## Context
A "different-perspective" audit of AVS found three caption-related gaps that the
usual architecture audit misses:

1. **Headless Fontconfig failure** — `resolveFontFile()` only ever resolved
   *system* fonts. On headless/CI boxes without fontconfig, ffmpeg emits
   `Fontconfig error: Cannot load default config file` and drops all
   subtitles. (Observed live during a QA run on the 6GB Windows box where
   `fc-list` was not installed.)
2. **Non-Latin tofu boxes** — Tamil / Devanagari / CJK captions rendered as
   `□` because system fonts (Arial/DejaVu) lack those glyphs. The project
   author is a Tamil speaker, so this is a real user-facing gap.
3. **"No API key" claim overstated** — Pexels (the *recommended* provider per
   `logPexelsRecommended()`) requires `PEXELS_API_KEY`; keyless runs silently
   degrade to free CC sources. README said "No API key" unqualified.

## Fix applied (commits 2c594ee + eec6fda)
- Bundled SIL-Open-Font-License Noto fonts in `assets/fonts/`:
  `NotoSans-Regular.ttf` (Latin), `NotoSansTamil-Regular.ttf`,
  `NotoSansDevanagari-Regular.ttf`, `NotoSansSC-Regular.otf` (CJK, ~8.3 MB).
- `resolveCaptionFont(text)` detects script via Unicode ranges
  (`/[\u0B80-\u0BFF]/` Tamil, `/[\u0900-\u097F]/` Devanagari,
  `/[\u3000-\u9FFF\uFF00-\uFFEF]/` CJK) and returns the matching bundled font.
- `resolveFontFile()`'s headless fallback now returns `resolveCaptionFont('')`
  (bundled Latin) instead of relying on fontconfig.
- Every caption/title/lower-third/CTA/per-scene overlay path uses
  `resolveCaptionFont(text)` (or `overlayFont(text)` helper).
- README + `bin/agentic-run.ts` startup banner now state keyless-mode reality.

## Download recipe (reproducible)
```bash
cd /c/one/Automated-Video-Generator && mkdir -p assets/fonts && cd assets/fonts
BASE="https://cdn.jsdelivr.net/gh/notofonts/notofonts.github.io@main/fonts"
curl -fsSL "$BASE/NotoSans/hinted/ttf/NotoSans-Regular.ttf"        -o NotoSans-Regular.ttf
curl -fsSL "$BASE/NotoSansTamil/hinted/ttf/NotoSansTamil-Regular.ttf"        -o NotoSansTamil-Regular.ttf
curl -fsSL "$BASE/NotoSansDevanagari/hinted/ttf/NotoSansDevanagari-Regular.ttf" -o NotoSansDevanagari-Regular.ttf
curl -fsSL "https://cdn.jsdelivr.net/gh/notofonts/noto-cjk@main/Sans/SubsetOTF/SC/NotoSansSC-Regular.otf" -o NotoSansSC-Regular.otf
```
Validate each (magic bytes): TrueType = `00 01 00 00`; OTF/CJK = `4F 54 54 4F`
("OTTO"). `head -c 4 file | xxd`.

## Empirical tofu-proof (run after any caption-font change)
Do NOT trust "the font exists" — prove glyphs render:
```bash
FFMPEG=$(node -e "console.log(require('ffmpeg-static'))")
FONT="$PWD/assets/fonts/NotoSansTamil-Regular.ttf"
"$FFMPEG" -y -f lavfi -i "color=c=blue:s=640x200:d=1" \
  -vf "drawtext=fontfile='$FONT':text='நீர் அருந்துவது':fontcolor=white:fontsize=40:x=20:y=80" \
  -frames:v 1 -t 0.1 -c:v libx264 -pix_fmt yuv420p proof_tamil.mp4
# exit 0 + non-empty mp4 => glyphs present (not tofu). rm proof_tamil.mp4 after.
```
Note: `--frames:v 1` with the `image2` muxer errors on single-frame pattern;
use `-t 0.1` + mp4 output instead.

## Caption ffmpeg injection — PROVEN NON-ISSUE (don't "fix" it again)
A fresh auditor may flag `drawtext text='...'` as command-injection. It is NOT:
- Inside single-quoted `text='...'`, a `,` is NOT a filterchain separator and a
  `:` is NOT an option separator — ffmpeg parses the quoted value literally.
- `esc()` in compose.ts escapes `\`, `:`, AND `'` (correct). The overlay path's
  `.replace(/'/g, "'\\''")` handles the only break character (`'`, which would
  close the quote). Raw commas/colons in captions are safe.
- Empirical test: `drawtext=text='A,B'` and `drawtext=text='A:B'` both render
  fine (exit 0). Only a literal `'` breaks parsing, and that is escaped.
=> Do not add escaping for `,`/`:` in caption text; it is unnecessary churn.

## Test
`tests/agentic/operations/font-selection.test.ts` — 5 cases: Latin/Tamil/
Devanagari/CJK resolve to the right bundled file + all four files present on
disk. Importing compose.ts outside tsx fails (missing compiled deps); run tests
with `npx tsx --test` from repo root (so `process.cwd()` = repo root, matching
`bundledFontPath`'s primary path).
