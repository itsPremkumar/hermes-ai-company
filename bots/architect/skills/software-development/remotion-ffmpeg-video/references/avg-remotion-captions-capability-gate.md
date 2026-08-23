# AVG — Remotion capability upgrade + two durable pitfalls

Captured during the Remotion "use it to full capability" push on
Automated-Video-Generator. The repo had two Remotion codebases (legacy
`src/render.ts` segmented renderer + modern `remotion/AgenticVideo.tsx`) and was
using ~15% of Remotion's real power (crossfade + burned text only).

## 1. `@remotion/captions` v4 API shape (4.0.487–4.0.490)

The package does NOT export `TokenizeText` / `Caption` / `useCurrentTranscript`
in these versions (those came later). The v4 idiom is:

```ts
import { createTikTokStyleCaptions } from '@remotion/captions';

// Input: our already-captured TTS word-boundary cues — exact shape match:
const captionSegments = [{ text: 'Did', startMs: 0, endMs: 400 }, ...];

// Returns: { pages: [{ text, startMs, tokens: [{ text, fromMs, toMs }], durationMs }] }
const { pages } = createTikTokStyleCaptions({
  captions: captionSegments as any,          // accepts {text,startMs,endMs}
  combineTokensWithinMilliseconds: 400,
});

// Active page at frame f (fps F): page whose [startMs, startMs+durationMs) contains nowMs
const nowMs = (frame / F) * 1000;
const active = (pages as any[]).find(p => nowMs >= p.startMs && nowMs < p.startMs + (p.durationMs ?? Infinity));
// Highlight token: tok.fromMs <= nowMs < tok.toMs  -> spoken word (karaoke)
```

This is the single highest-ROI Remotion upgrade: it gives pro-style word-level
karaoke captions that auto-wrap (no hand-rolled `wrapCaptionLines`), driven by
the TTS word boundaries the pipeline already captures. Wrap the component in an
error boundary so a caption failure never aborts the render.

## 2. Remotion needs Chrome — add a capability gate + ffmpeg fallback

`@remotion/renderer` `renderMedia` **silently hangs** (for the full
`timeoutInMilliseconds`, e.g. 9 min) on a host with no Chromium binary. Do NOT
let that block the run. Pre-flight at the top of the render function:

```ts
const { renderMedia, selectComposition, ensureBrowser } = require('@remotion/renderer');
if (!process.env.CHROME_EXECUTABLE) {
  try {
    await Promise.race([
      ensureBrowser(),
      new Promise((_, rej) => setTimeout(() => rej(new Error('Chrome readiness timed out')), 20000)),
    ]);
  } catch (e: any) {
    throw new Error('Remotion renderer unavailable (no Chromium). ' + (e?.message ?? e) + ' — use --renderer ffmpeg on this host.');
  }
}
```

The CLI already wraps `renderAgenticWithRemotion` in try/catch and falls back to
`renderAgenticSlideshow` (ffmpeg-static) — so throwing fast here triggers the
fallback instead of a 9-minute stall.

## 3. PITFALL — ffmpeg `between(t\,...)` backslash escaping in JS template literals

`buildDuckExpression` builds an ffmpeg volume-duck expression
`volume=eval=frame:volume='0.18-0.120*gt(between(t\,0.000\,1.500),0)'`.
The commas inside `between()` must be backslash-escaped (**2 backslashes** at
runtime: `between(t\,0.000\,1.500)`) for ffmpeg.

A JS **template literal** `between(t\,${...}\,${...})` collapses `\,` to `,`
(zero backslashes!) because `\,` is an "unknown escape" that template literals
DROP. A normal string `"between(t\\,0.000\\,1.500)"` gives 1 backslash (wrong).
To get exactly 2 runtime backslashes, use **`String.raw`**:

```ts
// String.raw: source backslashes == runtime backslashes. Write 2 in source => 2 at runtime.
const terms = segs.map((x) => String.raw`between(t\,${x.s.toFixed(3)}\,${x.e.toFixed(3)})`).join('+');
// runtime: between(t\,0.000\,1.500)  (2 backslashes — correct)
```

DO NOT attempt this with a regular template literal + `\\` — it collapses
unpredictably and you'll burn 6+ tool calls chasing the escaping. Use `String.raw`
and write the literal backslash count you want.

### How to verify the runtime value (not guess)
Print the ACTUAL evaluated string, because source-escaping lies:

```ts
import { buildDuckExpression } from './orchestrate.js';
const out = buildDuckExpression([{ durationSec: 4, captionSegments: [{ startMs: 0, endMs: 1500 }] }], 0.18, 0.06);
console.log('ACTUAL:', JSON.stringify(out));   // JSON.stringify doubles backslashes — count them
```

And test the EXPECTED literal the same way — a test's `'between(t\\,0.000\\,1.500)'`
string literal evaluates to 2 runtime backslashes, so it only matches a function
that also emits 2. If the function emits 0 (template-literal collapse), the
`includes()` assertion fails with NO helpful diff — you must dump both values.

## 4. Roadmap that was produced (file REMOTION_UPGRADE.md in repo)

8-step plan: (1) Chrome gate+fallback done, (2) `@remotion/captions` karaoke done,
(3) `Series`+`@remotion/transitions`, (4) `spring()` entrances, (5)
`@remotion/shapes`+`@remotion/gradient`, (6) voiceover waveform via
`@remotion/media-utils`, (7) consolidate legacy `src/render.ts` into
`AgenticVideo`, (8) CI guard for Remotion e2e (Chrome-present only).
Items 1-2 take it from "basic" to "clearly professional"; 3-6 are "full
capability". `@remotion/transitions` is NOT installed by default — add it
before using `@remotion/transitions`.
