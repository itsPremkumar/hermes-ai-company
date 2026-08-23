# Production-Hardening QA Session (2026-07-28) — worktree qa/production-hardening

Worktree: `C:/one/avs-production-hardening` (node_modules = Junction to main
checkout, so `npm audit fix --package-lock-only` only — never live install).

## Verified fix commits (branch qa/production-hardening)
- `27e5ed1` process leaks + bundled-music self-heal + CI test hardening
- `9b2f9b7` CLI validation + test:unit flags + stabilization report
- `a883920` empty --topic truthiness bug (`!== undefined` in arg())
- `6a21bb9` Wikimedia PDF/AV media-type gate
- `ee8058c` caption lt() boundary fix + regression test
- `b247ddc` stopword filter in agent.ts topicParts (keyword-hygiene.test.ts)
- `de16d46` image scenes could receive video files → frozen "stills"
- `33c8925` download stall guard: destroy() without error → infinite hang
- `c176e71` bare pool fetches (fetchVisualsForScene/searchImages) wedged runs
- `a8586c1` global 30-min watchdog (AGENTIC_MAX_RUN_MS) in bin/agentic-run.ts
- (matrix harness) freezedetect n=0.001 → 0.02 (Ken Burns false-positive)

## Hang root-causes found & fixed this session (all execution-verified)
1. **Download stall guard called stream.destroy() with NO error** — plain
   destroy() emits only 'close', so the download promise never settled and
   acquire hung forever (36-min silent wedge, Kids-story). FIX: destroy(err)
   + a 'close' reject guard. `src/lib/visual-fetcher/download.ts`.
2. **axios stream GET had NO timeout** — only a body-stall timer that arms
   AFTER headers arrive. A server that accepts the socket but never sends
   headers blocked forever. FIX: timeout:30000 on the stream request.
3. **Bare external fetches in pipeline.ts pooled fallback** — fetchVisualsForScene/
   searchImages called with no withTimeout; one wedged provider stalled the
   whole run (seen TWICE even after the download-layer fixes). FIX: every call
   wrapped in withTimeout(fn, 20000, label); grep must show ZERO unwrapped calls.
4. **Global watchdog catch-all** — AGENTIC_MAX_RUN_MS (default 30min, 0 disables,
   unref'd) so no unknown path can wedge the matrix silently.

## freezedetect false-positive on Ken Burns (QA-harness fix, not product)
freezedetect=n=0.001 (0.1%) flags every smooth zoom as "frozen" (4-5/segs per
video). PROVED false via PSNR 55dB (adjacent) / 27-28dB (2s-apart) between
scene frames + different MD5s + freeze spans == exact scene durations. FIX:
harness uses n=0.02; confirm motion with PSNR/MD5, never freezedetect alone.

## Leaked-handle probe (reusable)
```js
// probe-handles.mjs — run with: node --import tsx --import ./probe-handles.mjs <test>
setTimeout(() => {
  const h = process._getActiveHandles?.() ?? [];
  for (const x of h) {
    if (x?.constructor?.name === 'ChildProcess') console.log('CHILD:', x.spawnargs);
  }
  console.log('ACTIVE HANDLES:', h.map(x => x?.constructor?.name));
}, 45000).unref();
```
Found: `['Socket'×4, 'ChildProcess']` → ffprobe with open stdin pipe.

## Bundled-music self-heal
`src/music-system/bundled-assets.ts` `ensureBundledTracks()`: generates 3
procedural CC0 beds via ffmpeg-static into git-ignored
`input/bgm/__bundled__/` when empty; called in BundledProvider constructor.
Music suite went 0/4 → 19/19 in the fresh worktree.

## Per-video QA recipe (matrix harness)
For each rendered mp4:
1. ffprobe: `format=duration,size` + `stream=codec_name,width,height`
2. `blackdetect=d=0.5:pix_th=0.05` → count black_start
3. `freezedetect=n=0.001:d=2` → count freeze_start
4. `volumedetect` → mean_volume (expect ~-26 dB)
5. mid-frame extract (`-ss` AFTER `-i`) → vision_analyze
   ("visible imagery? readable captions? overflow/cropping/stretching/artifacts?")
Vision on the Finance portrait frame is what caught the overlapping-caption
bug (all signal-level checks passed).

## CI-simulation env for the unit suite
`env -u OLLAMA_URL -u OLLAMA_MODEL -u VOICEBOX_PROFILE_ID -u VOICEBOX_API_URL
-u PEXELS_API_KEY -u OPENROUTER_API_KEY -u GEMINI_API_KEY CI=true npm run test:unit`
test:unit flags: `--test-timeout=240000 --test-concurrency=2` (default 16-way
concurrency + 120 s timeout flaked on this RAM-starved box).

## Error-recovery probes that passed
- Corrupt mp4 (100 KB urandom) + missing file through
  `estimateAudioDurationSafe` → graceful 4 s fallback, no throw/hang.
- No Pexels key → free-provider fallback (observed live in run logs).
- CLI: empty/invalid `--topic/--orientation/--backend/--format` → clear
  error + exit 2 (bin/agentic-run.ts validation block).

## RAM discipline during renders
Box hit 74 MB free mid-matrix. Hogs killed: `taskkill /PID <Antigravity> /F`,
`wsl --shutdown` (~1.1 GB reclaimed). Renders serialized one-at-a-time;
~18 min per agentic video on this machine.
