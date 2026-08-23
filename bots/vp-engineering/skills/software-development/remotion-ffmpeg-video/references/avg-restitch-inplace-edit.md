# AVG: In-place master re-stitch (edit one scene without full re-render)

Context: the "video editor assistant" gap — after `edit` regenerates a single
scene clip (`scene_{N}_edit.mp4`), the old flow forced a FULL re-render of the
entire video. The fix is `restitchMaster(masterMp4, newSceneClip, planPath,
sceneNumber, outPath)`: splice the new clip into the EXISTING rendered master
at the correct timeline offset, preserving audio. This is what a real editor
does — operate on the MP4, not the pipeline.

## The proven ffmpeg recipe (works on this box)
1. Read per-scene durations from `plan.json` (the SOURCE OF TRUTH).
2. `cutAt` = sum of durations of scenes before `sceneNumber`.
   `sceneDur` = duration of scene `sceneNumber`.
   `planTotal` = sum of ALL scene durations.
   `partBDur` = `Math.max(0, planTotal - cutAt - sceneDur)`  ← derive from PLAN,
   NOT from the master file (see pitfall 1).
3. Split the master:
   - `partA` = `ffmpeg -i master -t cutAt -c:v libx264 -pix_fmt yuv420p -c:a aac partA.mp4`
     (re-ENCODE, not `-c copy` — accurate cut regardless of keyframes)
   - `norm` = re-encode the new scene clip to project size/fps:
     `-vf scale=720:1280:force_original_aspect_ratio=decrease,pad=...,setsar=1,fps=25,format=yuv420p -c:a aac -t sceneDur norm.mp4`
   - `partB` (only if `partBDur > 0.1`): `-ss (cutAt+sceneDur) -i master -t partBDur ...`
4. Concat via the **concat FILTER**, never the concat demuxer:
   `-filter_complex "[0:v][0:a][1:v][1:a]concat=n=N:v=1:a=1[v][a]" -map [v] -map [a]`
   where N = number of parts (2 if last scene, 3 otherwise).

## Pitfalls (each burned a turn this session)
1. **Keyframe-padding master → wrong tail.** A naive `-c copy` concat of two
   2s clips produces a 5s master (keyframe/container padding). If you derive
   `partBDur` from `masterDur` (`masterDur - cutAt - sceneDur`), you splice in a
   spurious ~1s tail → concat filter gets a degenerate audio-only `partB`
   (0.04s, no video stream) → `Stream specifier ':v' matches no streams` error.
   FIX: derive cut points from the PLAN, not the master. The master may be
   longer than the plan total; that padding is dropped (correct — it's padding).
2. **concat demuxer (`-f concat -i list.txt -c copy`) mis-reports/desyncs.**
   Across two independently re-encoded clips it produced a 5s file from [2s,2s]
   inputs. The concat FILTER is bulletproof here. Do NOT use `-c copy` for the
   final join.
3. **Skip near-zero tail.** `if (partBDur > 0.1)` — a 0.04s tail is an
   audio-only clip that breaks the filter. Treat <=0.1s as "this is the last
   scene" (parts=[A, norm] only).
4. **node:test stale-file double-run.** When the test reruns on a reused temp
   dir, a previous run's `out.mp4` can be read as "5s" because the assertion
   measured a stale file. FIX in tests: use a UNIQUE `out` filename per run
   (`restitched_${Date.now()}_${rand}.mp4`) and `fs.rmSync(out, {force:true})`
   before calling restitch. Also avoid `estimateAudioDurationSafe` on a path
   that may be stale.

## Test recipe (node:test + tsx, no network)
- Generate fixtures with `ffmpeg-static` lavfi sources:
  `color=c=red:s=720x1280:d=2` + `sine=frequency=440:duration=2 -ac 1 -t 2 -c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac`.
- Build the test master by re-encoding the concat (NOT `-c copy`) so its
  duration matches the plan exactly.
- Assert the restitched output duration ≈ `planTotal` (e.g. 4s for two 2s
  scenes), not the padded master duration.
- `assert.ok(dur >= 3.5 && dur <= 4.5)` style tolerance; ffprobe/container
  duration is ~4.0x, not exactly 4.000.

## Where the code lives
- `src/agentic/operations/restitch.ts` — `restitchMaster()`.
- Wired into `src/adapters/cli/agentic-modular.ts` `runEdit`: after rendering
  `scene_{N}_edit.mp4`, auto-stitch into the existing master (Gap C closed).
- HTTP: `POST /jobs/:id/restitch` in `src/adapters/http/editor-controller.ts`.
