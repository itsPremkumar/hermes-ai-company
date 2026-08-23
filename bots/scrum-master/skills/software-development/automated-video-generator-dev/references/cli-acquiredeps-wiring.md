# AVS CLI acquireDeps Wiring Footgun

## Lesson (2026-08-11, local material pool feature)
When you add a feature flag that must reach `acquireAssets()` (e.g. `localPool`),
wiring it into `PipelineRequest` + `pipeline.ts` is NOT enough - the **CLI path
rebuilds its own `acquireDeps` object** (`src/adapters/cli/agentic-modular.ts`,
~lines 400-441) that does NOT read from the `req` / `PipelineRequest`. It passes
that object straight to `acquireAssets(plan, acquireDeps, ...)` at ~line 443.

### Symptom
- Added `localPool` to `PipelineRequest` (`orchestrator/types.ts`) OK
- Added `if (req.localPool) acquireDeps.localPool = true;` in `pipeline.ts` OK
- Job JSON set `"localPool": true` OK
- BUT the rendered job still fetched stock (FALLBACK [Free Video]) - `localPool`
  never reached `acquireAssets`. `candidates.json` showed `pexels` refs, 0
  `local-pool`.

### Root cause
The CLI's `acquireDeps` is a separate literal:
```ts
const acquireDeps: any = {
    fetchVisual: async (...) => { ... },
    download: async (...) => { ... },
    fetchMusic: async (...) => { ... },
    // ... no localPool here
};
```
`req.candidatesPerAsset` is copied in manually (~line 387) but NEW fields are
NOT. So `localPool` was dropped between job-parse and `acquireAssets`.

### Fix
Set the flag in BOTH places:
1. `pipeline.ts` - the `if (req.localPool) acquireDeps.localPool = true;` block
   (handles the library/orchestrator path).
2. CLI - add it as the FIRST property of the `acquireDeps` literal (~line 400):
   ```ts
   const acquireDeps: any = {
       localPool: job.localPool ?? false,
       fetchVisual: async (...) => { ... },
   ```

Verify by rendering a job with the flag set and grepping `candidates.json`:
`"source": "local-pool"` should be present and `pexels`/`pixabay` refs should be 0.

### General rule
Any new `AcquireDeps` field controlled by a job-JSON flag MUST be set in BOTH:
- `src/agentic/orchestrator/pipeline.ts` (the
  `if (req.X) acquireDeps.X = true;` block), AND
- `src/adapters/cli/agentic-modular.ts` (the `const acquireDeps: any = { ... }`
  literal, ~line 400) - add it as a literal property there too.

The MCP path (`register-agentic-tools.ts`) builds its own deps as well - check it
if the feature is also exposed over MCP.
