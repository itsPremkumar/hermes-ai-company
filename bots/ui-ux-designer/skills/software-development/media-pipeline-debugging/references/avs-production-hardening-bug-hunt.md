# Case log: AVS production-hardening bug hunt (July 2026)

Worktree `C:/one/avs-production-hardening`, branch `qa/production-hardening`.
Method: render real videos → ffprobe + blackdetect + freezedetect + volumedetect
+ mid-video frame extraction + vision_analyze on every output. Every bug below
was found EMPIRICALLY (static checks all green).

## Bugs found → fixes (commit refs in that branch)

1. **Process leaks** (`src/agentic/orchestrator/ffmpeg.ts`, `voice-engine.ts`,
   `visual-fetcher/download.ts`) — ffprobe spawns with stdin pipe + un-unref'd
   timers kept node:test alive 60–240s. Fix: stdio `['ignore','pipe','ignore']`,
   `unref()` all guard timers, `taskkill /T` on timeout. Traced via
   `process._getActiveHandles()`.
2. **Offline music dead in fresh worktrees** — `input/bgm/__bundled__/` is
   git-ignored → BundledProvider (priority 1) empty. Fix: self-healing
   `bundled-assets.ts` generates procedural CC0 beds with ffmpeg-static on
   construction.
3. **Wikimedia provider returned PDFs/DjVu as "images"** — Commons namespace-6
   search includes non-image media; one run burned 938 throttled (429) requests
   downloading interest-table PDFs. Fix: request `iiprop=mime`, accept only
   `image/*`, reject pdf/djvu/av extensions.
4. **Caption overlap at scene boundaries** — `gte(t,s)*lte(t,e)` enable windows;
   fixed to `lt(t,e)` (half-open). Caught only by vision review of an extracted
   frame.
5. **Frozen 5s segment** — image scene received `.webm` from a fallback
   provider, rendered as a still. Fix: reclassify candidate kind by actual
   extension in `acquire.ts`.
6. **36-minute silent hang** — stall guard `destroy()` without error → download
   promise never settled. Fix: `destroy(new Error(...))` + `'close'` reject
   guard.
7. **Stopword keywords** — `writeScriptHeuristic` visuals for "the". Fix: STOP
   set filter in topicParts; regression test `keyword-hygiene.test.ts`.
8. **CLI truthiness** — `arg()` used truthy check so `--topic ""` fell to the
   default instead of validation; use `!== undefined`.

## Environment/ops notes (this box)
- Windows, RAM-starved (~1GB free): kill hogs before long renders
  (`taskkill /PID <id> /F`), serialize renders one-at-a-time.
- Background `npm run agentic ... | tail` is pipe-buffered → blind. Redirect to
  a log file (`> /tmp/run.log 2>&1`) and tail the file instead.
- Per-video QA one-liner set:
  ```bash
  ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height -of default=nw=1 V.mp4
  ffmpeg -i V.mp4 -vf blackdetect=d=0.5:pix_th=0.05 -an -f null - 2>&1 | grep -c black_start
  ffmpeg -i V.mp4 -vf freezedetect=n=0.001:d=2 -an -f null - 2>&1 | grep -c freeze_start
  ffmpeg -i V.mp4 -af volumedetect -vn -f null - 2>&1 | grep mean_volume
  ffmpeg -y -ss <mid> -i V.mp4 -frames:v 1 frame.png   # then vision_analyze
  ```
- node:test with `--experimental-test-module-mocks` is REQUIRED for suites using
  `mock.module` — running a single test file without the flag gives
  `mock.module is not a function` (false failure).
- `test:unit` flags for slow boxes/CI parity: `--test-timeout=240000
  --test-concurrency=2`.
