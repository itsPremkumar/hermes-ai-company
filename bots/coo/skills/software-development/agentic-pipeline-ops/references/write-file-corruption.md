# write_file / patch corruption trap (agentic-pipeline-ops)

Captured 2026-07-18 during the second build pass of the AVG discrete-ops
layer (8 new ops + router + chain dispatcher + 20-tool MCP registration).
This is the single most expensive debugging loop of that session — document
it so the next pass avoids it.

## What happens
The file-persistence path in this Hermes environment normalizes/stores some
characters incorrectly when writing .ts via write_file (and similarly
when editing with patch). Concretely observed:

1. Non-ASCII arrow (U+2192) inside a template literal (e.g. the
   okr helper textResponse(`-> ${out}`)) is written as a corrupted
   multibyte sequence. tsc then fails to parse the string and reports a
   generic error far away from the line.
2. Backslash sequences double up. Regex like .replace(/\\/g, '/')
   lands as /\\\\/g (invalid regex) - or a path.basename(f)) call gains
   a stray extra ). Inline split(/(?:\n|;\s*)/) turns the \n into a
   literal backslash-n inside the regex (still parses, but a latent smell).
3. The error location lies. tsc reports TS1005: '{' expected,
   TS1136: Property assignment expected, TS1128: Declaration or statement
   expected at the NEXT tool/function boundary (e.g. line 107 of the
   register file when the corruption was actually at line 28). You chase the
   wrong line for a long time.

## How to AVOID it (cheapest)
- Use ASCII only: use "->" not the arrow character.
- Never put a regex-with-backslash inside a template literal; precompute:
  const font = fontSafe().replace(/\\/g, '/'); then embed ${font}.
- When writing a many-branch tool handler, prefer a switch or an
  applyOp(name, file, out, opts) helper over 8 inline
  cropVideo(f, path.join(outDir, path.basename(f)), {preset}) calls - the
  path.basename(f)) double-paren bug came from exactly this shape.

## How to FIX it when it already happened
patch CANNOT see the normalized byte, so re-patching the same string
reports "old_string and new_string are identical" and does nothing. Instead,
rewrite the whole file deterministically:

    # run via terminal as `python` (NOT python3 - not on PATH here)
    p = r"C:/one/Automated-Video-Generator/src/adapters/mcp/register-operations-tools.ts"
    s = open(p, encoding="utf-8").read()
    # fix the specific corruption: extra ')' after basename(...)
    s = s.replace("path.basename(f)), { preset", "path.basename(f), { preset")
    open(p, "w", encoding="utf-8").write(s)

Then npx tsc --noEmit and read the FIRST error by line number (sort the
output). Repeat for each remaining corruption. This is far faster than
hunting through patch.

## Symptom-to-cause quick map
| tsc says | likely real cause |
|----------|------------------|
| TS1005 '{' expected at a server.registerTool(... async (a)=>{ line | an arrow char or unterminated string earlier in the file |
| TS1128 Declaration or statement expected at EOF | a ) or } is missing somewhere above (often a doubled/stray paren in a batch/if-else handler) |
| error moves when you fix the reported line | the reported line is a victim; the cause is above it |

Related: deterministic-file-edits skill (same class, patch-oriented).
