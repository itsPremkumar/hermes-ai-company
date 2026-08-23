---
name: multi-factor-debugging
description: "Debug situations where a single symptom has multiple independent root causes — includes cache-staleness detection and isolation-testing techniques."
version: 1.0.0
author: Hermes Agent (curated)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, multi-factor, cache-staleness, isolation-testing, tsx, pipeline]
    related_skills: [systematic-debugging, verify-before-integrate, test-driven-development]
---

# Multi-Factor Debugging

## Overview

Standard debugging assumes one root cause → one fix. In practice, a single
visible symptom (white frames, all scenes identical, crash on load, empty page)
can be the product of TWO OR MORE independent bugs that each contribute to the
same failure mode.

**This is more common than you think and is the #1 reason "I fixed the bug but
it's still broken".**

This skill provides techniques for detecting and handling multi-factor bugs,
plus two companion patterns: cache-staleness detection and isolation testing.

## When to Use

- The symptom you're debugging has multiple subsystems feeding into the same
  output path (e.g. asset selection + rendering both affect output frames).
- You found a root cause, fixed it, ran the repro, and the symptom changed but
  did not fully resolve.
- The system has a cache layer (in-memory, file, compiled-code) that could mask
  changes.
- The full repro pipeline takes minutes — you need a faster feedback loop.

## The Multi-Factor Checklist

When a fix doesn't resolve the symptom:

| # | Question | Action |
|---|----------|--------|
| 1 | Was the fix actually deployed / is the new code running? | Check cache staleness (§Cache) |
| 2 | Did your fix address the root cause or just a symptom? | Trace data flow from input to output through your fix site |
| 3 | Could there be a SECOND independent root cause? | See §Multi-Factor below |
| 4 | Did you trace the complete data flow since applying the fix? | Follow every path from source to output |

## Detecting Multi-Factor Bugs

### Signals

**Strong signals that a second root cause exists:**
- You fixed bug X, the output changed but is still wrong (e.g., went from
  "white frame" to "different video per scene but all same asset").
- Two completely unrelated subsystems converge on the same output (e.g., an
  asset-fetch module AND a rendering module both affect pixel output).
- Each fix reveals a new symptom in a different subsystem — the chain breaks
  but the final output is still broken.

**Weak signals (investigate but less certain):**
- The code has no tests for the specific output path.
- The system has multiple fallback tiers (ladder, pool, placeholder).
- You're debugging with production data and can't easily isolate paths.

### Process

1. **Fix one root cause → re-run the tight loop → observe the symptom.**
   - If symptom FULLY resolved → done (single-factor bug).
   - If symptom CHANGED but not resolved → note the change, keep looking.
   - If symptom UNCHANGED → check cache staleness first (§Cache).

2. **Map every subsystem that feeds the output.**
   ```
   Input → [Subsystem A] → [Subsystem B] → Output
   ```
   For a video pipeline:
   ```
   Topic → [Agent writes keywords] → [Visual Fetcher queries APIs] →
   [Downloader caches files] → [Render pipeline assembles scenes] →
   [Output MP4]
   ```

3. **Test each subsystem independently** using isolation testing (§Isolation).

## Cache Staleness Detection

### Problem

Dynamic runners (tsx, ts-node, nodemon with tsx) cache compiled JavaScript.
Source changes may NOT take effect until the cache is cleared, even when the
source file clearly has the fix.

- tsx caches to `/tmp/tsx-*` (Linux/Mac/Windows/MSYS) and `~/.cache/tsx`.
- The cache is per-process — a fresh `npx tsx` call may or may not recompile
  depending on file modification timestamps and cache TTL.

### Detection

Add a temporary unique log statement near your fix:

```typescript
console.log('[DEBUG-a4f2] using cacheKey:', cacheKey);
```

- If the log appears in output → your code IS running, problem is elsewhere.
- If the log does NOT appear → cache is serving old compiled code.

### Fix

```bash
rm -rf /tmp/tsx-* ~/.cache/tsx
```

### Prevention

Add cache clearing to your "verify fix" workflow step. When debugging a
pipeline that uses tsx/ts-node:

1. Patch source.
2. Clear tsx cache.
3. Run isolation test (fast).
4. If isolation test passes, clear tsx cache again.
5. Run full pipeline.

## Isolation Testing

### Problem

The full pipeline (e.g. video generation) takes minutes per run. Debugging
cycles are painfully slow.

### Solution

Write a throwaway test script that imports and exercises a SINGLE function with
controlled inputs.

