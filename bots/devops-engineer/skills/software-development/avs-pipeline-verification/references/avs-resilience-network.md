# AVS Network-Resilience & Continuous-Campaign Reference

Companion to `avs-pipeline-verification` SKILL.md (the "NEW: network-resilience
layer" + "dead control-signal audit" sections) and `codebase-gap-analysis`
(`references/dead-signal-audit-avs.md`). Captures the Wave G–K learnings so a future
session converges the variety campaign without re-deriving them.

## 1. Network-resilience layer (why full renders stopped truncating)

Symptom across Waves A–F: `waveF_outro_card` repeatedly composed only 1–2 of 3
scenes because Pexels/Openverse blips returned empty media for a scene → the scene
encode `return`ed (dropped) → degenerate short video. Root cause was TWO layers:

### A. Fetch layer had no retry
`searchFreeImages` (Openverse + Wikimedia) failed once → empty array → scene dropped.
Fix: `withRetry(fn, label, maxAttempts=3)` (exported, exponential backoff) wrapping
`searchOpenverseImages` + `freeImageAdapter.searchAll` in `src/lib/visual-fetcher/search.ts`.
Unit test `visual-fetcher/resilience.test.ts` (4 cases) locks it.

### B. No graceful fallback when everything fails
`fetchVisualsForScene` returned `null` on total failure → scene dropped.
Fix: when ALL providers empty, return `generatePlaceholderAsset(query, orientation)` —
a local ffmpeg `lavfi color=c=<bg>:s=720x1280` card with the keyword burned via
drawtext (no network, no deps). The slideshow keeps its FULL scene count.
- Coerce for internal use: `const cacheOrientation = orientation==='square' ? 'portrait' : orientation`
  (cache-key helpers + free-adapter + placeholder only understand portrait/landscape/none;
  Pexels `searchVideos`/`searchImages` get the real `'square'` since Pexels supports it).
- `generatePlaceholderAsset` uses `ffmpegPath()` + `C:/Windows/Fonts/seguiemj.ttf` is NOT
  needed (plain drawtext). Returns a `MediaAsset {type:'image', localPath}` so downstream
  never drops the scene.

### C. Music fallback hung the whole pipeline
`resolveFreeBackgroundMusic` legacy loop tried CcMixter (15s timeout) → InternetArchive
BEFORE the offline `FallbackToneProvider`. On a bad-network day this spun >60s and the
mix stage never ran. Fix: `defaultProviders()` lists `FallbackToneProvider` (name
`'bundled'`) FIRST; also a `prefersBundled` guard skips the online engine when
`preferProviders` includes `'bundled'`. (commits `5a128b2`, `1e9181a`.)

Also `free-music.ts` `FallackToneProvider.name` was renamed `'bundled'` so the offline
path actually returns `provider:'bundled'` (was the silent bug behind "bundled" tests
failing). (commit `1e9181a`.)

## 2. The verification discipline that converges the campaign
A "done" feature is NOT proven until a REAL render shows it. Unit tests + typecheck
pass even when a field is a no-op (the whole point of the dead-signal audit).

1. Append a minimal job to `input/scripts/agentic-scripts.json` exercising ONLY the new
   field (e.g. `{platform:'youtube'}` with no `aspect`/`orientation`). Keep a `.bak`.
2. Render: `npx tsx src/adapters/cli/agentic-batch.ts --mode compose --job <id> > /tmp/<id>.log 2>&1`
3. `ffprobe` the `final.mp4` for dimensions (`width`/`height`) — decisive for aspect/square.
4. Extract ONE frame and `vision_analyze` it: "is the text orange?" (brand.accent),
   "does the end-card show CTA + SUBSCRIBE + hashtags?" (outro), etc.
5. Add a pure-function unit test (precedence matrix, 12–20 cases) so the gap can't
   regress without a slow full render.

## 3. Windows / tooling gotchas that burned cycles (don't repeat)
- **`execute_code` `node -e` JSON writes can silently not persist** (sandbox cwd
  mismatch). After writing `agentic-scripts.json` via a script, re-read it in a separate
  `terminal` call. A render exiting "No jobs matched filter" = the write didn't land.
  (This happened twice this campaign — wk1/wi2b.)
- **Background renders need >60s.** `process(wait)` caps at 60s; a full 3-scene kitchen-
  sink encode at ~800MB RAM takes 90–120s. Don't conclude "hang" at 60s — poll
  `ffprobe final.mp4` / `ps` for ffmpeg, or launch with `timeout 200` +
  `notify_on_complete`.
- **Stale-final.mp4 masking.** `compose.ts` now `rm -f final.mp4` at the start of the mix
  stage so a failed/skipped mix can't leave a stale good-looking video behind (was
  masking the aspect fix in earlier waves).
- **`tsc --noEmit` is SLOW** — run foreground with `timeout: 180`, or accept a "timed
  out" and re-run; a clean run prints nothing + `TC 0`.
- **Re-verify is a cache gate.** When asked to "re-run verification," run
  `npm run typecheck` + targeted `*.test.ts` + `git status --porcelain` / `git diff HEAD`
  to prove the tree is clean; flagged "changed files" are usually already committed.

## 4. Dead control-signals fixed (cross-ref dead-signal-audit-avs.md for full detail)
- `platform` (AI-hint only → drives aspect via `resolveOutputSize`)
- `aspect:'square'` / `orientation:'square'` (only `'1:1'` matched → portrait)
- `brand.accent` (declared, only Remotion read it → now tints ffmpeg captions)
- voice default `en-US-GuyNeural` (timed out on flaky TTS → pinned `en-US-JennyNeural`,
  root cause was `voice-intel.ts` overriding `plan.voice` downstream)
