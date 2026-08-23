# edit.ts standalone-op bug hunt (2026-07-28) — verified by execution

Test method: import ops from `src/agentic/operations/edit.ts` via `npx tsx` harness on an
8 s 1280x720 25fps AUDIO-LESS mp4 (typical AVS asset) + an audio variant; every output
decode-probed with `ffmpeg -v error -i out -f null -`. Full report:
`workspace/bug-hunt/findings_editing.md` in the repo.

## Confirmed bugs (still present unless fixed since)
1. **trimVideo / splitVideo: `-ss`/`-to` AFTER `-i` + `-c copy` → 262-byte, ZERO-stream
   mp4, ffmpeg exit 0, function returns ok=true.** Stream copy with output-side seek
   encodes nothing ("Output file is empty, nothing was encoded") but exits 0.
   Fix pattern: re-encode when trimming, or validate the output has a stream/duration —
   `fs.existsSync()` is NOT a success check.
2. **interpolateVideo can never succeed:** `minterpolate=mode=blend` — real option is
   `mi_mode=blend` ("Option not found" on every input). edit.ts:255.
3. **changeSpeed crashes on audio-less video** — hard-codes `[0:a]atempo` + `-map [a]`.
   Same class: `addAudio {mix:true}` (`[0:a]...amix`) fails without existing audio.
   AVS-generated visuals commonly have NO audio track: any filtergraph referencing
   `[0:a]` must probe for an audio stream first or add `-f lavfi -i anullsrc`.
4. **atempo range is [0.5, 100]** — docstring promises 0.25x but atempo rejects it
   ("Result too large" error, confusingly). Chain `atempo=0.5,atempo=0.5` for <0.5x.
5. **silenceRemove uses `-af silenceremove` with `-c:v copy`** → audio shortened, video
   untouched → A/V desync; on audio-less input output is byte-identical to input yet
   reports success.
6. **addProgressBar totalSec defaults to 10** instead of probing real duration → bar
   wrong on any clip ≠ 10 s.
7. **crop preset lacks trailing `setsar=1`** → odd SAR (5120:5121), not exact 9:16.
8. **mergeVideos `concat=:a=0`** silently drops all audio.

## Plugin-system finding
`src/agentic/plugins/*` (27 plugins + registry/loader) is only reachable from
`orchestrator/pipeline.ts` (init) and `orchestrator/render.ts:274` (post-render hooks).
`compose.ts` NEVER uses the plugin registry — its "motion plugins" comment refers to
local compose-scene-fx functions. `plugins/integration-example.ts` is dead code.
Don't assume editing a plugin module changes compose output.

## remove-bg
Works via `venv/Scripts/python.exe` + rembg. Fallback is literally `'python3'` string
checked with `fs.existsSync('python3')` → always false on Windows; only the venv path
is viable.

## Harness gotcha
`npx tsx -e "import('./x.js').then(...)"` gave `removeBackground is not a function`
(inline eval module-resolution quirk); a real .ts harness file importing the same module
worked fine. Prefer file-based tsx harnesses over `-e` for dynamic import tests.

## agentic-editor.ts CLI bugs (verified 2026-07-29)
The standalone CLI at `src/adapters/cli/agentic-editor.ts` wraps the edit.ts ops with
its own argument parsing. Three bugs found during batch-generation fuzzing:

1. **Speed audioRate formula inverted (line 160).** `const audioRate = 1 / rate;` —
   for 2× speed this computed `atempo=0.5` (SLOWING audio) when it should be
   `atempo=2.0` (speeding audio). Fix: `const audioRate = rate;`
   The video `setpts=1/rate` is correct; audio `atempo` must be `rate`, not `1/rate`.

2. **Crop accepts `--w`/`--h` but not `--width`/`--height` (line 246-249).** The
   COMMANDS['crop'] handler reads `args.w`/`args.h` but the CLI usage docs say
   `--width`/`--height`. Since `parseArgs()` stores `--width X` as `args.width`,
   the handler always falls back to the default 720×720. Fix:
   `const w = args.w || args.width || '720';`

3. **Resize same arg mismatch (line 263-264).** Same pattern — `args.w`/`args.h`
   instead of accepting `args.width`/`args.height`. Fix: same fallback chain.

**Root cause pattern:** The `parseArgs()` utility (line 108) strips the `--` prefix
but keeps the full flag name (e.g. `--width` → `args['width']`). Every COMMAND
handler that uses abbreviated keys (`w`, `h`, `x`, `y`) MUST have a fallback to
the long form. As of 2026-07-29 the affected commands are crop, resize. Check new
editor commands for the same trap.

## ffprobe is NOT bundled with ffmpeg-static on Windows
`ffmpeg-static` ships only `ffmpeg.exe` — there is no `ffprobe.exe` in the npm
package on Windows. Calling `require.resolve('ffmpeg-static').replace('ffmpeg','ffprobe')`
returns a path to a non-existent binary. Workarounds when `spawnSync` is absent:
- Parse `ffmpeg -i` stderr output (always writes stream info to stderr):
  ```ts
  const r = spawnSync(ffmpeg, ['-i', input, '-f', 'null', '-'], { stdio: 'pipe' });
  const info = r.stderr.toString();
  const dur = info.match(/Duration: (\d+:\d+:\d+\.\d+)/);  // 00:00:15.95
  const vid = info.match(/Stream #0.*Video: (\w+)/);        // h264
  const aud = info.match(/Stream #0.*Audio: (\w+)/);        // aac
  const dim = info.match(/(\d+)x(\d+)/);                    // 1920x1080 -- Caution: this also matches stream index [0x1]!
  ```
- CAUTION: The `(\d+)x(\d+)` dimension regex ALSO matches ffmpeg's stream index tags
  like `Stream #0:0[0x1]`, producing false dimensions `0x1`. Always verify the second
  match occurrence or use `-show_entries` format when possible.
- The project's own `probeAsset()` at `src/agentic/media/asset-checks.ts` also works
  and is the preferred probing path when not doing standalone testing.
- If you must install ffprobe explicitly: `npm install @ffprobe-installer/ffprobe`.
