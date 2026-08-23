# AVG feature build + verify workflow (from 2026-07 session)

Reusable pattern for adding a production feature to the Automated-Video-Generator
agentic pipeline (`src/agentic/`, `src/lib/`) and proving it works.

## Build checklist (per feature)
1. Create the module in `src/agentic/<feature>.ts` (or `src/lib/` if it's a
   shared util, e.g. `asset-cache.ts`). Keep it additive — never break the
   legacy path.
2. Wire it where the pipeline runs:
   - Render-time features → `orchestrate.ts` `writeOutputArtifacts` /
     `renderAgenticSlideshow` opts, and `autopilot.ts` render opts.
   - Config knobs → `config.ts` `AgenticConfig` + `resolveConfig` layering
     (preset → videoType template → user override).
   - Brain decisions → pass `cfg.brain` (maxCalls/maxFails) into `new AgentBrain`.
3. Add `src/agentic/<feature>.test.ts` (node:test, NOT bun:test — bun not
   installed; tsx runs node:test fine).
4. Verify: `npx tsc -p tsconfig.json --noEmit` then
   `npx tsx --test "src/**/*.test.ts"`.

## Verify gates (run after every edit batch)
- `npx tsc -p tsconfig.json --noEmit`  → expect 0 errors.
- `npx tsx --test "src/**/*.test.ts"`  → expect green (baseline 260 pass / 0 fail / 1 skip).
- Commit + push at GREEN (see "Commit discipline" below).

## tsx test-runner pitfalls (Windows/MSYS)
- **Module-load tmp dir ENOENT:** if a test writes temp files using a path built
  at module top-level (`const tmp = path.join(os.tmpdir(), ...)` then
  `fs.mkdirSync(tmp)` at top level), the dir may not exist when the test body
  runs under tsx. Fix: call `fs.mkdirSync(tmp, {recursive:true})` INSIDE each
  `test(...)` body (or a setup helper), not at module scope.
- **Flaky net/asset tests:** one-off failures in acquire/agent batch are usually
  transient (network / file timing). Re-run 2–3x; if stable green, the earlier
  failure was a flake, not a regression. Don't chase a single red run.
- `python3` is NOT on PATH on this box — only `python` (3.11). Scripts using
  `python3` will fail. `py` launcher points to a missing 3.13.

## @remotion/captions API facts (verified)
- `parseSrt({ input: string })` returns `{ captions: Caption[] }` — NOT a direct
  `Caption[]`. Pass an object, not a raw string.
- `Caption` uses `startMs` / `endMs` (NOT `start` / `end`).
- `serializeSrt({ lines: Caption[][] })` — `lines` is an array of arrays
  (one inner array per cue; usually a single-element array per cue).
- Reuse these instead of hand-rolling SRT serialization.

## ffmpeg-static filter pitfalls (verified 2026-07-18, second pass)
The bundled `ffmpeg-static` build on this box is MINIMAL — several common
filters are NOT supported and fail with misleading `Error applying option ...`
/ `Error initializing a simple filtergraph`. Use the safe equivalents below:
- **`curves=all=0.4/0.5/0.6` (and `curves=preset=cinematic`) is REJECTED** —
  `Undefined constant or missing '(' in 'cinematic'`. Do NOT use `curves` for
  color grading. Use `eq=contrast=1.15:saturation=1.05:brightness=-0.02`
  plus `colorbalance=rs=.02:gs=0:bs=-.02:rm=0:gm=0:bm=.02` for a cinematic look.
  `colorbalance` + `eq` ARE supported. (This broke `grade.ts` until switched.)
- When hand-writing a `-vf` chain, validate the EXACT string on a 2s lavfi clip
  via `terminal` (`"$FF" -f lavfi -i "color=c=blue:s=720x1280:d=2" -vf "<chain>"
  -pix_fmt yuv420p -c:v libx264 -y out.mp4`) BEFORE trusting it in a test —
  a bad filter burns a full test run instead of one quick shell call.
