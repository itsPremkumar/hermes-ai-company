# AVG agentic-core bug-hunt (read-only review of src/agentic/**)

Task shape: "bug-hunt the agentic core, report VERIFIED real errors with file:line +
suggested fixes, NO edits, NO commits." Deliverable = a report backed by real tool
output, not a patch.

## Method that worked
1. Baseline first: `npm run typecheck` (clean) + `npx tsx --test "src/agentic/*.test.ts"
   "src/agentic/operations/*.test.ts"` (241 pass). A green suite means the real bugs are
   the ones tests DON'T exercise (auth headers, regex literals, dead fallbacks). Do not
   stop at "tests pass" — that is the starting line for a bug-hunt, not the finish.
2. Grep risky patterns via `rg` (terminal), then read every non-test file in full.
   High-yield greps: `Bearer|Authorization`, `throw|throw new`, `JSON.parse`,
   `readFileSync`, `replace(/`  (regex literals), `return null`.
3. Verify each suspect empirically before reporting. For a regex bug, run a 3-line
   `node -e` repro comparing the buggy vs intended pattern. For a header bug, `git blame`
   the line to prove it's a committed artifact and not a display/redaction artifact.

## P-class bugs found (durable, reusable classes)

### PB1 — Corrupted auth header: `Bearer` replaced by `***`
`brain.ts:69` and `brain.ts:384`:
```
headers: { Authorization: `*** ${o.openRouterKey}`, 'Content-Type': 'application/json' }
```
The literal `*** ` should be `Bearer `. Every OpenRouter call sends `*** sk-...` → 401 →
`completeJSON`/`visionVerify` return null → agent SILENTLY falls back to heuristics. The
"free model" tier is entirely dead in production, and because the fallback is graceful,
NO test and NO runtime error ever surfaces it.
- Detection: grep `Authorization`. If you see `***` in a SOURCE file header, it is almost
  certainly a real corruption (a secret-scrubber or bad find/replace), NOT a redaction of
  your view. Confirm with `git blame -L N,N <file>` — the raw committed text shows `*** `.
- This is a CLASS: any `Authorization`/`Bearer`/API-key header where the scheme token was
  mangled. Check both the text-completion AND the vision path — the same bug was copy-pasted
  into both.
- Fix: `*** ${key}` → `Bearer ${key}` at both sites.

### PB2 — Double-escaped regex literal in a `.replace()` strips nothing
`orchestrate.ts:641`: `filename.replace(/\\\\.[^.]+$/, '')`. In a JS source file `\\.`
inside a regex literal matches a LITERAL backslash+char, so on `"candidate_1.png"` it
matches nothing and the extension is NOT stripped (label keeps `.png`). Intended:
`/\.[^.]+$/`. Sibling line 623 uses the correct single-backslash form — inconsistency is
the tell. Verify with `node -e` (escape carefully for the shell: the source `\\\\.` needs
`\\\\\\\\.` on a bash `-e` command line, or drop into a .cjs file). Low severity (cosmetic)
but a real, provable defect. See also the `deterministic-file-edits` skill — regex/backslash
literals are exactly where the fuzzy `patch` tool misbehaves.

## Non-bugs worth recording (so a re-hunt doesn't re-flag them)
- `manifest: manifest!` non-null assert (orchestrate) is safe: `runFinalGate` only sets
  `pass:true` when `manifest !== null`.
- `autopilot.ts` `VIDEO_CACHE` (`agentic-pipeline/.video-cache.json`) is `rmSync`'d by the
  self-heal fixes but NEVER written by the pipeline (acquire uses an in-memory
  `sharedImagePool`, reset per-run). The "clear stale cache" fix is a harmless no-op / dead
  code — report as a note, not a crash.
- Dead code (harmless): `escapeFilterPath` defined, never called; `audioInputArgs`/`audioMap`
  computed but only used on the non-segmented render branch.

## Report format the user wants
Group as CONFIRMED REAL BUGS (severity + file:line + what breaks + repro + fix) FIRST, then
a short "investigated, determined non-bugs" honesty section so the reader trusts the sweep
was exhaustive. Be explicit that no files were edited/committed.

## Tooling gotcha on this Windows/MSYS box
`search_files` (ripgrep wrapper) fails with `os error 3 / cannot find the path` when handed
paths outside the session cwd tree (e.g. `C:\one\...` while cwd is `C:\Users\...`) — it
mis-translates the drive path to `/c/...`. Do NOT loop retrying it. Fall back immediately to
`rg -n <pattern> <path>` through the `terminal` tool (bash/MSYS handles `/c/one/...` and
native `C:\one\...` fine). `read_file` with the native `C:\...` path works regardless.
