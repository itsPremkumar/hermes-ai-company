# input/scripts/ consolidation & fixture-relocation recipe

Reusable procedure for the recurring "combine all these input JSON files into
`agentic-scripts.json`" ask. The naive `cat *.json > agentic-scripts.json`
form SILENTLY DROPS jobs when IDs repeat — this recipe prevents that.

## Verified live layout (2026-07-26)
```
input/scripts/
├── agentic-scripts.json     # LIVE — agentic pipeline. agentic-batch.ts
│                             #   hardcodes SCRIPTS_FILE = this file. 65 jobs,
│                             #   tagged (tags:["waveA-matrix"], etc.).
├── agentic-scripts.json.bak # original backup (untouched)
├── input-scripts.json       # LIVE — LEGACY batch (npm run generate). simple jobs.
├── README.txt               # documents which files are live vs fixtures
├── INPUT_FORMAT.md          # legacy field docs
└── examples/                # REFERENCE FIXTURES (NOT auto-loaded)
    ├── agentic-scripts.example.json
    └── variety-matrix / waveA..waveI -matrix .example.json  (9 files)
```
The 9 `*-matrix` files are a 100% SUBSET of `agentic-scripts.json` (same IDs).
They were relocated (not merged) into `examples/` purely for labeling/clarity.
Copy a job out of `examples/` into a live file to actually run it.

## The 5-step safe-consolidation recipe
1. **SUBSET CHECK first (prevents phantom merge).** Parse every candidate file,
   collect `id`s, compute the union, and test `union ⊆ target_ids`.
   If true → the merge ADDS ZERO jobs; only file ORGANIZATION is needed.
   (This session: 32/32 matrix IDs already inside `agentic-scripts.json`.)
   ```py
   import json, os
   d = "input/scripts"
   target = {j["id"] for j in json.load(open(f"{d}/agentic-scripts.json")) if "id" in j}
   union = set()
   for f in candidates:
       for j in json.load(open(f"{d}/{f}")):
           if "id" in j: union.add(j["id"])
   print("pure subset?", union <= target, "| new jobs:", len(union - target))
   ```
2. **ID-DEDUPE.** JSON array concatenation keeps both copies of a duplicate ID
   but a tool that dedups-by-ID silently deletes one. If `len(ids) != len(set(ids))`
   after merge, you LOST jobs. Decide the merge direction (which copy wins) BEFORE
   writing.
3. **LOSSLESS twin check.** Spot-check divergent twins by `json.dumps(x, sort_keys=True)`
   diff. A `1.0` vs `1` difference is numerically identical (safe); a real field
   difference means pick the newer copy. Never assume "same ID = same content."
4. **PROVENANCE via `tags`.** `AgenticCliJob` already supports `tags: string[]`.
   Add `tags:["waveA-matrix"]` to each relocated job in the live file so wave
   origin survives the consolidation. No info loss.
5. **VERIFY runtime, not just JSON.parse.** After moving/merging:
   - Confirm the runner hardcodes the input file: `grep -n "SCRIPTS_FILE" src/adapters/cli/agentic-batch.ts`
   - Confirm no test hardcodes the moved path: `grep -rln "waveA-matrix\|variety-matrix" tests src`
   - Confirm field CONSUMPTION: for every advanced field the fixtures use, grep
     `src/` for consumption in `compose.ts`/`overlays.ts`/`visual-fx.ts`/`sfx.ts`/
     `single-feature.ts` — NOT just the type declaration in `cli-job.ts`. A field
     only matters if an operation file reads it.

## `mode: "compose"` is a LABEL, not a stage gate (non-obvious)
The matrix jobs carry `"mode": "compose"`, but:
- `agentic-batch.ts` reads the job's `mode` field ONLY as a descriptive label.
  Its own `--mode` CLI flag (plan/compose/render/download-*) is a SEPARATE thing.
- `cli-job.ts` / `pipeline.ts` NEVER branch on `job.mode === 'compose'`
  (grep returns 0 hits). So a `mode:"compose"` job runs the NORMAL full agentic
  pipeline when placed in `agentic-scripts.json`. The flag is harmless/inert.
- Implication: you can drop `mode:"compose"` from relocated jobs with zero effect,
  OR keep it as a human-readable tag.

## Relocation safety (backward-compat rule)
- Move redundant fixtures to `examples/` with a `.example.` infix so they read as
  fixtures, not live inputs.
- Keep the pre-existing `agentic-scripts.json.bak` (don't overwrite it).
- Don't delete old files outright — relocate + keep `.bak`. If you MUST drop a
  redundant `.bak` you created yourself, only remove YOUR OWN backups, never the
  original `agentic-scripts.json.bak`.
- Verify end state: `node -e "const j=require('./input/scripts/agentic-scripts.json'); console.log(j.length, new Set(j.map(x=>x.id)).size)"` → 65 / 65.