- `vibrance=intensity=...` is also dicey on this build; prefer `eq=saturation=`.

## Commit discipline (USER CORRECTION, 2026-07-18)
User flagged uncommitted multi-session work ("why you does not commited the last
changes commit that"). Rule: **commit at GREEN CHECKPOINTS** — after each
feature/module passes tsc + test suite, `git add -A && git commit` then
`git push origin main` (itsPremkumar via cached GCM; `gh` NOT installed).
Do NOT let work pile up uncommitted across sessions even if "more features
coming." User wants persisted + pushed progress, not just code on disk.

## Feature set delivered this session (all committed 7a54aef)
- #6 global disk-backed asset cache (hash→path, TTL) wired into visual-fetcher + free-music
- #1 template engine: VIDEO_TYPE_PROFILES extended + listTemplates()
- #2 localization: localize.ts multi-language SRT sidecars (brain translate, offline fallback)
- #8 publish adapter: publish.ts manifest for 5 platforms + optional YouTube upload helper
- #3 offline word-timing: syllableWordTimings heuristic (word-by-word captions, no native binary)
- #4 brain budget/circuit-breaker: maxCalls/maxFails guards in AgentBrain
- docs/VOICE_CLONING_GUIDE.md: license-verified open-source TTS/voice-clone audit

## Multi-agent feature work — recovery lessons (2026-07-18, third pass)
When a dispatched feature-builder subagent commits BROKEN, UNVERIFIED code and
leaves its branch tangled (uncommitted files + concurrent edits on the same tree):

- **`verification_evidence` parser is UNRELIABLE.** It reports
  `status: passed` even when `npm run typecheck` emits errors. Trust the raw
  `grep -c "error TS"` count (0 = pass). Never trust the JSON verdict.
- **`write_file` silently NO-OPs** when a sibling subagent modified the file
  after your last `read_file`: it returns a "modified since you last read it"
  warning and keeps the subagent's version on disk. Symptom: your edits "don't
  take". Fix: re-read, then re-write; better, work on an ISOLATED branch the
  subagent does not touch (`git checkout -b feat/agentic-ops main`).
- **Subagent may keep editing its branch AFTER it looks done** (uncommitted
  files + continuous rewrites). Its tree is never safe to edit or cherry-pick
  while it runs. Takeover pattern: `git checkout -b feat/agentic-ops main`, then
  port/re-implement the good ops there (READ the agent's real on-disk signatures
  first), verify, merge. Never fight the agent's live tree with in-place edits —
  they'll be blocked or overwritten.
- **Keep `main` GREEN.** Do NOT merge a broken subagent branch. If you already
  cherry-picked it, `git reset --hard <green-sha>` + `git push --force-with-lease
  origin main`, then take the work over cleanly on a fresh branch.
- **Match the agent's REAL op signatures, not your assumptions.** This session
  the agent's ops used: reframe `preset: '9:16'|'16:9'|'1:1'` (not `aspect`);
  noise `{ audio: 'off'|'light'|'medium'|'heavy', video: number }` (not
  `strength`); brand `BrandKit { name?, logo?, color? }` (not `accent`/`handle`);
  silence `parseSilenceLog(log, duration, minDur)` (3 args); scene
  `parseSceneCuts` regex `scene_cut_detected time=(\d+...) score=(\d+...)` with
  `SceneCut.time` / `Chapter.label`. READ the on-disk interfaces before wiring.
- **Test runner is `node:test`, NOT jest.** Write
  `import { test, describe } from 'node:test'; import * as assert from 'node:assert/strict';`
  and assert with `assert.equal/ok/deepEqual`. jest-style `describe`/`expect`
  blows up typecheck with `Cannot find name 'describe'`.
- **Synthetic ffmpeg log strings must match the real regex** (see scene/silence
  formats above) or parse helpers return `[]` and your chapter assertions fail.
- **Don't drop sibling imports** when editing `dispatch.ts` — e.g.
  `DerivativeResult` is used by the `derive` case; re-add it if a patch removes it.
