# Parsing `git blame --line-porcelain` (Node)

Recipe proven while building `todoscope` (2026-08-01): porcelain output is the fastest way to map file lines → {author, authored-at} for debt-age tracking ("how long has this TODO been rotting").

## Format (what the output ACTUALLY looks like)

`--line-porcelain` has **NO blank-line separators between records**. Each record:

```
<sha> <orig-line> <final-line> [group-size]   ← first line of each record
author <name>
author-mail <...>
author-time <epoch-seconds>
author-tz +0530
committer <name>
committer-mail <...>
committer-time <epoch-seconds>
committer-tz +0530
summary <commit subject>
boundary                                  ← only for boundary commits
filename <path>
<TAB><content>                            ← the actual source line, tab-prefixed
<next record starts immediately — no blank line>
```

Key traps:
- **Final line number = 3rd field** of the sha line; orig line is 2nd.
- Content lines are TAB-prefixed; blank lines are NOT separators (the classic `split('\n')` + `l === ''` recorder silently produces a 1-entry map).
- **Windows CRLF**: git emits `\r\n` — split on `/\r?\n/`, or the `''` separator check never fires.
- `author-mail` also starts with `author` — match `l.startsWith('author ')` (trailing space) to skip it.

## Parsing algorithm

```ts
const entryRe = /^[0-9a-f]{40}\s+(\d+)\s+(\d+)/;
let curLine = 0, author = '', time = '';
for (const l of stdout.split(/\r?\n/)) {
  const e = entryRe.exec(l);
  if (e) { curLine = Number(e[2]); author = ''; time = ''; }
  else if (l.startsWith('author ')) author = l.slice(7);
  else if (l.startsWith('author-time ')) time = l.slice(12);
  else if (l.startsWith('\t')) map.set(curLine, { author, dateIso: new Date(Number(time) * 1000).toISOString() });
}
```

## Operational notes

- **One `git blame` per FILE, not per line/match** — spawn once per file that has matches (whole-file porcelain), then look up by line number. A repo-wide debt scan = ~1 spawn per file with hits. Set a large `maxBuffer` (128 MB) for big files.
- `spawnSync('git', ['blame', '--line-porcelain', '--', fileAbs], { cwd: <SCANNED ROOT>, windowsHide: true })` — pass the scanned root as `cwd`, NOT `process.cwd()`, or git fails to resolve repos for absolute external paths (e.g. scanning another project's tree).
- Non-git dir / untracked file → `status !== 0` → return empty Map; caller treats missing author as "unknown" (report omits the column) rather than erroring.
- `author-time` is the AUTHOR date (when the line was written) — the right clock for "debt age".
- Tag-scanning false positives: a loose `\bBUG\b` regex matches prose ("see bug #4"). Require a separator for strict tags: `new RegExp(\`\\bBUG\\b[\\s]*[:\\-\\])][\\s]*(.*)\`, 'i')` — colon/dash/paren required, optional surrounding whitespace; loose tags (TODO/FIXME/HACK) may keep any separator including space.
