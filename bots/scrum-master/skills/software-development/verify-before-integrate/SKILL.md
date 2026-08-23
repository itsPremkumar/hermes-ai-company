---
name: verify-before-integrate
description: Discipline for wiring standalone / "complete but unwired" modules into a main pipeline. The user's standing rule — a module must be PROVEN working end-to-end (real test runs + load probes) BEFORE it is imported into the main flow. Do not trust a list or a teammate's claim that something is "done but not connected." Use when handed an inventory of unwired modules, or about to import/require a sibling module.
---

# Verify Before Integrate

The user's standing rule (stated explicitly, repeated across sessions):
**verify the complete end-to-end working state of a thing BEFORE integrating it
into the main pipeline — in its correct, required position.** Integrate ONLY what
is free, offline-capable, and proven working. Everything else waits.

This is the inverse of "wire it then test it." You verify first, wire second, one
module at a time, each with a regression test.

## When to use
- Someone hands you a list of "modules that exist but aren't connected" and asks
  you to wire them in. (The list is a CLAIM — treat it as unverified.)
- You're about to `import`/`require` a sibling module into the main flow.
- Audit / integration passes over a large repo with many half-finished features.

## Sequence (verify first, wire second)
1. **Inventory on disk, don't trust the list.** `find`/`ls` the dirs. File counts
   can reveal symlinks or a 3866-file `node_modules` masquerading as source.
2. **Run each module's OWN test suite** with a `timeout`. Real test runs are the
   only proof a module works. A module "with tests" you haven't executed is
   unverified. Offline suites (pure ffmpeg, mocks) are gold; network suites are
   gated.
3. **Probe the load/runtime paths tests don't cover:**
   - registry / factory constructors (`createRegistry(ctx)`, `setupX()`) — these
     routinely CRASH on load from an undefined config field even when every
     individual plugin file looks fine. The crash blocks EVERYTHING downstream.
   - the exact entry points the main pipeline will call.
4. **Classify each module:**
   - ✅ FREE + offline-working (integrate)
   - 🔌 network / key-gated (don't integrate, or gate behind a flag + note it)
   - 💥 crashes / type errors (fix the one-line bug, or skip)
5. **Wire only the FREE + verified ones**, one at a time, each behind a regression
   test. Re-`tsc` after every single module.
6. **Delete temp probe files** and re-run the targeted suites.

## Hard pitfalls
- **Claimed-but-broken:** a module billed "complete" often throws on load
  (e.g. `path.resolve(cfg.lutDir)` where `lutDir` is `undefined` → the WHOLE
  registry init throws, killing all 25 plugins). Always probe the actual
  constructor, not just `grep` for the function name.
- **Sibling-agent collision (live multi-agent repo):** if another agent is
  editing the SAME repo concurrently, its writes can (a) overwrite your edits to
  shared files, and (b) leave a file with broken syntax that breaks the entire
  `import` graph (10 suites cascade-fail to load).
  - Before editing a shared file, check `git status` and any
    "modified by sibling subagent" warnings from the tool.
  - **Do NOT repair another agent's live in-progress file.** It's live; you'll
    collide and may lose both versions. Leave it, name it as a blocker, and verify
    YOUR work via the suites that DON'T depend on that file (type-only / lazy
    `import('./x.js')` references and optional injected deps don't pull the broken
    module into the graph).
  - `tsx` (esbuild) fails harder/faster than `tsc --noEmit` on syntax errors.
    If `tsc` passes but `tsx` throws, suspect a stale buffer OR a file the
    typechecker excludes from its `include`. Re-run both fresh.
- **Stray probe files:** temp `.ts`/`.mjs` verification scripts left in the repo
  trip "unverified" flags. Delete them; confirm with `git status` + `ls`.
- **Don't fight a constrained box:** on a low-RAM Windows host, bound EVERY
  command with `timeout`. A huge `npm run test:unit` glob that imports a broken
  module cascade-fails a dozen suites — run the specific suites you own instead.

## Verification gate (per module, before moving on)
- `npx tsc -p tsconfig.json --noEmit` → 0 errors
- `npx tsx --test "<module>.test.ts"` → green
- `git status` clean of temp/probe files
Only then wire the next module.

## Reporting to the user
Give a table: module | location | purpose | verified? (real test count) |
integrate-or-skip + why. Distinguish "free + verified" from "network/key-gated"
from "crashes (fixable)".

References: `references/verification-recipe.md` — exact commands and the real
case this was learned on (a 25-plugin registry that crashed on load, a sibling
agent's broken `brain.ts` blocking 10 suites, offline ffmpeg fallback proving).

References: `references/agentic-custom-script-cli.md` — how to add a simple
JSON-in + `[Visual: ...]` tag CLI to an agentic pipeline (case study:
Automated-Video-Generator agentic pipeline). Covers the 4-step pattern:
script field on request, req.script bypass of auto-generation, local-asset
overwrite fix, and CLI+NPM-script creation.
