# Worktree Recipes & Case Study

## 1. Create worktree from a specific base commit (Windows)
```bash
cd /c/one/Automated-Video-Generator
git worktree add -b improvement/pipeline-hardening C:/one/avs-improvements fe22038
# then inside the worktree:
cd /c/one/avs-improvements
cmd /c "mklink /D node_modules C:\one\Automated-Video-Generator\node_modules"
```
List worktrees: `git worktree list`. Clean up later: `git worktree remove C:/one/avs-improvements`.

## 2. The 238s test-hang case study (AVS session)
A test for `buildPipelineRequest` was placed next to `agentic-cli.ts`, which imports
`runAgenticPipeline` → the entire orchestrator graph (pipeline.js, render.js,
speech-backend.js, ffmpeg.js, axios). Result: `npx tsx --test` ran **238s** then was
killed by timeout (`exitCode: 143`), with only part of the suite completing.

Fix that made it <0.5s:
- Created `src/adapters/cli/cli-job.ts` containing `AgenticCliJob` interface + `buildPipelineRequest()`.
- Every cross-module import is `import type` (erased at runtime):
  ```ts
  import type { PipelineRequest } from '../../agentic/orchestrator/types.js';
  import type { AgenticBackend } from '../../agentic/ai/agent.js';
  import type { AgenticConfig } from '../../agentic/config.js';
  ```
- Test imports from `./cli-job.js` (lightweight) instead of `./agentic-cli.js` (heavy).
- `agentic-cli.ts` re-imports and re-exports `buildPipelineRequest` from `cli-job.js`
  (no behavior change; `main()` still calls it).

After: `tsc --noEmit` clean, `agentic-cli.test.ts` → 4/4 pass in ~0.27s.

## 3. Typecheck + test verification loop (per worktree)
```bash
npx tsc -p tsconfig.json --noEmit 2>&1 | head -15; echo "TSC_EXIT: ${PIPESTATUS[0]}"
timeout 120 npx tsx --test "src/path/to.test.ts" 2>&1 | tail -14
# tsx cold-start is slow; give 120-180s, don't assume hang on first slow run
```

## 4. Lint only the files you touched
```bash
npx eslint src/adapters/cli/cli-job.ts src/adapters/cli/agentic-cli.ts
# 0 errors expected; warnings in untouched files (require()/any/unused) are pre-existing
```

## 5. Staging discipline
`git add -A` will stage the `node_modules` symlink even though it's gitignored.
```bash
git add -A && git reset HEAD node_modules
git status --short   # confirm node_modules shows as ?? (untracked), not A (staged)
```

## 6. Recovery: `replace_all` mangled a parser file (same AVS session)
While adding 6 inline tags to `script-parser.ts`, a `replace_all` on the repeated
`const cleanText = line\n .replace(/\[Visual:?.../gis, '')` cleanup chain (3 copies)
doubled backslashes and injected the new lines 9×, corrupting the file. The tool
still reported "success".

Recovery (fast, non-fuzzy):
```python
# execute_code — Python open().read/write is exact, no fuzzy matcher
path="C:/one/avs-script-control/src/lib/script-parser.ts"
c=open(path).read()
anchor="            .replace(/\\[Volume:?\\s*.*?\\]/gis, '')\n            .trim();"
addition="""            .replace(/\\[Volume:?\\s*.*?\\]/gis, '')
            .replace(/\\[CaptionTheme:?\\s*.*?\\]/gis, '')
            .replace(/\\[Sfx:?\\s*.*?\\]/gis, '')
            .replace(/\\[JCut:?\\s*.*?\\]/gis, '')
            .replace(/\\[Vignette:?\\s*.*?\\]/gis, '')
            .replace(/\\[Kinetic:?\\s*.*?\\]/gis, '')
            .replace(/\\[MusicIntensity:?\\s*.*?\\]/gis, '')
            .trim();"""
assert c.count(anchor)==3, f"expected 3, found {c.count(anchor)}"
open(path,'w').write(c.replace(anchor,anchor+addition))
```
Rules: (1) `git checkout -- <file>` first if you already corrupted it. (2) Use
`execute_code` with Python `str.replace` (exact) — it avoided the fuzzy matcher.
(3) `assert count == N` before replacing so you know how many sites you hit.
(4) Re-run `tsc --noEmit` after. This is the companion to the
`deterministic-file-edits` skill's `replace_all` pitfall.
