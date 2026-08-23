# tsx Cache Staleness Debugging Recipe

Reproduced and confirmed during multi-factor debugging of a video-generation pipeline.

## Symptom

You patched TypeScript source files, verified the diff with `git diff`, ran the
pipeline via `npx tsx bin/agentic-run.ts`, but the output did NOT reflect the
change. The old behaviour persisted.

## Root Cause

`tsx` compiles TypeScript to a JS cache in `/tmp/tsx-*` and `~/.cache/tsx/`.
If the cache timestamp is newer than the source file, tsx serves the cached
compiled version even though the source has changed.

## Detection

```typescript
console.log('[DEBUG-a4f2] NEW CODE IS RUNNING', uniqueVariable);
```

Insert near your fix. Run the pipeline. If the log does not appear in stderr
or stdout, the cache is serving old code.

## Fix

```bash
rm -rf /tmp/tsx-* ~/.cache/tsx
```

## Prevention

Add this to your "verify fix" step checklist when using tsx-based tooling.

## Additional Context

In the Automated-Video-Generator project:

1. The `visual-fetcher.ts` module uses an in-memory cache object (`getCache()`)
   that is populated GLOBALLY once per process. Clearing the workspace/cache
   directory WITHOUT restarting the process has no effect — the in-memory
   object still holds stale entries.

2. The pipeline (`pipeline.ts`) has its own shared state in `sharedImagePool`
   that persists across scene requests. This pool short-circuits the
   per-scene Pexels search — a completely separate bug from the tsx cache
   issue, but both can make it look like "the fix didn't work".

The combination of:
- tsx code cache (serving pre-fix bytecode)
- In-memory data cache (serving pre-fix search results)
- Pool logical short-circuit (bypassing the fix entirely)

...meant that THREE separate mechanisms could each independently cause "fix was
applied but didn't take effect". Always check all three.
