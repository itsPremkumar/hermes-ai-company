# Full Merge Execution — Worked Example

Real session: 7 worktrees under `C:/one/` for the Automated-Video-Generator project.
User asked: "check last 24 hours — any worktree code not committed in main? then do everything."

## Initial state

| Worktree dir | Branch | Status |
|---|---|---|
| `C:/one/Automated-Video-Generator` | `main` | Clean |
| `C:/one/avs-production-hardening` | `qa/production-hardening` | **DIRTY** — 3 modified + 4 untracked |
| `C:/one/avs-production-stable` | `stable/prod` | Clean (merged) |
| 4 others | (deleted/pruned) | Directories gone, `prunable` flag |

The `qa/production-hardening` worktree had:
- **12 commits not in main** (last one ~17h ago): watchdog, unbounded fetch/connect guards,
  stalled download fix, stopwords leak, overlapping captions, Wikimedia PDF/DjVu gate, etc.
- **3 modified files**: `ffmpeg.ts` (human-readable placeholder labels), `pipeline.ts`
  (honest source attribution), `acquire.ts` (content gate for solid-color placeholders)
- **4 untracked files**: `docs/RELEASE_NOTES_HARDENING.md`,
  `src/agentic/pipeline/asset-validators.ts`, `tests/.../asset-validators.test.ts`, `$null`
- The fork point was `da01b10` (~24h old); main had 20+ new commits since.

## Step 1 — Commit worktree changes

```bash
cd /c/one/avs-production-hardening
rm -f '$null'                            # empty artifact file
git add -A
git commit -m "fix(acquire): content gate for near-uniform placeholders + honest source labeling"
# 6 files, 230 insertions, 5 deletions
```

This made the branch's local state fully committed before attempting the merge.

## Step 2 — Dry-run merge

```bash
cd /c/one/Automated-Video-Generator
git merge --no-commit --no-ff qa/production-hardening
```

Auto-merging succeeded on:
- `package.json`
- `src/adapters/cli/agentic-batch.ts`
- `src/agentic/operations/compose.ts`
- `src/lib/visual-fetcher/download.ts`
- `tests/agentic/media/tts.test.ts`

**One conflict**: `tests/agentic/ai/enhancement.test.ts` — the `buildDuckExpression` test.

## Step 3 — Read and resolve the conflict

Both sides had touched the same assertion block:

- **HEAD (main)**: tested `between(t,0.000,1.500)` and `startsWith('0.18-0.120*between(t,')`
- **qa/production-hardening**: tested the same `between(...)` call, plus:
  - `!includes('\\\\,')` — asserts no escaped commas (commas must stay raw for ffmpeg volume exprs)
  - `!includes('gt(')` — asserts no gt() wrapper (breaks ffmpeg volume filter)
  - fixed `startsWith` to not hardcode `t,` after `between(`

**Verdict**: The worktree's version is more comprehensive. Accept it entirely.

Backslash-escaping pitfall: the patch tool doubled the `\\` in the source, turning `'\\\\,'`
into `'\\\\\\\\,'`. Fixed with Python:
```python
lines[77] = re.sub(r"includes\('[\\\\]+,'", "includes('\\\\,',", lines[77])
```

## Step 4 — Complete the merge

```bash
git add tests/agentic/ai/enhancement.test.ts
git commit -m "Merge branch 'qa/production-hardening' into main"
```

## Step 5 — Prune stale worktrees

```bash
git worktree prune
```

Before prune: 7 listed (4 `prunable`). After: 3 active worktrees remain.

## Step 6 — Verify

```
npm run typecheck          → PASS (tsc --noEmit)
node --import tsx --test tests/agentic/ai/enhancement.test.ts → 7/7 PASS
```

All 7 tests passed, including the merged test and the ffmpeg-based `verifyRenderedVideo` test.

## What was merged (13 commits worth)

- 30-min global watchdog for wedged runs
- Unbounded fallback-fetch fix
- Unbounded connect/headers timeout fix
- Stalled downloads fix
- Image scenes receiving video files fix
- Stopwords leaking into visual search keywords fix
- Overlapping captions at scene boundaries fix
- Wikimedia returning PDFs/DjVu/AV as "images" fix
- Production readiness checklist docs
- Empty `--topic` truthiness CLI fix
- CLI input validation + CI test runner flags
- Stabilization: process leaks, offline music self-heal
- Content gate for near-uniform placeholders + honest source labeling + new asset-validators module
