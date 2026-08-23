# Lion relevance bug — Automated-Video-Generator (session reproduction)

## Symptom the user reported
"The image and video download is the most important part. It was giving the
wrong image and wrong video — a 'lion' query changed the video's total content."
Earlier runs had already confirmed: downloading "lion" returned NASA space
images, MetMuseum "stone lion"/"sea lion"/"Lion King" art, not real lions.

## File map (where the bug lived)
- `src/lib/free-image/adapter.ts` — `FreeImageAdapter.searchAll` queried
  Wikimedia + Archive + **NASA + MetMuseum** for EVERY keyword; `searchBest`
  ranked by `width*height` only.
- `src/lib/free-image/providers/{nasa,metmuseum,wikimedia,archive}.ts` — raw
  provider search; none checked title relevance.
- `src/lib/visual-fetcher.ts` — `searchFreeImages` did `all.slice(0,count)`
  on the flat provider merge → off-topic appeared first.
- `src/agentic/orchestrate.ts` `fetchVisual` + `src/agentic/gateway.ts`
  `reAcquireScene` → both route through `fetchVisualsForScene` →
  `searchFreeImages`, so the fix propagated to the agentic pipeline too.

## Fix applied (commit 4e02900, pushed to main)
1. Provider gate: NASA only for space regex; MetMuseum only for art regex.
2. `isOnTopic` static: whole-word `\b` match + off-topic compound exclusions
   (stone lion / sea lion / lion king / lioness / mountain lion / city lion).
3. Relevance-first ranking in `searchBest`.
4. Same filter mirrored in `visual-fetcher.searchFreeImages`.
5. 3 OFFLINE `node:test` cases added (always run, incl. CI).
6. `bin/verify-lion-relevance.ts` manual proof script (7/7 checks).

## Verification results
- typecheck 0 errors; lint 0 errors.
- Free-image suite: 14 tests / 7 pass / 7 skip (7 skipped = network tests
  guarded by CI env); the 3 new OFFLINE tests are in the passing 7.
- Full suite: 463/419/36/8. **The 36 failures are PRE-EXISTING** — proven via
  `git stash` baseline (460/416/36/8). They are a Node-version
  `mock.module is not a function` error in `src/adapters/**` test files that
  do NOT import free-image. Not a regression from this fix.

## Known pre-existing CI debt (NOT fixed this session — out of scope)
- `npm run format:check` fails on 6 files committed non-conforming:
  api-routes.test.ts, server-bootstrap.test.ts, videos-controller.test.ts,
  env-tools.test.ts, input-store.test.ts, pipeline-commands.test.ts.
  Fix: `npx prettier --write` on those 6 (pure formatting, zero risk).
- 36 adapter-test failures from Node `mock.module` version mismatch in CI.
  Fix: bump CI `actions/setup-node` to a Node >=22.3 or polyfill `mock.module`.

## .env pitfall (related, fixed same session)
`TTS_PROVIDER=voicebox` with `VOICEBOX_PROFILE_ID=<placeholder>` caused a
Voicebox spawn/retry storm earlier. Correct default: `TTS_PROVIDER=edge-tts`
(free, no key) and leave `VOICEBOX_PROFILE_ID=` empty (opt-in only). The
placeholder profile is treated as unset by `voicebox-lifecycle.ts`.

## Operating cadence the user expects
Commit + push at green checkpoints; never leave work uncommitted across
sessions. Dispatch parallel subagents (max 3 concurrent) for independent
verification/audit work. The user communicates tersely ("continue", "hi",
"d") and wants action over narration.
