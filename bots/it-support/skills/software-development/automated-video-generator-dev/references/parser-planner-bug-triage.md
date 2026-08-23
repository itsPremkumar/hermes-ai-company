# Script Parser + Plan.ts — verified behavior & known bugs (bug-hunt July 2026)

Executable repro harness: `workspace/bug-hunt/parser_probe.mts` (run with `npx tsx`); full report `workspace/bug-hunt/findings_parser.md`.

## tsx import pitfall (repo-specific)
Importing `src/agentic/pipeline/plan.ts` (and other src modules) from an .mts probe under tsx yields ONLY a `default` export — `import { applyProEdits } from ...` fails with "does not provide an export named". Workaround used:
```ts
import pl from '../../src/agentic/pipeline/plan.ts';
const { buildPlan, applyProEdits } = (pl as any).buildPlan ? pl as any : (pl as any).default ?? pl;
```
Same for `script-parser.ts`. Cause: NodeNext/CJS interop under tsx.

## Verified-fixed behaviors (don't re-flag)
- B1 (script-parser.ts:180–184): any line containing `[Visual:]` becomes exactly ONE scene, no sentence split.
- B3 (plan.ts:171–172): `applyProEdits({hookFirst:true})` skips reorder when ANY scene has `localAsset`.
- Empty/whitespace scripts → 0 scenes, no crash. `[Visual:file]` (no space) parses fine.

## Open bugs (as of this triage — verify before re-reporting or fixing)
- P-1 script-parser.ts:385 — duration `ceil(len/15)` uncapped; 500-word line → 167s scene.
- P-2 :185/:360 — CJK: `。！？` not sentence boundaries; whole CJK string becomes one keyword.
- P-3 :372 — nonexistent `[Visual: x.mp4]` silently makes filename the search keyword, no warning.
- P-4 :322 — duplicate `[Visual:]` tags on a line WITH text: only first used, second dropped silently (tag-only line correctly splits into N scenes via :293).
- P-5 — empty `[Visual: ]` still triggers B1 no-split path.
- P-6 :186–197 — Visual-tag half of propagation guard is dead code (Visual lines continue at :183). Non-visual trailing tags (e.g. `[Transition: fade]`) propagate to ALL sentence fragments.
- P-7 plan.ts:75 — `parseTimeToSeconds` returns 0/NaN on malformed input, no validation.
