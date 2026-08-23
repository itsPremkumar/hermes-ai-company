# Multi-agent swarm dispatch on this project (AVG)

When the user asks to "use many subagents / make it world-class / continuous
improvement", dispatch a PARALLEL swarm via `delegate_task` with `tasks: [...]`.

## HARD PITFALL: concurrency cap is 3
`delegate_task` with `type: batch` rejects >3 tasks ("max_concurrent_children is
3"). You CANNOT dispatch 7+ agents at once. Dispatch in WAVES:
- Wave 1: first 3 agents (highest priority).
- When a slot frees (you get the consolidated result message), dispatch Wave 2
  (next 3), then Wave 3 (remainder).
Do NOT block/poll — the system notifies you when a wave completes; continue other
work or just wait for the notification.

## Each agent brief must include
- Repo path + branch (main at <sha>); tell it to work on a NEW isolated branch.
- Standing constraints: FREE stack only, additive changes, match code style,
  DO NOT touch the Voicebox integration (api-tts-provider.ts,
  voicebox-lifecycle.ts, VOICE_CLONING_GUIDE.md) or .env secrets.
- Verify command to run before "done": `npm run typecheck` + `npm run test:unit`
  (NOT `npm run test` which includes GPU/ffmpeg `test:render`). Report exact
  pass/fail counts.
- Return: branch name + what changed + verification evidence.

## Verify-before-merge discipline (the user's standing rule)
When each wave reports back, DO NOT trust the summary. Re-run `npm run typecheck`
+ `npm run test:unit` on the branch yourself, confirm green, THEN merge to main
and push. The agent's "all passing" claim is not verification.

## Suggested wave split for a full production pass
Wave 1 (foundation): Bug-Hunter (fix failing tests) · Docs Architect ·
CI/CD (GitHub Actions).
Wave 2: Test-Coverage Expander · Perf/Hardening (async ffmpeg, timeouts,
lint:fix) · Agentic Ops CLI (bin/agentic-ops.ts over existing operations).
Wave 3: Release/Versioning (CHANGELOG + release.yml) · Feature Identifier
(free-only gap analysis) · Feature Builders (top free features as new
src/agentic/operations + MCP tools + tests).

## Feature scope guard
New features must be FREE + run on the 6GB/RTX3050 box via ffmpeg/edges/wasm
(NO mandatory GPU, NO paid APIs). Famous-person voice cloning is OFF-LIMITS
(legal). The Voicebox GPU clone (user's-own-voice) stays a separate opt-in and
is never touched by the swarm.
