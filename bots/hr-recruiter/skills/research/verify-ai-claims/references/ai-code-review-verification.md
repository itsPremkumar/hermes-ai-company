# Verifying an AI-generated "code review" of YOUR repo

When another AI pastes a numbered review/audit of this project, treat it as
UNVERIFIED until you probe the code. Many such docs are written without reading
or running the code and contain FALSE defect claims.

## Disprove-first probe recipe (run, read, then judge)

```bash
# 1. "Module missing / import crashes"
node -e "console.log(require.resolve('@remotion/bundler'))"   # installed? claim false
grep -rn "from '@remotion/bundler'" src | head

# 2. "Function X is never called / ignored"
grep -rn "scoreCandidate\|agentDecide" src/agentic | head      # read call sites

# 3. "Never tested"
grep -rln "scoreCandidate" src/**/*.test.ts

# 4. "Dead code / unused"
grep -rn "sfx-selector\|planSceneSfx" src | grep -v "sfx-selector.ts:"

# 5. "Crashes / wrong path / hardcoded"  -> read the cited lines
```

## Real example (session 2026-07-16, Automated-Video-Generator)
Pasted 35-item review, verdict after probing:

| # | Review claimed | Verdict | Evidence |
|---|----------------|---------|----------|
| 1 | `@remotion/bundler` missing -> Remotion crashes | FALSE | require.resolve OK; real Remotion video rendered same session |
| 5 | `agentDecide` ignores `scoreCandidate` | FALSE | calls it at ~line 170, uses totalScore |
| 8 | Remotion has no graceful fallback | FALSE | bin/agentic-run.ts try/catch -> ffmpeg fallback |
| 11 | `renderAgenticSlideshow` untested | FALSE | src/agentic/render.test.ts exists |
| 13 | `scoreCandidate` never tested | FALSE | enhancement.test.ts:17-29 |
| 35 | `makeContactSheet` never called | FALSE | called in runAgenticPipeline |
| 4 | Absolute Windows paths in subtitles filter fail | OVERSTATED | code already passes relative path + escapeFilterPath |
| 17 | Hardcoded music path crashes if renamed | OVERSTATED | last-resort fallback to tone, not a crash |
| 6 | Acquire fetches scenes sequentially | TRUE | fixed -> Promise.all parallel fetch |
| 16 | workspaces/ grows unbounded | TRUE | fixed -> pruneWorkspaces(maxKeep=25) |
| 9 | writeScriptHeuristic 3 rigid sentences | TRUE | fixed -> varied hook/insight/payoff |
| 23 | sfx-selector.ts dead code | TRUE (but keep) | wired into render instead of deleting (user: "don't delete anything") |
| 25 | No --dry-run flag | TRUE | added to CLI + pipeline |

## Lesson: brittle tests force bad code
A test asserting a literal string (e.g. keywords must include 'video of lions')
locks in low-quality output. Replace with property assertions: distinct,
deterministic, no degenerate phrase (video of X / image of X). This session
removed that hack -> search relevance improved AND the test still guarded behavior.

## Response shape
Claim | Verdict (real/false/overstated) | Evidence - then implement ONLY the
verified-true subset. Keep the review's useful frame; fix the false facts.
