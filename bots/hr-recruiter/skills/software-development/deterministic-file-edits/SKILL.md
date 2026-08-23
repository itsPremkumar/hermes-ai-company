---
name: deterministic-file-edits
description: Recover when the `patch` tool silently fails or reports success without applying — especially on regex literals, backslashes, escaped characters, or generated code. Use a deterministic node `.cjs` script run via `terminal` instead of fuzzy replace. Also covers the isolate-verify-merge workflow for risky/credential-gated features.
---

# Deterministic File Edits (when fuzzy `patch` lies)

## When to use this skill
- `patch` returns "success" / "file modified" but a follow-up `read_file` shows the **old content still there** (classic on `\\s`, `\\[`, regex literals, YAML with backslashes, minified/generated strings).
- Fuzzy matching on special characters **silently no-ops** — no error, no change.
- You need a **byte-exact** edit and cannot trust fuzzy replace.

## The trap (cost this session ~8 wasted turns)
The `patch` tool uses 9 fuzzy-matching strategies. On backslash/regex/generated content it can report success while applying **nothing**. Symptoms:
- Repeated "success" then `read_file` still shows old text.
- Eventually a real error like `no_unresolved` or `idempotent_no_progress_warning`.
Never trust a "success" from `patch` on special-char content — always `read_file` immediately after.

## The fix: deterministic node script via `terminal`
Author a tiny `.cjs` that does an exact `String.split(from).join(to)`. To avoid the agent's OWN backslash-escaping problem while writing the script, pass the exact `from`/`to` strings through a **JSON file** (JSON `\\` reliably means one backslash).

Reusable script: see `scripts/exact-replace.cjs`. Usage: see `references/usage.md`.

### Minimal inline version
```js
const fs=require('fs');
const p='src/lib/script-parser.ts';
let s=fs.readFileSync(p,'utf8');
const from=JSON.parse('"'+process.argv[2]+'"'); // pass JSON-escaped string
const to=JSON.parse('"'+process.argv[3]+'"');
if(!s.includes(from)){console.log('NOT FOUND');process.exit(2);}
s=s.split(from).join(to);
fs.writeFileSync(p,s);
console.log('OK');
```
Run: `node fix.cjs "\"\\\\s\"" "\"\\s\""` — note argv is itself JSON, so `\\` on CLI = one backslash in the arg.

