# Complex-script captions (Tamil/Devanagari/Arabic) — empirical proof + fix

## Symptom
Tamil/Devanagari captions render as empty boxes (tofu) in the AVS final MP4
even though the bundled font is correct and complete. Latin + CJK render fine
via `drawtext`.

## Root cause (verified, not assumed)
ffmpeg-static 6.1.1 bundles `--enable-libfreetype --enable-libharfbuzz`, but its
`drawtext` path cannot shape Indic glyphs — it produces `.notdef` boxes for
shaped scripts. Confirmed:
- Font loads (ASCII "Water Test" renders with the Tamil font).
- Tamil text via `textfile=` (UTF-8, bypasses shell encoding) STILL tofus.
- `text_shaping=true` (default) does not help.
- The font IS complete: `fontTools` shows U+0B85 -> `atamil`, 2 contours.
So the failure is in `drawtext`/freetype shaping, NOT the font and NOT encoding.

## Fix
Route shaped-script captions through the `subtitles` filter (libass), which
ffmpeg-static also enables and shapes Indic correctly. Keep `drawtext` for
Latin/CJK/emoji (proven, fast).

### ASS file (write to disk, reference via `subtitles=`)
```
[Script Info]
ScriptType: v4.00
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Style: T,Tamil,56,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,5,10,10,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:03.00,T,,0,0,0,,{\fnNotoSansTamil}நீர் அருந்துவது நல்லது
```
### ffmpeg (headless-safe: point fontsdir at bundled Noto, avoid fontconfig)
```
ffmpeg -y -f lavfi -i color=c=teal:s=1280x720:d=3 \
  -vf "subtitles=tamil.ass:fontsdir=/abs/path/assets/fonts" \
  -t 3 -c:v libx264 -pix_fmt yuv420p tamil_libass.mp4
```
On Windows libass uses DirectWrite and may pick `NirmalaUI` first — that's fine
(real Tamil). On headless Linux (no fontconfig) `fontsdir=` forces the bundled
Noto Tamil so it does not fall back to the broken system fontconfig.

### Verify (the only truth = vision)
Extract a frame and `vision_analyze` it: ask "readable Tamil with curved
letterforms, or empty boxes?" A correct render shows curved Brahmic glyphs
with pulli dots; tofu shows uniform hollow rectangles.

## Font-source trap (cost this session real time)
The `notofonts/noto-fonts` jsdelivr CDN serves a **74 KB Latin-only SUBSET**
with **0 Tamil glyphs**. It downloads "successfully" and even reports 428 cmap
entries via fontTools — but every Tamil codepoint maps to `.notdef`. ALWAYS
verify a downloaded font before trusting it:
```python
from fontTools.ttLib import TTFont
f = TTFont('NotoSansTamil-Regular.ttf')
cmap = f.getBestCmap()
tamil = [cp for cp in cmap if 0x0B80 <= cp <= 0x0BFF]
glyf = f['glyf']
real = [cp for cp in tamil if getattr(glyf[cmap[cp]], 'numberOfContours', 0) > 0]
print('tamil codepoints:', len(tamil), 'with real outlines:', len(real))
# tamil>0 AND real>0 means the font is usable; otherwise it's a broken subset.
```
Get full static fonts from `github.com/google/fonts/raw/main/ofl/notosanstamil/
NotoSansTamil[wdth,wght].ttf` (variable, 340 KB, 72 real Tamil glyphs), then:
```python
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
f = TTFont('NotoSansTamil[wdth,wght].ttf')
instantiateVariableFont(f, {'wght': 400}, inplace=True)
for t in ('fvar', 'gvar', 'MVAR', 'STAT', 'avar'):
    if t in f: del f[t]
f.save('NotoSansTamil-Regular.ttf')
```
Devanagari/CJK: same CDN-subset caution. google/fonts `ofl/notosansdevanagari/`
and `ofl/notosanssc/` (or notofonts/noto-cjk for SC) are reliable full sources.
