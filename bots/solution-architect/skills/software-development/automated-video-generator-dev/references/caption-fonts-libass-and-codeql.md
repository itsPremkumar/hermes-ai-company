# AVS — Captions / non-latin fonts + GitHub Code-Scanning alerts

Condensed from the 2026-08-03 "different perspective" + GitHub-security-alert session.

## 1. `drawtext` CANNOT render complex scripts (Tamil / Devanagari / Arabic)

**Symptom:** captions burn as empty boxes (tofu) for Indic/Arabic text even though
the font file is correct and `ffmpeg -filters` shows `--enable-libharfbuzz` and
`--enable-libfreetype`. Latin renders fine; CJK (non-shaped) usually renders.

**Root cause:** ffmpeg-static's `drawtext` (libfreetype) does not shape complex
scripts the way HarfBuzz does, even with `text_shaping=1`. Indic/Arabic need
OpenType GSUB reordering that drawtext's freetype path mishandles -> `.notdef` boxes.

**Verified fix:** render complex-script captions with the **`subtitles` (libass)
filter** instead of `drawtext`. libass bundles HarfBuzz + font fallback and shapes
Indic/Arabic correctly. ffmpeg-static has `--enable-libass`.

```bash
# ASS file (tamil.ass):
#   [Script Info]
#   ScriptType: v4.00
#   PlayResX: 1280
#   PlayResY: 720
#   [V4+ Styles]
#   Style: T,Tamil,56,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,5,10,10,20,1
#   [Events]
#   Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
#   Dialogue: 0,0:00:00.00,0:00:03.00,T,,0,0,0,,{\fnNotoSansTamil}நீர் அருந்துவது நல்லது
ffmpeg -y -f lavfi -i color=c=teal:s=1280x720:d=3 \
  -vf "subtitles=tamil.ass:fontsdir=/abs/path/assets/fonts" \
  -t 3 -c:v libx264 -pix_fmt yuv420p out.mp4
```
- On Windows, libass uses the **DirectWrite** font provider and may pick a system
  font (e.g. `NirmalaUI`) before your bundled one. On headless Linux there is no
  DirectWrite -> it relies on fontconfig (often broken) UNLESS you pass
  `fontsdir=` to your bundled fonts AND force the font via `{\fnNotoSansTamil}`.
- The correct architecture: keep `drawtext` for Latin/CJK/emoji (proven path);
  route Tamil/Devanagari/Arabic through libass. The `resolveCaptionFont()` script
  classifier in `compose.ts` already picks the right bundled font -- feed that into
  the libass `{\fn...}` tag.

## 2. Bundled-font CDN gotcha -- notofonts.github.io serves BROKEN subsets

**Symptom:** a "Tamil font" renders tofu despite being loaded. `fontTools` shows 0
Tamil glyphs.

**Cause:** `cdn.jsdelivr.net/gh/notofonts/noto-fonts@main/.../NotoSansTamil-Regular.ttf`
is a **74 KB Latin-only subset** (0 Tamil codepoints). Looks like a font, isn't.

**Fix / source of truth:** fetch full static fonts from the **`google/fonts`** repo
raw (not the notofonts hinted subset CDN):
```
# Tamil is a VARIABLE font there -- instance a static Regular:
curl -fsSL "https://github.com/google/fonts/raw/main/ofl/notosanstamil/NotoSansTamil%5Bwdth,wght%5D.ttf" -o tamil_var.ttf
python -c "
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
f=TTFont('tamil_var.ttf')
instantiateVariableFont(f, {'wght':400}, inplace=True)
for t in ('fvar','gvar','MVAR','STAT','avar'):
    if t in f: del f[t]
f.save('assets/fonts/NotoSansTamil-Regular.ttf')
"
```
**ALWAYS verify glyph coverage before trusting a font** (the 74 KB subset passed
every "does the file exist" check but had 0 Tamil glyphs):
```python
from fontTools.ttLib import TTFont
f=TTFont('assets/fonts/NotoSansTamil-Regular.ttf')
cmap=f.getBestCmap()
print('tamil glyphs:', sum(1 for cp in cmap if 0x0B80<=cp<=0x0BFF))
# also confirm glyphs have outlines, not just cmap entries:
g=cmap.get(0x0B85); print('U+0B85 ->', g, 'contours=', f['glyf'][g].numberOfContours)
```
Latin (2965), Devanagari (128 hits), CJK/SC (30890) from the same google/fonts or
notofonts source were verified complete; only the Tamil subset was broken.

## 3. Verify rendered frames with vision -- it catches fake "proof"

A frame that *looks* like a successful caption render can still be tofu. After
burning captions, extract one frame and run `vision_analyze` on it asking
"readable <script> or empty boxes?". In this session a first "Tamil proof" was
declared done, then vision_analyze revealed tofu boxes -- the font was the broken
subset. **Never claim a non-Latin caption works without a vision check of the
actual rendered frame.** Latin/ASCII via drawtext is a valid control (proves the
font loads); if ASCII works but the script tofus, it's a shaping problem (-> libass).

## 4. GitHub Code-Scanning (CodeQL) alerts -- diagnose & fix

When the user screenshots the repo's Security tab (or says "GitHub shows an error"):
```bash
gh auth status
gh api repos/itsPremkumar/Automated-Video-Generator/code-scanning/alerts?state=open \
  --jq '.[] | "\(.rule.id) | \(.most_recent_instance.location.path):\(.most_recent_instance.location.start_line)"'
gh pr list --repo itsPremkumar/Automated-Video-Generator --limit 15
```
Common alert classes seen (30 open on 2026-08-03):
- `js/incomplete-sanitization` -- ffmpeg `drawtext` text NOT escaped for `\`.
  Fix: use the existing canonical `ffmpegDrawtextEscape()` from `src/lib/ffmpeg-text.ts`
  (escapes `\ : ' " ,`); do NOT hand-roll a partial `.replace(/:/g,'\\:')`.
  Render.ts kinetic-caption path (was line 885) and CJK/Indic font paths (414/418)
  were the live offenders.
- `js/log-injection` -- `console.error(... + args.join(' '))` logs user-derived
  ffmpeg args with newlines -> log forging. Fix: strip CR/LF before logging
  (`safeLog`). NOTE: the `patch` tool mangles a `\n` inside a regex literal -- write
  the strip as `String(s).split(String.fromCharCode(13)).join('').split(String.fromCharCode(10)).join(' ')`
  to avoid a broken `/[\n]/` regex. (This is the same class as the TS6053
  false-positive in verify-and-push-protocol.md -- keep typecheck as the real gate.)
- `js/path-injection` -- a path passed to ffprobe/ffmpeg without NUL/`..` guard.
  Fix: reject `file.includes('\u0000') || file.includes('..')` before probing.
- `js/unused-local-variable` (x15) -- harmless lint hygiene; sweep only if you want
  the alert count to zero. Not security.
- `js/loop-bound-injection` on a benign hash loop -- usually false positive; leave it.

After fixing, `git commit` + `git push origin main` -- CodeQL re-scans on push and
auto-clears the fixed alerts. Stage ONLY intended source files; scratch proof
artifacts (`proof_*.png`, `*.ass`, `*.txt`, driver scripts) stay untracked.
