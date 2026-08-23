---
name: remotion-composition-audit
description: Find real rendering bugs in Remotion (v4) React composition code (remotion/*.tsx and referenced components). Verifies every suspected API misuse against the installed package source before reporting it, and prioritizes by rendering impact.
triggers:
  - "find bugs in the Remotion composition"
  - "review remotion/*.tsx"
  - "audit the composition / render layer"
  - "check Remotion scenes / transitions / captions / karaoke for bugs"
  - static review of a @remotion/*-driven render
---

# Remotion Composition Audit

Class-level skill for reviewing Remotion v4 composition/render code for bugs that
actually break playback or rendering — not style nits. Covers scene sequencing,
transitions, captions (karaoke/subtitle), shape accents, motion blur, and async
media (waveforms/audio).

## When to use
The user asks to find/audit bugs in Remotion compositions (`.tsx` under `remotion/`
or any `@remotion/*`-driven render), or to review a PR touching the composition
layer. Also the bug-finding half of a render-QA pass.

## Method — do NOT guess, VERIFY
1. Read every file in the composition set, PLUS any referenced components that are
   NOT in the same folder. If `AgenticVideo.tsx` imports `./SubtitleOverlay`, read
   `SubtitleOverlay.tsx` too — a missing import path is itself a bug signal.
2. For every *suspected* API misuse, confirm against the installed package BEFORE
   reporting it. Pattern:
   - Locate the package: `find node_modules/@remotion/<pkg>/dist -name "*.d.ts"`
   - Read the signature (`.d.ts`) AND the implementation (`.js`) to see real
     defaults and runtime behavior.
   - Confirm `useCurrentFrame()` returns the Sequence-local frame:
     `cat node_modules/remotion/dist/cjs/use-current-frame.js`
     (look for `return frame - contextOffset`).
   - Confirm `makeArrow({})` defaults:
     `cat node_modules/@remotion/shapes/dist/utils/make-arrow.d.ts` and `.../make-arrow.js`.
   - Confirm `CameraMotionBlur` multiplicity:
     `cat node_modules/@remotion/motion-blur/dist/cjs/CameraMotionBlur.js`.
3. Prioritize by rendering impact (invisible output > wrong layout > cosmetic) and
   cite `file:line` + the evidence line. Do NOT edit files unless explicitly asked.

## Verified Remotion v4 gotchas (real bugs seen in the wild)
Full evidence-backed list: `references/remotion-v4-gotchas.md`. The high-value ones:

- **Double-subtracting the Sequence `from` offset.** `useCurrentFrame()` inside a
  `<Sequence from={N}>` ALREADY returns the frame relative to `N`. Doing
  `local = frame - from` again makes `local` negative; `interpolate(local,...)`
  clamps to 0 and `opacity = Math.min(fadeIn,fadeOut)` becomes 0 → scene renders
  invisible / crossfade never fires. Fix: `local = frame`.
- **`<Audio>` duplicated inside `CameraMotionBlur`.** `@remotion/motion-blur`'s
  `CameraMotionBlur` renders `children` once per `samples`, each inside a `<Freeze>`.
  Putting `<Audio>` (or any single-instance media) inside it stacks N copies. Keep
  per-scene audio OUTSIDE the blur wrapper.
- **`getAudioData` is browser-only + needs a URL.** `@remotion/media-utils`
  `getAudioData(src)` throws `"getAudioData() is only available in the browser."`
  in headless render and `fetch`es `src` directly — pass `staticFile(audioPath)`,
  not a bare relative path. On headless failure it must degrade (render null) or
  the waveform feature is silently dead.
- **`makeArrow({})` does not fit a centered `viewBox`.** Unlike `makeStar`/
  `makeCircle`/`makePolygon` (centered at `(size/2,size/2)`), `makeArrow`'s default
  path (length 300, headWidth 185) is offset and overshoots a small `viewBox` →
  clipped/invisible. Center it or scale the viewBox.
- **Trust code, not comments.** `KaraokeCaptions` comments "wrapped in an error
  boundary" but has none (unlike `SubtitleOverlay`). Verify the actual tree.

## Pitfalls to check while reviewing
- Module-level mutable globals set during render (e.g. `_widthForSlide = vw`) to
  smuggle props into a child are fragile under concurrent render / fast refresh.
  Prefer passing the prop explicitly.
- `createTikTokStyleCaptions({captions, combineTokensWithinMilliseconds})` accepts
  `{text,startMs,endMs}` — `Caption.timestampMs`/`confidence` are optional, so `as any`
  casts there are safe, NOT a bug.
- Last-scene tail can be clipped when outro duration < crossfade overlap, because
  `totalFrames = t + outroDur` yet the final Sequence runs `dur+overlap`.
- Confirm whether `transitions.tsx` / `path-morph.tsx` / `animated-entrances.tsx`
  are actually imported. Dead code carrying a latent bug (e.g. the arrow case) is
  lower priority but worth flagging.
