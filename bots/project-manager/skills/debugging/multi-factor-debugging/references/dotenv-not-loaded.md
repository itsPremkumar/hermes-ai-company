# dotenv Not Loaded at Entry Point

## Symptom

Pipeline runs but reports API keys as missing (`"No API key set"`, `"Missing
credential"`) even though `.env` file exists with the key.

```
⚠ [PEXELS] No API key set, skipping Pexels video search
```

## Root Cause

The project has `dotenv` in `package.json` dependencies but **no entry point
calls `dotenv.config()`**. Environment variables sit in `.env` file but the
runtime never reads them.

## Fix

Add `dotenv.config()` at the **very top** of every bin/ entry point, before any
other imports:

```typescript
// bin/agentic-run.ts (top of file)
import dotenv from 'dotenv';

// Load .env from project root before anything else
dotenv.config();
```

## Detection

Test directly from the shell:

```bash
# If key is MISSING → dotenv.config() not being called
node -e "require('dotenv').config(); console.log('KEY:', process.env.PEXELS_API_KEY ? 'SET' : 'MISSING')"

# If key is SET → the pipeline entry point isn't calling dotenv
```

## Prevention Checklist

When working on a TypeScript/Node project with `.env` files:

1. Check that EVERY entry point (bin/*.ts, src/cli.ts, src/index.ts) calls
   `dotenv.config()` or loads environment variables early.
2. Search for existing `dotenv.config()` calls: `grep -rn "dotenv" src/ bin/`.
3. If `dotenv.config()` only appears in non-entry modules (e.g. MCP admin
   tools), the main pipeline is not loading `.env`.

## Why This Happens

- dotenv is often added as a dependency for a specific feature (e.g. MCP env
  tools) but the main entry point was never updated.
- Projects that started with manual `export` or shell wrappers may have added
  `.env` files without adding the import.
- tsx/ts-node loaders do NOT auto-read `.env` files.

## Related

- `tsx-cache-staleness.md` — tsx caches may also re-run old code even after
  adding the import.
