---
name: codebase-gap-analysis
description: Audit an EXISTING codebase to find MISSING capabilities, dead code paths (classified-but-not-implemented intents), orphaned state machines, and inconsistent code paths — then produce a prioritized, file:line-evidenced gap report with a concrete design for the missing pieces. Use when asked to "analyze my project for gaps", "what's missing for X", "review the architecture", "what features are incomplete", or "make a better assistant/tool for this codebase".
triggers:
  - "analyze my project"
  - "what is missing"
  - "gap analysis"
  - "review the architecture"
  - "what features are incomplete"
  - "make a better assistant for this codebase"
  - "audit the repo for missing pieces"
---

# Codebase Gap Analysis

A gap analysis is NOT a bug hunt (that's `source-audit`) and NOT a test/verify pass
(that's `verify-codebase`). It answers: *"The code declares it can do X, but does it
actually deliver X end-to-end? What's missing, dead, or inconsistent?"* The deliverable
is a prioritized report (P0–P4) with **file:line evidence** and a concrete design.

## When to use
- User asks to analyze their project for gaps / missing features / completeness.
- User wants to extend an existing tool into a "better assistant" or fuller pipeline.
- You're onboarding to a large existing repo and need a capability map.

## Methodology (run in order)

### 1. Map the DECLARED capability surface
Find where the code *promises* capabilities. Common shapes:
- TS union types: `type TaskKind = 'merge' | 'trim' | 'crop' | ...` (router intents)
- Tool registries: `server.registerTool('agentic_plan', ...)` (MCP surfaces)
- CLI subcommand maps: `const COMMANDS: Record<string, (args)=>void> = {}`
- Interface/type definitions that enumerate variants.

### 2. Map the IMPLEMENTED surface
Find where capabilities are *actually executed*:
- `switch (task.kind) { case 'merge': ... }` dispatchers
- Registered tool handlers, command handlers
- Functions actually called from the pipeline entry point

### 3. DIFF declared vs implemented → dead intents
Every declared intent with NO executor is a gap. Use the bundled
`scripts/find-dead-intents.py` (generic router/dispatcher diff) or replicate inline:
extract union members with `\| '([a-z0-9_]+)'` and switch cases with
`case '([a-z0-9_]+)':`, then set-diff. Report the dead list explicitly.

### 4. Detect ORPHANED code (defined, never driven)
For each major function/state-machine/class, grep `-l` for its name across `src/`.
If it appears ONLY in its own definition file (and maybe tests), it is **orphaned** —
defined but never called from the real flow. Example: a `revision.ts` state machine
with `requestChanges`/`resolveRound` that nothing in the pipeline ever calls → the
"review loop" is phantom. (Caveat: skip truly-exported library APIs meant for external
callers; focus on internal control flow.)

### 5. Trace the end-to-end data flow, stage by stage, with file:line
Read the real execution path (entry → stages → output). For each stage note:
file:line of the function, what it consumes/produces, and any fallback path. This
surfaces *inconsistencies* — e.g. two entry points that call different
implementations of the same concern (voice stage routing through kokoro in one path,
Edge-TTS in another).

### 6. Classify gaps by impact ÷ effort
- **P0** — closes a broken promise / feedback loop (highest value, lowest risk)
- **P1** — correctness/consistency (e.g. regen captions on voice change, unify paths)
- **P2** — intelligence/UX lift (e.g. self-critique, better automation)
- **P3** — convenience (reorder, new intents)
- **P4** — polish (UI, type debt)

### 7. Propose a design, not just a list
For each P0/P1 gap give: concrete new file/function, the file:line target it plugs into,
and a before/after evidence plan (tests that fail-before/pass-after).

## Output format (NON-NEGOTIABLE for this user)
- **Every claim cites file:line.** No "the pipeline handles X" without `file.ts:NN`.
- **Trace data flow** with file:line refs, not prose summary.
- Be DETAILED on root cause — show the actual code path that breaks.
- End with a prioritized table + a concrete next-step recommendation that asks the
  user which scope to build (don't assume).

## Pitfalls
- **NEVER recommend deleting code to "fix" a gap.** This user's rule: backward-compat
  is non-negotiable — add new implementations / shims, do NOT delete old code or
  declared intents. If an intent is dead, *implement it* (or leave the declaration and
  flag it), never prune the declaration.
- **Router without default fallback = silent mis-route.** A `classifyOne` that returns
  no fallback for an unimplemented intent can route "convert to webm" → `full_video`
  (rebuilding a whole video instead of transcoding). Verify every classified intent
  has a real executor, and flag routers lacking a catch-all.
- **Windows path gotcha (Python pathlib):** use `C:/one/...` NOT `/c/one/...`. The
  latter fails `Path(...).exists()` under git-bash MSYS even though `cd /c/one` works
  in the terminal. Use `C:/`, `C:\\`, or `os.path.expanduser`.
- **Don't over-claim from memory.** When the user gives a direct source (a file path in
  the repo), inspect it; session memory is secondary to the actual current source.
- **Windows `search_files` tool fails on MSYS paths.** In this Windows/msys-git-bash
  environment the `search_files` tool (both `content` and `files` modes) returns
  `os error 3` / "The system cannot find the path specified" for paths like
  `C:/one/...` or `/c/one/...` — even though `cd /c/one` works in the terminal and
  `rg` runs fine. **Workaround:** do all repo-grepping via `execute_code` with
  `subprocess.run(["rg", "-n", "<pattern>", "-n", "<abs-path>"], ...)`. Python's
  `os.listdir`/`os.walk` on the same path also works. This bites gap analysis
  constantly (you must grep union members, switch cases, and orphaned fn names) —
  default to `execute_code`, not the `search_files` tool. (Separate from the
  pathlib `C:/` vs `/c/` gotcha below.)

## Techniques (verified this session)

### Wiring an orphaned state machine (close the loop)
A common gap: a state machine file (e.g. `delivery/revision.ts` with
`requestChanges`/`resolveRound`/`approve`) is *defined* but **never called from the
real flow** — the "review loop" is phantom. To close it:
1. Add a driver function (e.g. `revise.ts`) that calls `requestChanges` → re-runs the
   pipeline into a **NEW non-destructive id** (`<id>_r<round>`) → `resolveRound(newId)`.
2. **Fail-safe before writing state:** the driver must check the original `plan.json`
   exists *before* calling `requestChanges` (which `writeFileSync`s a state file).
   Otherwise a missing job throws `ENOENT` from inside `save()`.
3. Expose it as an MCP tool + a CLI subcommand so an agent/user can drive revisions.
Full worked example (the AVS project): `references/worked-example-avs.md`.

### Dead-intent detection (concrete)
For a router union `TaskKind` + a `switch` dispatcher: extract union members with
`\| '([a-z0-9_]+)'` and `case '([a-z0-9_]+)':`, set-diff. But ALSO check the
`classifyOne` regex branches — an intent can be *classified* yet still have no
executor `case`. In AVS, `route.ts` classified ~37 intents but `dispatch.ts`
implemented only ~26; 11 were dead (`to_gif`, `convert`, `convert_audio`,
`images_to_video`, `video_to_images`, `separate_audio`, `separate_video`,
`mute_video`, `social_download`, `write_script`). Fix = add `case` branches
dispatching to existing thin op modules (reuse `convert.ts`, `image-video.ts`,
`social-dl.ts`; add small `demux.ts`/`script.ts`).

### Declared config-field → actual-consumption audit (the "dead control signal" pattern)
The highest-leverage gap class in a configurable pipeline is a field that is
**declared in the input/CLI type but silently ignored by the render path** — so
users set it and nothing happens. This drove an entire multi-wave hardening
campaign on AVS (waves A–K) and is the recipe to reuse:

1. **Extract the DECLARED surface.** Grep the input/config type for all optional
   fields, e.g. in AVS: `grep -nE "^\s+[a-zA-Z]+\??:" src/adapters/cli/cli-job.ts`
   (every `AgenticCliJob` field). Also capture nested shapes (`brand?: { watermark?; accent? }`).
2. **Extract the CONSUMED surface.** Grep the actual executor for `job.<field>` /
   `opts.<field>` usage, e.g. `grep -oE "job\.[a-zA-Z]+" src/agentic/operations/compose.ts | sort -u`.
   Any declared field NOT appearing in the consumed set is a *candidate dead signal*.
3. **Trace the real call chain, not just one file.** A field can be consumed in
   `buildPlan` but OVERWRITTEN downstream — or consumed only by an AI/style-engine
   path, not the deterministic render. In AVS the `compose` mode calls
   `buildPlanOnly` → `buildPlan` (default voice Jenny) → `buildVoiceConfigs`
   (`baseVoice` default Guy) → `applyVoiceConfigsToPlan` which **overwrote** the
   Jenny plan.voice with Guy. So fixing the default at one site was insufficient;
   the *root cause* was the downstream override. Always follow every assignment of
   the affected value to its final use (grep the field name across `src/`, not just
   the first hit).
4. **Confirm with a real render, not just grep.** A field that "looks consumed" may
   be behind a dead branch. Render a minimal job exercising ONLY that field and
   vision-check the output (see `avs-visual-frame-qa`). For color/aspect/text
   signals, extracting one frame and asking the vision model "is the text orange?"
   is decisive.
5. **Precedence contract.** When a field overlaps an existing one, define explicit
   precedence and write it as a pure function with unit tests. AVS example:
   `resolveOutputSize(job)` returns `{w,h}` with precedence
   `explicit aspect > explicit orientation > platform-default > portrait-default`;
   and `brand.accent` text color precedence
   `captionTheme > fontColor > brand.accent > theme default`. Extracting the
   resolution into a pure, exported, unit-tested helper is what made the
   `platform`/`aspect`/`square` fix regression-safe.
6. **Unit-test the contract, not the integration.** A full render is slow/flaky on
   a low-RAM box; extract the resolution logic into a pure function and assert the
   precedence matrix (12–20 cases) so the gap can never silently regress.

**AVS-specific dead signals found & fixed this way (reference for the pattern):**
`platform` (AI-hint only → now drives aspect), `aspect:'square'`/`orientation:'square'`
(only `'1:1'` matched → portrait), `brand.accent` (declared, only Remotion read it →
now tints ffmpeg captions), `voice` default `en-US-GuyNeural` (timed out on flaky
TTS → pinned `en-US-JennyNeural` consistently). See `references/dead-signal-audit-avs.md`.

## Pitfalls (specific to the config-field audit)
- **The first grep hit is a trap.** A field "consumed" at one site may be overridden
  or shadowed downstream. Trace EVERY assignment to final use before declaring it live.
- **AI-engine-only consumers don't count.** If a field is only read by a style-engine
  and never reaches the deterministic ffmpeg/encode path, it is effectively dead for
  the user. Verify it touches the actual render output.
- **Backward-compat is non-negotiable (this user's rule).** Add the field's effect;
  do NOT delete the declaration or change default *meaning* in a way that breaks
  existing jobs. New precedence should make explicit settings win.
- **Windows `search_files` tool fails on MSYS paths** — use `execute_code` +
  `subprocess.run(["rg", ...])` for the field-consumption greps (see Pitfalls above).
- **`execute_code` `node -e` file writes can silently not persist** on this Windows
  box (sandbox cwd mismatch) — after writing `agentic-scripts.json` via a script,
  immediately re-read it in a separate `terminal` call to confirm the job is present
  before launching a render that depends on it. A render that exits "No jobs matched
  filter" means the JSON write didn't land.

## Support files
- `scripts/find-dead-intents.py` — generic declared-vs-implemented intent diff.
- `references/worked-example-avs.md` — a real application of this method on the
  Automated-Video-Generator project (dead intents + orphaned revision state machine).
- `references/dead-signal-audit-avs.md` — the "declared config-field → actual-
  consumption" audit applied to AVS: every dead `AgenticCliJob` signal found/fixed
  (`platform`, `aspect:'square'`, `brand.accent`, voice default), with the exact
  precedence contract + verification for each. Reuse the recipe for any configurable
  pipeline whose render path silently ignores declared fields.