## Pitfalls
- **`replace_all` on repeated identical blocks corrupts files.** If `old_string` appears N times, `replace_all=true` does NOT cleanly replace each copy. When the block contains regex/backslashes (e.g. `script-parser.ts`'s `const cleanText = line\n .replace(/\[Visual:?.../gis, '')` chain repeated once per scene-push site — observed 3 copies), the matcher **doubles backslashes** (`\s` → `\\s`) AND injects the new text into every copy, wrecking the file (observed: 6 new `.replace()` lines injected 9× with mangled `\\,`/`\\s`). It reports "success" while corrupting.
  **Protocol:** (1) `git checkout -- <file>` immediately to recover a known-good state (committed work is safe). (2) Redo with a non-fuzzy method — **Python via `execute_code`** (`open(p).read()` → `s.replace(anchor, anchor+addition)` → `open(p,'w').write(s)`; assert `s.count(anchor)==N` first) is fastest when available; else the node `.cjs`. (3) Re-read + `tsc --noEmit` to confirm clean.
- **`execute_code` is NOT always blocked.** The stale claim "execute_code is often BLOCKED" is environment-dependent. In the AVS session `execute_code` (Python `open().read/write`) ran fine and was the cleanest deterministic editor for multi-occurrence edits — exact `str.replace`, no fuzzy matching. Only fall back to the node `.cjs` when `execute_code` actually errors with a BLOCKED message. (The node `.cjs` is still required when `execute_code` IS blocked.)
- **`String.raw\`\\s\`` is NOT the file's bytes** — `String.raw` of `\\s` is `\s` (one backslash). If unsure what's actually in the file, dump char codes (see `references/usage.md`).
- **`sed` in MSYS mangles backslashes** — prefer node or Python.
- **Markdown table pipes get doubled by `patch`.** The `|` characters in tables are treated as formatting syntax by the fuzzy matcher. See `references/markdown-table-pipes.md`.
- A `split().join()` that finds 0 occurrences means your `from` string doesn't match the real bytes — inspect with char codes before guessing.
- After recovery: `read_file` to confirm, then run the project's `typecheck`/`test`/`lint` for regressions. Never claim done without fresh pass evidence.

## Ffmpeg filtergraph edits — the WORST case for fuzzy `patch` (cost this session ~10 turns)
ffmpeg filter strings are full of backslashes (`\\,` in source = `\,` in the graph) AND
multiple lines share identical tails (e.g. every `drawtext ... enable='between(t\\,..\\,..)'`
ends the same way — the caption-burn line and the kinetic-lowerthird line are nearly
identical). Two failure modes bite hard:
1. **`replace_all` matches sibling lines.** Editing the caption line with
   `old_string` ending in `...enable='between(t\\,${start}\\,${end})'[${out}]'` ALSO
   matches the kinetic line (same tail, different receiver var) and **corrupts it**.
   The tool reports success while breaking a second line.
2. **Backslash counts get doubled/mangled.** The matcher can turn `\\,` into `\\\\,`
   (ffmpeg then fails the filter) or strip them entirely (`between(t,..,..)` with no
   escape → `enable=` parses wrong → black frames / no-op window).
**Protocol — do NOT hand-edit ffmpeg filter backslashes with `patch`:**
1. Match on a **non-backslash anchor** unique to the target line (e.g. the caption line
   has `line_spacing=4`; the kinetic line does not). Build `from`/`to` as exact full lines.
2. Use the node `split().join()` script (below) so bytes are exact — no fuzzy matching.
3. If `patch` reports "Found N matches for old_string" → STOP; it will corrupt siblings.
   Switch to the node script immediately.
4. ALWAYS re-run `tsc` + a 1-scene render + `blackdetect` after a filter edit — a doubled
   or missing `\\,` surfaces instantly as a failed filter or an all-black clip.
Reusable snippet (run via `terminal` when `execute_code` is blocked; if execute_code runs, prefer the Python `open().read/write` form for the same effect):
```js
const fs=require('fs');
let lines=fs.readFileSync('src/agentic/orchestrate.ts','utf8').split('\n');
for(let i=0;i<lines.length;i++){
  if(lines[i].includes('line_spacing=4') && lines[i].includes("enable='between(t")){
    // replace the whole enable clause with the correct single-backslash form
    lines[i]=lines[i].replace(/enable='between\(t[^)]*\)'/, "enable='between(t\\,${start}\\,${end})'");
  }
}
fs.writeFileSync('src/agentic/orchestrate.ts', lines.join('\n'));
```
(The `\\,` in the JS replacement string → `\,` in the file, which is what ffmpeg needs.)

## Inspect actual bytes (when escaping is confusing)
```js
const fs=require('fs');
const line=fs.readFileSync('src/lib/script-parser.ts','utf8').split('\n')[70];
for(let i=0;i<line.length;i++){ if(line[i]==='\\') console.log(i,'BACKSLASH'); }
console.log(JSON.stringify(line));
```
`JSON.stringify` doubles each backslash, so `\\\\s` in output = two backslashes in the file; `\\s` = one.

## Isolate-verify-merge (user-endorsed workflow)
For features needing credentials/network (OAuth upload, live API calls):
1. Build in a **separate subfolder** with its own `package.json` + `tsconfig.json`.
2. Keep external SDKs **lazy-imported** (`await import('googleapis')`) so dry-run/sandbox paths need zero deps and run fully offline.
3. Write offline tests (no network/credentials) and verify them.
4. Only then merge into main behind an env flag (e.g. `YOUTUBE_ENABLED`), reusing existing stores.
This keeps the main branch green and lets you prove logic before touching auth.

## Verification checklist (always run after a recovery edit)
- `read_file` the changed lines — confirm bytes actually changed.
- `npm run typecheck` (or `tsc -p tsconfig.json --noEmit`)
- `npm run test` / `npm run test:unit`
- `npx eslint <files>` — confirm 0 errors (warnings may be intentional)
- Report exact pass/fail counts. Do not say "verified" without running.

## Support files in this skill
- `scripts/exact-replace.cjs` — runnable exact-string replacer (pass a `replace.json`).
- `references/usage.md` — step-by-step + byte-inspect snippet + escaping rules.
- `references/patch-quirks.md` — the real script-parser.ts case that motivated this skill.
- `references/write_file-vanish-recovery.md` — when write_file reports success but the file is absent from disk.
- `references/markdown-table-pipes.md` — `patch` doubling `|` pipes in markdown tables and recovery strategies.
