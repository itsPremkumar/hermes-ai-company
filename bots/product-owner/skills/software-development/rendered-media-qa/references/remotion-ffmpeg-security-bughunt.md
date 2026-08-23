# Remotion + ffmpeg + security bug-hunt hit-list (AVG, 2026-07-20)

A concrete, reusable checklist of the real bugs found in one full sweep of the
Automated-Video-Generator. Use it as a triage map + verification recipe for the
next "test/fix everything" pass. Each item: location - bug - fix - how to prove.

## 1. CRITICAL - Remotion <Sequence> double-subtracts the frame
- Where: remotion/AgenticVideo.tsx TransitionedScene (const local = frame - from;)
- Why: the component is inside <Sequence from={from}>, where useCurrentFrame()
  already returns the local (offset) frame. Subtracting `from` again makes
  `local` negative for the first `from` frames of every non-first scene so
  fadeIn clamps to 0 -> black gap + broken crossfade.
- Fix: const local = frame;
- Prove (visual): render a >=2-scene clip (intro + 2 scenes + outro, each with
  audio to also exercise the waveform). Extract frames at the scene boundaries
  (t~1.6s, 2.0s, 4.6s, 5.0s for a 30fps 2-scene clip) and vision_analyze each -
  every frame must show content (no black gap). The waveform bars at the scene
  bottom also prove the VoiceoverWaveform fix.

## 2. P0 - ffmpeg zoompan comma crash
- Where: src/agentic/orchestrate.ts:~1242 (zoompan=z=min(zoom+0.0008,1.04))
- Why: unescaped comma inside min() -> ffmpeg parses it as a filter separator
  -> "[AVFilterGraph] No option name near '1:s=720x1280'".
- Fix: escape as \, in the runtime string (source min(zoom+0.0008\\,1.04)).
- Prove: render a Ken-Burns image scene; if it crashes, the comma is the cause.
  Confirm the runtime string with node -e (count backslashes).

## 3. HIGH - path-traversal startsWith boundary bypass
- Where: src/infrastructure/filesystem/local-filesystem.ts
  assertPathWithinProject + getViewFile.
- Why: startsWith(projectRoot) accepts <root>_evil/...; and getViewFile accepted
  absolute rawPath (bypassing ..-normalization).
- Fix: allowed = resolved === projectRoot || resolved.startsWith(projectRoot + path.sep);
  reject absolute paths in getViewFile.
- Prove: unit test getViewFile('C:\\Windows\\system.ini') and
  getViewFile('<root>_evil/secret.txt') both throw; a real public/ file is
  served. (4 regression tests added.)

## 4. P1 - verifyMedia fail-open bypasses fail-closed
- Where: src/lib/media-verifier.ts (unsupported-format / no-frame /
  unreadable-file branches returned passes:true).
- Fix: route all three through unavailableResult(...) (honors failClosed).
- Prove: unit test verifyMedia('/tmp/x.xyz', [...], {failClosed:true}) and
  verifyMedia('/tmp/missing.png', [...], {failClosed:true}) -> passes===false.

## 5. P1 - auto free-music double-prefix
- Where: src/video-generator.ts:~363 (backgroundMusic = 'music/__auto__/'+basename).
- Why: resolveFreeBackgroundMusic already returns an absolute localPath under
  input/music/__auto__/; re-prefixing makes it input/music/music/__auto__/...
  -> never found -> auto-music silently skipped.
- Fix: backgroundMusic = freeMusic.localPath;
- Prove: functional - with AUTO_FREE_MUSIC on, confirm the resolved music path
  exists and is passed through; or unit-test the string assembly.

## 6. MED - download endpoints missing local-only auth
- Where: src/adapters/http/api-routes.ts (/video-download/process,
  /social-download/process, /free-video/*).
- Fix: add requireLocalAccess to each (siblings already had it).

## Reusable sweep recipe
1. Fan out 3 READ-ONLY leaf subagents (Remotion comps / agentic pipeline+render /
   HTTP+MCP server+CLI). Treat their output as UNVERIFIED hypotheses.
2. Re-confirm every claim against source + a runtime repro (zoompan crash, the
   startsWith bypass, the power-of-two throw) before fixing.
3. For each fix: typecheck + lint + targeted unit test; for Remotion fixes, a
   REAL Chrome render + frame vision-check.
4. Commit at green, push. The repo uses Node's built-in node:test (NOT jest);
   test:unit = node --import tsx --test --experimental-test-module-mocks
   "src/**/*.test.ts" "remotion/**/*.test.ts".
