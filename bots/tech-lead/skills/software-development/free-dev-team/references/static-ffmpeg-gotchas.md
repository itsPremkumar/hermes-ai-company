# Static ffmpeg gotchas (ffmpeg-static build)

When building **free, offline asset-creation** engines (images/video/audio/GIF) with
`ffmpeg-static`, the bundled binary lacks features a full ffmpeg has. These bit us
while building `C:\one\asset-creator` (all verified by tests after fixing). Record so
they don't recur.

## Missing / renamed filters
| Wanted | This build needs | Symptom if wrong |
|---|---|---|
| audio lowpass | `lowpass` (NOT `a-lowpass`) | `Filter not found` |
| `sine=frequency=500*exp(-10*t)` | `aevalsrc='0.4*sin(2*PI*400*t)*exp(-12*t)'` | `sine` freq expr rejects `t` (time) → `Error opening input file` |
| text wrap | manual `wrapText()` + `\n` (NO `wrap_width`) | `Option not found` on `wrap_width` |
| `fontcolor=lightgray` | `gray` (or `white`/`black`/`red`) | `Cannot find color 'lightgray'` → cascades to output-file error |

## drawtext requires a fontfile
Static ffmpeg has **no bundled font**. `drawtext` fails unless you pass `fontfile=`.
Detect a system font:
```js
function fontFile() {
  const c = ['C:\\Windows\\Fonts\\arial.ttf','C:\\Windows\\Fonts\\segoeui.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/System/Library/Fonts/Supplemental/Arial.ttf'];
  return c.find(f => fs.existsSync(f)) || null;
}
// usage: drawtext=fontfile='C:/Windows/Fonts/arial.ttf':text='...'
```
Escape `:` in the font path with `/` (replace `\\` → `/`).

## Output error is a red herring
Most drawtext/filter mistakes surface as `Error opening output file X.png.`
(trailing dot) or `Option not found` — NOT a clear filter message. When you see that,
suspect an invalid color name, missing `fontfile`, or unsupported option in the
`-vf` string. Run ffmpeg directly with the same args and read the FIRST
`[Parsed_...] Cannot ...` line to find the real cause.

## Why ffmpeg-only (no node-canvas)
`ffmpeg-static` is already present; `node-canvas` needs a native compile (unreliable
on the RAM-tight box). ffmpeg covers images (lavfi `gradients`/`color` + `drawtext`),
video (zoompan, alpha drawtext), audio (sine/aevalsrc/amix/lowpass), and GIF
(palettegen/paletteuse). Zero new native deps.

## Reusable engine
`C:\one\asset-creator\src\index.js` — 10 functions (bg/title/quote images, ken-burns/
kinetic/countdown clips, procedural bg music, 5 SFX, GIF, placeholder). 14 tests, all pass.
Consumable by the Automated-Video-Generator agentic pipeline as a fallback asset source
when stock download fails or none exists.
