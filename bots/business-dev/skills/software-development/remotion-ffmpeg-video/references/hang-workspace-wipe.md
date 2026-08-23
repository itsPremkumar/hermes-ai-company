# Hang-pinpointing recipe: workspace-wipe + network re-fetch (P48 / P47)

Reproduced and resolved in a session that started with the agentic pipeline hanging at
`EXIT=124` on a fully-offline `--local-assets` run. The hang was NOT a sync ffmpeg call
(P45 was already fixed) — it was a *missing asset* making the gateway decide `replace`
and then network-hang.

## Symptom
```
[... only music lines ...]
<nothing for 120s>  -> EXIT=124
```

## Step-by-step diagnosis (no debugger, just markers)
1. Add `[M]` `console.error` markers at stage boundaries in `runAgenticPipeline`
   (`src/agentic/orchestrate.ts`) and inside `runGateway` (`src/agentic/gateway.ts`):
   - after `acquireAssets` -> `[M] acquire done, candidates=N`
   - entry of `runGateway` -> `[M] runGateway entry`
   - before/after `verifyAll` -> `[M] verifyAll start` / `[M] verifyAll done`
   - per candidate in the decide loop ->
     `[M] deciding <id> hasV=<bool> v.passes=<bool> conf=<n>`
   - after the loop -> `[M] gateway done`
2. Run with a SHORT timeout and read the LAST marker:
   ```
   timeout 60 npx tsx bin/agentic-auto.ts --topic "morning coffee routine" --title "Coffee" \
     --no-sfx --local-assets "img1.jpg,img2.jpg,img3.jpg,img4.jpg,img5.jpg,img6.jpg" \
     --max-attempts 1 --aspect 1:1 2>&1 | grep -E "\[M\]"
   ```
3. Observed sequence that pinned it:
   ```
   [M] acquire done, candidates=7
   [M] runGateway entry, candidates=7
   [M] verifyAll start
   [M] verifyAll done; vIds=image_s0_c1,image_s1_c1,image_s2_c1,music_s-1_c1,...
   [M] deciding image_s0_c1 hasV=true v.passes=false conf=0
   [M] decided image_s0_c1 -> replace      <-- replace on a LOCAL asset!
   [M] deciding image_s1_c1 hasV=true v.passes=false conf=0
   [M] decided image_s1_c1 -> replace
   ... then hang (reAcquireScene -> fetchVisual -> network)
   ```
   Key tell: `hasV=true` but `v.passes=false conf=0`. The verification EXISTS in the map
   (`hasV=true`) but its `passes` never got the stub's `true/conf=6` — meaning the source
   check saw a MISSING file. So the asset was deleted between acquire and verify.

## Root cause
`gateway.ts` called `createAgenticWorkspace(plan.jobId)` which WIPES `assets/images/*`
and `assets/videos/*`. `acquireAssets` had already populated those dirs, then `runGateway`
wiped them. `verifyAll` ran on absent files -> `passes:false` -> `replace` -> network hang.

## Fix
- `workspace.ts`: add `getAgenticWorkspace(jobId)` (mkdirs only, no wipe); keep
  `createAgenticWorkspace` (wipes) for the once-per-job acquire call.
- `gateway.ts`: `import { getAgenticWorkspace }` and `const ws = getAgenticWorkspace(plan.jobId);`
- (P47 defense-in-depth) wrap `fetchVisual` in `orchestrate.ts` with `withTimeout(..., 12000)`
  so even a `replace` can't hang.

## Verification
Re-run the same command; it should now print:
```
[M] deciding image_s0_c1 hasV=true v.passes=true conf=6
[M] decided image_s0_c1 -> approved
  · gate: GATE PASS
  · pipeline OK — rendering (ffmpeg, preset cinematic)
```
and finish with X7/X8/X9/X11-X15 passing (voiceover may still fall back to tones offline;
that is expected, not a hang).

## Cleanup
Remove ALL `[M]`/`[STAGE]` debug markers before committing. They are scaffolding only.
