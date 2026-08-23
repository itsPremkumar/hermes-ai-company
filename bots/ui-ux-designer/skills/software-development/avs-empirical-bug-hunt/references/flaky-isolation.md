# Flaky-test vs real-bug isolation

When a repro test fails but the raw ffmpeg command (or the real function in
isolation) succeeds, do NOT ship a fake fix. A flaky harness probe is a TEST
artifact, not a pipeline bug. This session spent real time on exactly this
(BUG A6: `addAudioTrack` dropping audio on silent files).

## Decision procedure
1. **Reproduce raw.** Run the exact ffmpeg args via `execFileSync` (synchronous,
   waits for full flush) and probe the output with ffprobe. If output HAS the
   expected stream → the CLI/command is fine; the test is the suspect.
2. **Loop the real function.** Call the function under test 5× in one script.
   If it's reliable in isolation (all 5 pass) → the bug is NOT in that function.
3. **Diff two repro scripts that disagree.** If script A passes and script B
   fails with identical inputs, find the real variable: input filenames,
   `stdio:'ignore'` vs `'pipe'`, a PRECEDING probe/raw-mux call, cwd. Example
   this session: a preceding `ffprobe` + raw-mux before the async call produced
   a failure that the async call alone did not — pointed to a probe/flush race,
   not the source function.
4. **Test-runner context.** If the failure only appears under `node --test` but
   not a plain script, it's almost certainly a flush/race in the harness probe.
   Fix the TEST (add a settle delay, re-probe, or assert on the sync raw output)
   — do NOT modify source to "make the flaky test pass."

## What NOT to do
- Do not edit `audio-track.ts` (or similar) just because a test failed, when
  isolated calls prove the function works. That ships a fake fix.
- Do not disable/remove the test to make it green. Make the test robust instead
  and document WHY.

## The settle-delay trick
If a probe races the ffmpeg `spawn` `close` event, add a short
`await new Promise(r => setTimeout(r, 200))` before ffprobe in the test, then
re-run. Passing-with-delay confirms a flush race (test artifact).
