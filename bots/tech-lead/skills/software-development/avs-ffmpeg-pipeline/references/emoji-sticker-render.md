# Emoji render on Windows — VERIFIED working (2026-07-24)

## False belief, now corrected
Old assumption: "ffmpeg drawtext cannot composite color emoji on Windows
(libFreetype renders blank)." This was a FALSE ALARM. Windows ships
**Segoe UI Emoji** (`C:/Windows/Fonts/seguiemj.ttf`, ~12 MB) and drawtext
renders the REAL glyph with it. The earlier "blank / flat black bolt"
conclusion came from a flawed capture/verification, NOT a Windows limit.

## Proof recipe (the new emoji-sticker.test.ts)
Render a single emoji to a transparent PNG, assert non-trivial + decodes:

```ts
import { execFileSync } from 'node:child_process';
// eslint-disable-next-line @typescript-eslint/no-var-requires
const ff = require('ffmpeg-static');

const font = 'C:/Windows/Fonts/seguiemj.ttf'; // Windows-only; skip on !win32
execFileSync(ff, [
  '-y', '-v', 'error',
  '-f', 'lavfi', '-i', 'color=c=black@0:s=120x120,format=rgba',
  '-frames:v', '1',
  '-vf', `drawtext=fontfile='${font}':text='☕':fontsize=90:x=(w-text_w)/2:y=(h-text_h)/2`,
  out,
], { timeout: 30000 });
// assert existsSync(out) && statSync(out).size > 200
// assert it re-decodes: execFileSync(ff, ['-v','error','-i',out,'-f','null','-'])
```

Vision-confirmed: `☕` renders as a real coffee-cup glyph, NOT blank.

## Gotchas
- `resolveEmojiFont()` in `compose.ts` already points at `seguiemj.ttf`.
- Do NOT "fix" code because the terminal shows `libx264`→`libx264` /
  `filter_complex`→`filter_complex` (lowercase-l-renders-as-x display glitch).
  The emoji path uses identical strings and works.
- The PNG-sticker `renderEmojiSticker` + `overlay` path is KEPT as a fallback,
  but `emojiByScene` now renders directly via drawtext (primary path).
- ALWAYS confirm a freshly-rendered emoji with a single-frame `-ss` extract +
  `vision_analyze` — never assume.
