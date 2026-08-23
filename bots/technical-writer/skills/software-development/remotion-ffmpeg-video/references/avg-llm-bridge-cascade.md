# AVG: Unified LLM bridge with a driver→model→signal cascade (additive refactor)

## When this applies
User wants **all** LLM / vision-verification calls in the agentic pipeline to
route through one boundary, with the **driver** (the MCP client that commanded
the generation — Hermes/OpenClaw/etc.) getting **first priority**, then the
configured free model (OpenRouter/Ollama/Gemini), then the deterministic signal
floor. Standing rule from the user: *"first all calls go directly to the driver
system for most accurate result, then fall back to other LLMs"* and *"don't
delete the code, only implement."* So the work is an **additive** unification,
never a rewrite that removes the existing `AgentBrain` / `verifyMedia` paths.

## The design that fits this codebase
Create `src/agentic/bridge.ts` — one `LlmBridge` interface, three impls, one
resolver:

```ts
interface LlmBridge {
  completeJSON<T>(system, prompt, schemaHint): Promise<T | null>;
  visionVerify(filePath, keywords): Promise<BridgeScore | null>;
  judgeAudio(transcript, expectation, flags): Promise<BridgeScore | null>;
  readonly name: string;                       // 'null' | 'model' | 'driver'
}
```
- **NullBridge** — every method returns `null` → caller uses signal gates (X7–X15). The guaranteed offline floor.
- **ModelBridge** — wraps the EXISTING `AgentBrain` (text/vision) + `verifyMedia` (Gemini/Ollama vision). Behaviour identical to pre-refactor.
- **McpDriverBridge(driverCallback?, fallback=ModelBridge)** — if a `driverLLM` callback is injected it is tried FIRST; on `null`/throw it transparently falls through to the fallback. With **no** callback it degrades to exactly its fallback (so CLI runs are unchanged).
- **`resolveBridge({hasModelKeys, driverLLM, modelOpts})`** — picks driver→model→null. Single entry point.
- **`toBridge(x: LlmBridge | AgentBrain | null)`** — normaliser so legacy callers that still pass an `AgentBrain` keep working; wraps a raw brain in a ModelBridge. This is what lets you change `aiVerifyAsset`'s signature to accept `LlmBridge | AgentBrain` WITHOUT touching all 4+ existing callers (gate.ts, orchestrate.ts, scene-edit.ts, tests).

Wire points: `orchestrate.ts` builds the bridge once (`resolveBridge`), uses it
for the script decision AND passes it as `acquireDeps.bridge`; `ai-verify.ts`
routes vision+audio through it; `acquire.ts` gets a `resolveAcquireBridge(deps)`
helper (deps.bridge → ModelBridge(deps.brain) → NullBridge).

## The MCP reality check (do NOT let another LLM's plan skip this)
A reviewing LLM proposed "the MCP server runs inside the driver's process, just
inject a callback." **FALSE on this codebase.** `mcp-server.ts` uses
`StdioServerTransport` — the server is a **separate stdio subprocess**; there is
no in-process handle to the driver's LLM and **no sampling/elicitation channel**
(verified: `grep -rE "sampling|elicit|createMessage|requestLLM"` → nothing).
So `McpDriverBridge` is built to *accept* an injected callback and fall back
correctly, but until a real bidirectional round-trip (a `provide_llm_result`
tool the driver fulfils) is wired into `register-agentic-tools.ts`, the driver
tier is dormant and the bridge behaves as ModelBridge. **Say this honestly** —
do not claim "all LLM calls now go to the driver" when the transport can't yet
deliver it. Answer to the user's recurring question "are all LLM calls received
by you (the assistant) by default?" → **No.** They go to OpenRouter/Ollama/Gemini
or to heuristics; the driver-first path needs the MCP round-trip first.

## Two TypeScript pitfalls that cost the most time
1. **Generic inference collapses to `unknown` from a leftover duplicate decl.**
   Symptom: `mapWithConcurrencyLimit(sceneFetches, N)` errors with
   `(() => Promise<unknown>)[]` and a phantom `scene: any`. Root cause was a
   **second, stale `const sceneFetches`** (the old `Promise.all` accumulator)
   still present above the new thunk-array declaration, plus the thunk array
   accidentally declared **inside** the loop (redeclared each iteration →
   discarded). Fix: (a) delete the stale accumulator, (b) declare the thunk
   array ONCE before the loop and `.push()` inside, (c) drop the explicit
   `results: {…any…}[]` annotation and let `T` infer from a concrete
   `Array<() => Promise<{…ScenePlan…}>>`. Import `ScenePlan` so the loop var
   isn't `any`. After that, generic inference resolves cleanly.

2. **Duck-typing a bridge vs a legacy class.** `toBridge` must distinguish an
   `LlmBridge` from an `AgentBrain`. Do NOT test `'visionVerify' in x` alone —
   `AgentBrain` ALSO has `visionVerify`. Discriminate on properties the brain
   does NOT have: `typeof x.name === 'string' && 'judgeAudio' in x`
   (verified: AgentBrain has neither a `name` field nor `judgeAudio`).

## Test-signature ripple (the failure that ended the session)
Changing `aiVerifyAsset`'s 5th param from `brain: AgentBrain` to
`bridge: LlmBridge` (even via `toBridge`) **breaks `ai-verify.test.ts`** — its
mocks pass a fake `brain` and the removed `if (!brain.modelEnabled) return null`
early-guard changes behaviour (5 tests: "no model → null", vision pass/fail,
"vision always called", verifyOnRender). Lesson: when unifying a hot signature,
**grep every caller AND every `.test.ts` up front** (`grep -rn 'aiVerifyAsset('`)
and either (a) keep a `modelEnabled`-equivalent guard so a NullBridge-wrapped
brain still short-circuits, or (b) update the mocks to bridge shape. Do this
BEFORE running the full suite so you don't burn iterations discovering it.

## Verification order (per user's standing quality bar)
typecheck 0 → new unit tests (bridge cascade: driver-first, model-fallback,
throw-fallback, setDriver swap) → full `test:unit` green → lint 0 → format →
commit on a feat branch → push → confirm CI green. `bridge.ts` unit tests are
fully offline-testable: fake the driver callback and a stubbed ModelBridge
(inject `b.brain = {completeJSON: …}` via `@ts-expect-error`), assert the tier
that fires.
