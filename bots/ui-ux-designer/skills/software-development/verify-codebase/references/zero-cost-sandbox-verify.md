# Zero-cost empirical verification in a no-API-key / offline sandbox

Pattern proven on the Automated-Video-Generator project (Windows, git-bash,
`ffmpeg-static` bundled). Use when the user demands "test everything, including
visually" but no paid keys / backends are available. Prove each feature EXECUTES
with a real engine, never with skip-gates alone.

## The sandbox truth table (what actually runs for free)
- `ffmpeg-static` IS present (`node -e "require('ffmpeg-static')"` → exe path).
  → ffmpeg effects, GIF/webm transcode, poster, contact-sheet, audio normalize,
    music loop ALL run for real. Generate a synthetic clip with:
  `ffmpeg -y -f lavfi -i testsrc=size=640x360:rate=25:duration=3 -f lavfi -i sine=frequency=440:duration=3 -c:v libx264 -c:a aac -shortest clip.mp4`
- Openverse (no API key) image/audio search works → real downloads (CC0 pool is
  small, so "10 eagle images" may yield 2 — that's real, not a bug).
- Edge-TTS / SAPI fallback produces real WAVs offline.
- Voicebox/Kokoro backend is DOWN unless its venv is running → expect ECONNREFUSED;
  that's the correct graceful-degradation path, not a code defect.

## Filtered typecheck (fast, catches ALL our files)
The full `tsc --noEmit` also reports pre-existing errors from `remotion/` and
`node:test` files unrelated to the change. Don't grep the whole log. Filter:
```bash
/c/one/MainRepo/node_modules/.bin/tsc -p tsconfig.json --noEmit 2>&1 \
  | grep -E "src/agentic/operations|src/agentic/ai/agent|src/adapters/cli|src/agentic/pipeline/gateway|src/agentic/media/voice-controller"
echo "EXIT_TSC=${PIPESTATUS[0]}"
```
Zero matches + exit 0 ⇒ our files are clean.

## Real-engine smoke tests (assert on disk, not console text)
- SFX: `resolveSfx()` → files land in `workspace/jobs/<id>/download-sfx/*.mp3`.
- Bulk image: `runBulkImageFetch("eagle", 10, outDir)` → `file` shows real JPEGs.
- ffmpeg fx: `applySceneFx(clip, 0, {clipSpeedByScene:{0:0.5}, filterByScene:{0:'bw'}}, dir)`
  → a NEW clip exists with non-zero size.
- Export: `transcode(clip,'gif',dir)` / `exportPoster` / `exportContactSheet` →
  real artifacts; `file` them to confirm type.
- Structure (pure): `restructurePlan` / `loopPlan` — assert scene counts/order,
  NOT via the same mutated object (the fn renumbers sceneNumber in place; build a
  FRESH plan per assertion or you'll get a false failure from shared mutation).

## Gotcha — shared mutation corrupts multi-assertion tests
`restructurePlan(plan, ...)` mutates the input scene objects' `sceneNumber`.
Reusing one `plan` across several checks makes later assertions see renumbered
data. Always `makePlan()` fresh inside each test case. (This cost one false
test failure before the fix.)

## When a feature can't be end-to-end verified here
State explicitly: "render-stage bake-in of overlays/filters is wired as verified
config + engine-tested modules, but the final hook into the Remotion composition
is not yet plumbed." Then show the config reachability proof (`apply-advanced`
mode listing every signal applied) + the standalone engine test. Never fake the
end-to-end run.
