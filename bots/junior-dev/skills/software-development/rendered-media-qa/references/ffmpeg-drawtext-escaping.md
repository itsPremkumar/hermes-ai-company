# ffmpeg drawtext escaping — condensed knowledge bank

Source: a full production-hardening sweep of an ffmpeg-based video generator
(Node 22 + ffmpeg-static 6.1.1, Windows). These are the rules that cost hours
to rediscover; they are stable facts about ffmpeg + this codebase's build path.
Updated after the session that found the apostrophe-leak + measured the real wrap
factor.

## The apostrophe leak (CRITICAL, gate-invisible) — NEW
Symptom: burned caption shows `...you'll see:fontcolor=0xFFFFFF:fontsize=30:...:
enable=between(t,3.14,6.00)` as VISIBLE TEXT. Every automated gate (X7-X15) passes.

Root cause: ffmpeg's drawtext does NOT accept the filtergraph `'` -> `'\''` escape.
It closes `text='...'` early and renders the rest of the filter as text.

Confirmed by repro (render + vision-check):
```js
const { execFileSync } = require('child_process');
const ff = require('ffmpeg-static');
// BROKEN: '\'' escape leaks the whole filter string as on-screen text
const bad = "text='Apply...you'\\''ll see':fontcolor=0xFFFFFF:...";
// FIXED: typographic ' (U+2019) — renders correctly, no leak
const ok  = "text='Apply...you’ll see':fontcolor=0xFFFFFF:...";
```
Rule: `ffmpegDrawtextEscape` must do `.replace(/'/g, '’')` (curly), NEVER
`.replace(/'/g, "'\\''")`. The kinetic-overlay path already used curly `'` and
worked; the caption-burn path using `'\''` was the bug. This passes all
automated gates and only shows in VISUAL QA.

## Backslash counts in the .ts SOURCE (not the final ffmpeg arg)
ffmpeg receives the filter after one more escaping layer (segmented render path
double-escapes; main path single-escapes). Empirically correct source forms:

| Usage | Source must contain | ffmpeg sees | Notes |
|-------|---------------------|-------------|-------|
| caption/kinetic `enable='between(t,start,end)'` | `\\\\,` (2 bs) | `\,` | 1 or 3+ => "Missing ')' or too many args" |
| `buildDuckExpression` duck term `between(t,s,e)` | `\\,` (1 bs) | `\,` | audio-ducking; DO NOT normalize to 2 |
| `text='...'` literal comma | `\,` | `,` | inside drawtext text arg |

Rule: keep the escaping IDENTICAL to a known-good sibling line in the same file
when editing. NEVER "normalize all `between(t...)` to one count" — the caption
path (2 bs) and duck term (1 bs) differ.

## `ffmpegDrawtextEscape` (src/lib/ffmpeg-text.ts) turns `\` -> `/`
Consequence: a literal `\n` you put in drawtext text becomes `/n`; ffmpeg will NOT
break lines. So **ffmpeg drawtext has no auto-wrap** — long captions overflow the
right edge and get silently truncated (X-gates don't catch it; only vision does).

## Correct caption wrapping (measured, not guessed) — CORRECTED
ffmpeg drawtext has NO auto-wrap. Emit one drawtext layer per wrapped line.
Measured Arial advance at our settings: avg glyph ≈ **0.62 × fontsize**.
The old factor `frameW*0.82/(fontsize*0.62)` allowed ~10% too many chars/line and
OVERFLOWED. Use this conservative formula (the `64+12` = 64px margin + 12px for
boxborderw=10 box):
```ts
const sidePad = 64 + 12;
const maxChars = Math.max(8, Math.floor((frameW - 2 * sidePad) / (fontsize * 0.65)));
```
Sanity check that caught the bug: a known 62-char line at fontsize 30 MUST split
into two lines, not stay one line. If it stays one line and overflows, the factor
is still too generous. (The wrapped-line emission pattern with `y = baseY - li*lineH`
is unchanged from the prior version of this file.)

## Ghost / duplicate caption
If captions are burned AND a kinetic `lowerthird` overlay runs, the two text
layers stack at the bottom => semi-transparent ghost. The MAIN path already gates
kinetic on `opts.captions === 'none'`; the SEGMENTED per-scene kinetic block
historically did NOT — that was the ghost. Mirror the `captions === 'none'` gate in
BOTH paths. Visual-verify a frame where a kinetic cue fires.

## Verification of escaping
Don't eyeball backslashes. Script it:
```js
const lines = fs.readFileSync('src/.../orchestrate.ts','utf8').split('\n');
const m = lines[n-1].match(/between\(t(\\+),/);
console.log('backslashes before comma:', m ? m[1].length : 'n/a');
```
(JSON.stringify doubles each backslash — a file count of 4 real backslashes shows
as 8 in JSON output; subtract accordingly.)
