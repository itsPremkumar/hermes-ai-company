# AVG Agentic Design — per-file inventory & 6-stage map (POST-BUILD, verified green)

Build done in `C:\one\Automated-Video-Generator`:
`tsc --noEmit` EXIT 0; `src/agentic/agentic.test.ts` **12/12** (4 new: agent backend); existing suite 23/23.

## 6 stages -> files

| Stage | File | Key exports | Notes |
|---|---|---|---|
| 1 Plan | `src/agentic/plan.ts` | `buildPlan`, `deriveMusicQuery`, `Parser` (exported) | Reuses `src/lib/script-parser.ts` `parseScript`. Parser injected so tests run offline. |
| 2 Acquire | `src/agentic/acquire.ts` | `acquireAssets`, `AcquireDeps`, `FetchedVisual` | Downloads N candidates into `assets/images/<scene_XX>/`, `assets/videos/<scene_XX>/`, `assets/music/`. All fetchers injected. |
| 3 Verify | `src/agentic/verify.ts` | `verifyAll`, `VerifyDeps`, `VERIFY_PASS_CONFIDENCE` | Per-asset -> `verification/{image,video,music,all}_checks.json`. `verifyImage/verifyVideo` injected; music via `verifyMusic`. |
| 4 Decide | `src/agentic/gateway.ts` | `runGateway`, `GatewayDeps`, `buildRenderManifest`, `Decider` | Loops acquire->verify->decide; reject -> re-fetch (max retries, default 3). Writes `approval-manifest.json`. |
| 5 Gate | `src/agentic/gate.ts` | `runFinalGate`, `GateReport` | X1-X6 cross-checks; BLOCKS render if any unverified / scene missing. |
| shared | `src/agentic/types.ts`, `src/agentic/workspace.ts` | `AssetCandidate`, `AssetDecision`, `Plan`, `RenderManifest`, `createAgenticWorkspace`, `sceneImageDir/VideoDir`, `writeJson/readJson` | Per-job workspace at `agentic-pipeline/workspaces/<jobId>/`. |
| agent backend | `src/agentic/agent.ts` | `writeScriptHeuristic`, `expandKeywordsHeuristic`, `agentDecide`, `readVerification`, `AgentBackendConfig` | **`backend:'agent'` (DEFAULT) — Hermes/OpenClaw IS the AI: writes script, expands keywords, DECIDES every asset. NO Gemini/Ollama key required.** `vision` is opt-in. |
| orchestrate | `src/agentic/orchestrate.ts` | `runAgenticPipeline` | One-shot 6-stage run; `agentic_run` MCP tool calls this. Honors `backend`. |

## Verification engine (reused + extended)
- `src/lib/media-verifier.ts` — EXTENDED: `verifyMedia(filePath, keywords, opts?: VisionCheckOptions)` now also screens `checkWatermark` + `checkSafety`. Was only wired on the video branch of `src/video-generator.ts` (~244-255); image branch still needs to call it (Phase-6 item).
- `src/lib/music-verifier.ts` — NEW: `verifyMusic(filePath, opts?, ffprobeRunner?)` checks duration >= video, no silence/corrupt, bitrate >= 96 kbps, license present. `ffprobeRunner` injected; degrades gracefully (passes on file-size) when ffprobe absent.

## MCP agent surface (10 tools)
`src/adapters/mcp/register-agentic-tools.ts` (registered in `src/mcp-server.ts`):
`agentic_plan`, `agentic_acquire`, `agentic_verify_all`, `list_pending_assets`,
`get_asset_preview` (returns base64 thumb — the agent SEES the asset), `approve_asset`,
`reject_asset`, `agentic_gate`, **`agentic_run`** (one-shot 6-stage, `backend:'agent'|'vision'`).
Wires real fetchers via `depsFor()`: `fetchVisualsForScene` (visual-fetcher), `downloadMedia` (visual-fetcher), `resolveFreeBackgroundMusic` (free-music), `verifyMedia` (media-verifier).

Autonomy: `AGENT_AUTONOMY` — L2 (default) agent auto-decides + logs; L0/L1 surface to human.

## Offline DI test pattern (RAM-starved box)
`src/agentic/agentic.test.ts` injects fakes for every network/vision/ffprobe dependency, so the 12 tests run with zero network and ~MB of RAM:
- `acquire` fakes return dummy files written to temp/workspace dirs.
- `verify` fakes return canned `{passes, confidence, reason}`.
- `gateway` `decide` stub: test approves all (gate passes); test rejects a scene visual (gate BLOCKS render).
- `agent` backend tests: heuristic script-write, keyword-expand, approve/replace decision from scores.

Run:
```
npx tsc -p tsconfig.json --noEmit   # whole project, EXIT 0
npx tsx --test "src/agentic/agentic.test.ts"   # 12 pass / 0 fail
```

## NodeNext import-extension rules (cost ~10 iterations — internalize)
1. Relative imports need `.js` suffix: `import {x} from './types.js'` (file is `types.ts`).
2. Count `../` from the file's dir: `src/adapters/mcp/x.ts` -> lib is `../../lib/y.js`.
3. Directory-index imports (`./free-video/index`) may omit ext ONLY if an existing import of that module does; verify with `grep` first.
4. Test/anonymous callbacks in `tsx --test` need typed params or `error TS7006` fires: `(c: AssetCandidate) =>`, `(url: string, dir: string, filename: string) =>`.
5. Fake parser doubles: type `: any` (don't reconstruct the real `Scene` shape -> `TS2345`).

## Standing user rules (non-negotiable for THIS user)
- **NEVER `git commit`/`git push` this work without explicit, separate approval.**
- **The agentic pipeline is ADDITIVE — the old workflow is UNTOUCHED.** `input/input-scripts.json` -> `npm run generate`, the Electron app, and the existing MCP `generate_video` tool must keep working. Gate any build on `git status` showing `src/video-generator.ts`, `src/lib/script-parser.ts`, `input/` with NO `M`.
- **Every build ships REAL tests + a green verification gate** (typecheck + `tsx --test`), matching the user's standing quality bar.

## Honest gap left open (don't claim done)
- Feeding the approved `render-manifest.json` into the existing Remotion render path (`src/video-generator.ts`) + a live e2e (real fetchers + vision) were NOT done.
- Nothing committed or pushed — it's in the working tree for review (per standing rule above).