### Recipe

```typescript
// _test_foo.ts — delete after use
import { functionUnderTest } from './relative/import/path.js';

async function main() {
    for (const input of [0, 1, 2]) {
        const result = await functionUnderTest(input);
        console.log(`input=${input}: url=${result.url}`);
    }
}
main();
```

```bash
npx tsx _test_foo.ts
```

### Hints

- Use the **same import path** as the actual codebase (including `.js` extension
  for ESM).
- Save in project root, run immediately, delete after use.
- When the test WORKS but the pipeline doesn't, suspect cache staleness or a
  **different code path** (like a short-circuit that bypasses your function).

### Real Example

Instead of running a 5-minute video pipeline to test scene diversity:

```typescript
// _test_videos.ts
import { fetchVisualsForScene } from './src/lib/visual-fetcher.js';

for (let i = 0; i < 3; i++) {
    const r = await fetchVisualsForScene(['solar system'], true, 'portrait', undefined, i);
    console.log(`Scene ${i}: url=${r.url}, dur=${r.duration}s, size=${r.width}x${r.height}`);
}
// → 5 seconds, proves resultIndex selection works
```

## Production Readiness Verification (Proactive Multi-Factor)

Instead of waiting for a bug report, you can discover **every independent issue**
in a pipeline BEFORE claiming production-readiness. This is proactive multi-factor
debugging: run the full pipeline once, inspect every layer of its output
independently, and fix all issues before declaring "done".

### When to Use

- You're asked "make this app production ready" or "find and fix all the bugs".
- You've refactored a large module and need to verify nothing broke.
- The pipeline has many upstream dependencies (API keys, free media providers,
  TTS engines, bundled binaries).

### The Layer-by-Layer Check

Run the pipeline once, then inspect its output systematically:

| Layer | What to check | Common failures (from real sessions) |
|-------|---------------|--------------------------------------|
| **Environment** | API keys loaded? `.env` read? | `dotenv.config()` never called at entry point — see `references/dotenv-not-loaded.md` |
| **API sources** | Pexels/Pixabay/Wikimedia reachable? | 403/429 from Wikimedia due to bot User-Agent blocking |
| **Downloads** | Files actually landed? Size plausible? | Zero-byte files, 403/429, placeholder fallback |
| **Voiceover/TTS** | TTS engine configured and running? | `TTS_PROVIDER=voicebox` with no voicebox installed, falls through silently |
| **Background music** | Free music providers responding? | `open-lofi` / `internet-archive` endpoints return 404 (stale URLs) |
| **Render** | Expected vs actual duration? Codec? | Placeholder image → short scene → total duration mismatch |
| **Post-render checks** | Built-in QA gates | Black frames, frozen frames, clipping, loudness — each is an independent fix |
| **Plugin startup** | PluginRegistry warnings | "already registered, overwriting" — duplicate registration |

### Process

1. Run the full pipeline with a simple topic (use `ffmpeg` renderer, `agent` backend).
2. Collect ALL warnings, errors, and QA failures from the output — don't fix
   anything yet, just catalog.
3. Sort by layer (above table) and fix each layer's issues independently.
4. Re-run and verify the QA gate count dropped.
5. If the output changed but is still wrong, apply **§Multi-Factor** above.

### Key Technique: Test the Echo

When the pipeline says "API key not set" but the `.env` file has one:

```bash
# Test whether the runtime can see the env var at all
node -e "require('dotenv').config(); console.log('KEY:', process.env.PEXELS_API_KEY ? 'SET' : 'MISSING')"
```

- If `SET` → the pipeline isn't loading dotenv → fix the entry point.
- If `MISSING` → the .env file is absent or named wrong.

This isolates the "is dotenv working?" question from "is the API key valid?".

## Pipeline Short-Circuit Pattern

A common multi-factor pattern: the pipeline has an **early-return** or
**short-circuit** that bypasses your fix entirely — often through a cache,
pool, or fallback check.

### Example

```typescript
// Bug: all scenes get the same video
const pool = await getImagePool(); // ← built ONCE at first call
if (pool.length > 0) {
    return pool[sceneIndex % pool.length]; // ← short-circuits Pexels search!
}
// ... Pexels search with per-scene resultIndex NEVER REACHES
```

### How to detect

1. Read the code path from the call site to the return site.
2. Look for early returns, cache hits, pool checks, or placeholder assignments
   that could exit before reaching your fix.
3. Test with an isolation script — if the isolation test passes but the
   pipeline fails, a short-circuit is likely.
