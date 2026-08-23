# Case study: AVS production-hardening sweep (July 2026)

Worktree `qa/production-hardening` off `da01b10`. Baseline: 685 tests, 665 pass,
5 fail, 2 cancelled. Final: 671 pass / 0 fail after the fixes below.

## Failures and root causes

1. **Music suite 0/4** — `BundledProvider` read `input/bgm/__bundled__/`, which is
   git-ignored, so the fresh worktree had zero tracks. Class of bug: *tests (or
   priority-1 providers) depending on untracked binary assets.* Fix pattern:
   self-healing generator (`bundled-assets.ts` creates procedural CC0 mp3s +
   sidecar JSON with ffmpeg-static when the dir is empty; invoked in provider
   constructor, idempotent). Fresh clones now always work offline.

2. **Test asserting broken behavior** — `enhancement.test.ts` expected
   `between(t\,a\,b)` + `gt()` wrapper in an ffmpeg volume expression. The
   production code was fixed earlier to raw commas (escaped commas make ffmpeg
   reject the expr) but the test was never updated. Lesson: when a renderer bug
   is fixed, grep tests for assertions on the OLD form.

3. **tts.test 120s timeout** — test transitively probed the external Voicebox
   backend. Fix: at test top, `if (CI || !VOICEBOX_API_URL) AGENTIC_VOICE_FALLBACK='1'`.

4. **revise-restitch cancelled after all subtests passed** — leaked
   `ChildProcess(ffprobe.exe)` handle. Found with `process._getActiveHandles()`
   probe (see SKILL.md). Fixes: stdio `['ignore','pipe','ignore']`, `unref()` all
   guard timers, taskkill tree on Windows timeout. Same flaw existed at 3 spawn
   sites + voice-engine safety timer + download stall interval — fix the class.

## Other durable notes
- `npm audit fix --package-lock-only` works fine when node_modules is a junction
  shared with the main checkout (no live install touched).
- `eslint --quiet` = errors only; `-f unix | grep error` does NOT work for
  isolating errors (severity word isn't in that format).
- ffmpeg cannot write PNGs to MSYS `/tmp` paths from a Windows binary
  (`Could not open file` I/O error) — extract frames into a project-relative
  dir (e.g. `workspace/tmp/qa/`).
- `tsx` rejects `--import file:///tmp/x.mjs` on Windows (ERR_INVALID_FILE_URL_PATH);
  copy the probe into the project dir and use `./probe.mjs`.
- CLI arg parsing with truthiness (`argv[i+1] ? val : fallback`) silently converts
  an explicit empty `--topic ""` into the default — use `!== undefined` so
  validation can fire.
