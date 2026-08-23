---
name: node-cli-scaffolding
description: Scaffold and ship a production-grade Node.js CLI tool — ESM package, interactive prompts, config generation, npm distribution, free/pro tier structure. Covers bin entry setup, inquirer-based interactive flows, JSDoc-typed config builders, save-to-file output, and premium upgrade navigation.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
---

# Node.js CLI Scaffolding

End-to-end recipe for building a **Node.js CLI tool** packaged for npm distribution with interactive prompts, generated output, and optional free/pro tier separation. Use for: config generators, scaffolding tools, interactive wizards, utility CLIs that produce structured output.

## When to use

- A user asks to build a "CLI tool", "interactive generator", "wizard", or "scaffolder"
- Starting a new Node.js executable package from scratch
- Adding interactive prompts (inquirer) to an existing script
- Packaging a dev tool for npm with a `bin` entry

## Scaffold structure

```
agent-config-generator/
├── src/
│   └── index.js          # CLI entry (shebang + ESM)
├── pro/                   # Premium / paid-tier assets
│   └── company-template.json
├── package.json           # name, bin, type: module, deps
├── README.md              # Professional docs
└── .gitignore
```

## Step-by-step

### 1. Package setup (`package.json`)

- `"type": "module"` — ESM across the board.
- `"bin": { "<command-name>": "./src/index.js" }` — single bin entry.
- `"files": ["src/", "README.md", "LICENSE"]` — whitelist what ships to npm.
- `"engines": { "node": ">=18.0.0" }` — inquirer 12+ requires node 18.
- `"scripts"`: `"start"`, `"dev": "node --watch src/index.js"`, `"test"`, `"prepublishOnly"`.

### 2. Entry point (`src/index.js`)

```
#!/usr/bin/env node
import inquirer from 'inquirer';
```

- **Shebang** `#!/usr/bin/env node` is critical for the `bin` to work on Unix.
- **ESM** — use `import`, not `require`. Inquirer 12+ is ESM-only.
- **Imports** node built-in modules: `import { writeFile } from 'node:fs/promises'`.
- **JSDoc** type the config schema with `@typedef` so the code is self-documenting.

### 3. Banner

Print a box banner at startup with the tool name, version, and tagline. Uses `console.log` and `String.padEnd` for alignment.

```js
function printBanner() {
  console.log('');
  console.log('╔═══════════════════════════════════════════════════════════╗');
  console.log('║          Agent Config Generator  v' + VERSION.padEnd(38) + '║');
  console.log('╚═══════════════════════════════════════════════════════════╝');
  console.log('');
}
```

### 4. Interactive prompts (inquirer)

**Pattern for each prompt:**

```js
{
  type: 'list',       // 'list', 'checkbox', 'confirm', 'input'
  name: 'fieldName',
  message: 'Prompt text?',
  description: 'Helpful subtitle',
  choices: [...],
  default: 'default_value',
  when: (answers) => answers.prevField === 'xyz',  // conditional
  validate: (input) => input.length > 0 || 'Error message',
}
```

- **List choices** — always set `loop: false` so arrow-up at the first item doesn't jump to the bottom.
- **Checkbox** — `validate: (input) => input.length > 0 || 'Select at least one'`.
- **Conditional prompts** — use `when` to show a custom input only when `custom` is selected.
- **Error handling** — catch `ExitPromptError` (inquirer 12+ throws this on Ctrl+C):

```js
try {
  const answers = await runPrompts();
  // ... handle answers
} catch (err) {
  if (err instanceof Error && err.name === 'ExitPromptError') {
    console.log('\n  Cancelled.\n');
    process.exit(0);
  }
  die(String(err));
}
```

### 5. Config builder

Separate the logic from presentation. After collecting answers:

```js
function buildConfig(answers) {
  const model = answers.model === '__custom__' ? answers.customModel : answers.model;
  return {
    name: 'Paperclip Engineer',
    adapterType: 'hermes_local',
    role: answers.agentRole,
    adapterConfig: { model, provider, ... },
  };
}
```

- Resolve custom/fallback values before building.
- **JSDoc** the return type with `@typedef` and `@returns`.

### 6. Output (print / save / both)

After generating, let the user choose:

```js
{ type: 'list', name: 'action', message: 'What to do?',
  choices: [
    { name: '📋  Print to console', value: 'print' },
    { name: '💾  Save to file', value: 'save' },
    { name: '📋 + 💾  Both', value: 'both' },
  ],
}
```

- **Save** — use `path.resolve(path)` then `writeFile(resolved, json + '\n', 'utf-8')`.
- **mkdirp** — `mkdirSync(dir, { recursive: true })` before writing.
- **Handle errors** — wrap in try/catch with `die()`.

### 7. Premium / PRO tier

The free version generates single outputs. The PRO tier lives in a separate `pro/` directory with multi-agent or orchestration configs. Reference it in an upsell banner after output.

```js
function showPremiumUpsell() {
  console.log('🚀 Need multi-agent orchestration?');
  console.log('PRO version ($29) generates a complete company config...');
}
```

### 8. CLI flags

```js
if (flag === '--help' || flag === '-h') { printHelp(); return; }
if (flag === '--version' || flag === '-v') { console.log(VERSION); return; }
```

### 9. Professional README

A README for an npm-published CLI tool should include:

- Badges (npm version, license, node version)
- Overview paragraph — what problem it solves
- Installation (`npm install -g` / `npx`)
- Interactive usage screenshots (block-art simulating terminal output)
- Table of the prompts/questions
- Output example (JSON block)
- Premium upsell section with link
- API reference table
- Development instructions (clone, install, dev)

## Error-handling patterns

| Situation | Pattern |
|-----------|---------|
| User hits Ctrl+C | Catch `ExitPromptError`, exit gracefully |
| File write fails | Wrap in try/catch, call `die(msg)` |
| Invalid input | `validate` function returns error string |
| Missing/invalid CLI args | `--help` shows usage |

## Windows path pitfall (MSYS / git-bash)

When running on Windows under MSYS (git-bash), the `terminal` tool translates `/c/...` to `C:\...`, but `write_file`/`patch` resolve paths relative to the Hermes workspace (`C:\Users\<user>`). Consequently, passing `/c/one/project/file` to `write_file` lands at `C:\c\one\project\file` — not the intended `C:\one\project\file`.

**Fix:** Use `terminal` for file operations on paths under `/c/...`, `C:\...`, etc. OR pass native Windows paths to `write_file`/`patch`. If files already landed in the wrong place, `cp` them from `C:\c\...` to `C:\...` via `terminal`.

## Windows / tooling pitfalls (verified 2026-07-31)
- **`node --test dist/test/` FAILS on Windows** (trailing slash): node tries to `require("dist\test")` as a module → MODULE_NOT_FOUND / ERR_TEST_FAILURE. Pass explicit files instead: `node --test dist/test/scoring.test.js dist/test/github.test.js`.
- **Disk-cached CLI tools mask your own fixes**: if the tool caches API responses to disk (TTL cache), a stale entry hides the bug you just fixed — re-verify with the cache-bypass flag (`--no-cache`) after code changes, or you'll chase a ghost.
- **TS `as const` palette vs empty-string fallback**: casting `{reset:'',...}` to an `as const` object type fails (TS2352). Declare `type Palette = {...}` plus separate `COLORS: Palette` and `NO_COLOR: Palette` consts.
- **CLIs that consume the GitHub public API**: see `references/github-api-consumer-quirks.md` — base64 line-wrapping in /readme, lenient Buffer decode, 60 req/hr unauthenticated limit + disk-cache pattern, 403-on-actions = disabled, mandatory User-Agent.
- **`for (const [a, b] of tuple)` destructures the tuple's ELEMENTS, not the pair**: `for (const [open, close] of blockTokens)` where `blockTokens = ['/*', '*/']` yields `open='/'`, `close='*'` then `open='*'`, `close='/'` — the opener gets split into characters and matching silently fails (caught only by a block-comment unit test). Destructure ONCE outside the loop: `const [open, close] = tuple;`, or iterate an array of tuples.
- **Regex escapes: prefer `new RegExp(\`\\b...\`)` template strings over regex literals**: a regex literal carrying double-escapes (`/\\b.../`) trips TS1508 "Unexpected ')'" or matches literal backslashes; the template-string form (`\\b` → string `\b` → regex word-boundary) compiles and behaves. When escape layers stall you, stop reasoning — get byte-level ground truth with `od -c file | grep pattern` (read_file display + JSON transport double-escape and will mislead), and write debug scripts to FILES instead of `node -e "..."` (bash backslash mangling adds a second escape layer). To trace a compiled dist module, copy it, inject `console.error` markers, and run the copy.
- **git-blame integration (debt age, authorship)**: see `references/git-blame-porcelain-parsing.md` — porcelain record layout (no blank separators; `<sha> <orig> <final>` first line; tab-prefixed content), Windows CRLF gotcha, one-spawn-per-file pattern, `cwd` = scanned root, and the strict-tag regex for filtering prose false positives.

## Zero-dependency TypeScript CLI (tsc-built, API-backed, terminal tables)

For a `weather-cli`-style tool (zero runtime deps, global `fetch`, Node >= 18, `tsc` build,
live API + terminal table output) — the non-interactive counterpart to the inquirer flow above.
Verified 2026-08-01 building `C:\one\weather-cli` (22/22 tests green, committed locally).

- **ESM + NodeNext essentials**: `"type": "module"`, `module: NodeNext` + `moduleResolution: NodeNext`,
  and EVERY relative import needs an explicit `.js` extension (`import { x } from './types.js'`) or tsc
  emits TS2835. `rootDir: "."` + `outDir: "dist"` with `include: ["src/**/*", "test/**/*"]` mirrors the
  tree: bin becomes `dist/src/cli.js`, tests compile to `dist/test/*.test.js`, so the test script is
  exactly `npm run build && node --test dist/test/a.test.js dist/test/b.test.js ...`.
- **tsc preserves the shebang**: `#!/usr/bin/env node` on line 1 of `src/cli.ts` survives compilation —
  the emitted `dist/src/cli.js` is directly runnable and linkable.
- **`npm link` works on Windows git-bash without admin** — the bin shim lands in the npm global dir
  (`/c/nvm4w/nodejs/weather-cli` here); confirm with `which weather-cli`.
- **ANSI-colored table cells break padding**: escape sequences add invisible characters, so
  `colored.padEnd(n)` misaligns columns. Keep every row as a `{ plain, display }` pair — pad by
  `plain.length`, render `display`. Only color line-leading tokens to keep this cheap.
- **Backslash-free regex/string hygiene** (extends the regex pitfall above): when a backslash isn't
  strictly needed, delete it — `base.replace(new RegExp('/+$'), '')` needs NO escaping (the constructor
  form has no delimiter), build ANSI codes with `String.fromCharCode(27)` instead of writing `'\x1b'`
  in source (write_file JSON transport mangles `\x1b`/`\b` literals), and assert colors with
  `.includes(String.fromCharCode(27))` instead of a `\x1b` regex.
- **API clients are testable offline via env-injectable base URLs**: read
  `process.env.WEATHER_API_BASE ?? DEFAULT` in a `baseUrl()` function (strip trailing `/` with
  `new RegExp('/+$')`), then the integration test spins up `node:http` `createServer` on port 0, sets
  the env vars, and asserts end-to-end fetch+parse — no network, no mocking library. `node --test`
  runs each test FILE in its own child process, so env vars set in one file never leak into another.
- **Canned fixture-server pitfall**: match `url.pathname === '/forecast'` EXACTLY, not
  `pathname.endsWith('/forecast')` — otherwise an error-path test pointed at `/boom/forecast` gets a
  200 + fixture and `assert.rejects` fails with "Missing expected rejection". Also call
  `server.closeAllConnections()` in the after-hook so keep-alive undici sockets don't hold the runner.
- **Parse `'YYYY-MM-DD'` manually** (`split('-')` + `new Date(y, m-1, d)`) before
  `toLocaleDateString` — `new Date('2026-08-01')` is UTC midnight and shifts a day in negative-offset
  timezones.
- **Transient `TS6053 File not found` lint noise during parallel `write_file` batches**: the patch
  linter compiles the whole program per-file while sibling writes are still in flight — every result
  in a parallel batch can show it. It's a race artifact, not a real error; confirm with one real
  `tsc` run after all writes land.
- Exit-code convention that reads well: `0` success, `1` runtime failure (geocode/API, with a helpful
  message), `2` usage error; `main()` returns the code, the caller sets `process.exitCode`.
- **`spawnSync` BLOCKS the parent event loop — an in-process demo/test server cannot serve a child
  CLI**: when a live demo needs a local http server AND the CLI as a child process in one foreground
  command, `spawnSync` freezes the parent, so the server never responds to the child's fetches →
  every remote check times out (UNREACHABLE) while local checks pass; child exits 1 with EMPTY
  stdout/stderr (misreads as "CLI broken"). Use async `spawn` wrapped in a Promise, awaited from the
  `listen` callback, so the server keeps serving. Also: a demo script OUTSIDE the repo must not
  derive the repo dir from `dirname(import.meta.url)` (one level too high → MODULE_NOT_FOUND) —
  join the repo name explicitly or keep the script inside the repo.
- **Markdown inline-link regex: greedy URL class eats balanced parens**: `[text](https://x/a_(b))`
  with a greedy `[^)\s]+` captures `a_(b` — the closing paren is consumed by the trailing `\)` and
  the balanced group never fires. Use a LAZY core + optional balanced-parens group + paren-excluding
  tail: `[^)\s]+?(?:\([^)\s]*\))*[^()\s]*` (verified fix for linkrot's extractor).
- **`createReadStream` 'data' chunk is `string | Buffer`, not `Buffer`**: typing the handler
  `(chunk: Buffer) => void` fails TS2345 against @types/node 22 — the Readable 'data' payload type
  includes string. Type it `(chunk: string | Buffer)`; `hash.update()` accepts both. (Verified building
  `dupe-hunter`'s `hashFile`, 2026-08-01.)
- **Formatting-loop off-by-one: divide THEN check, or 1024 becomes "1.0 MB"**: a
  `while (v >= 1024) { v /= 1024; i++; }` loop advances one unit too far for exact powers of 1024.
  Use a do-while that divides first: `let i = -1; do { v /= 1024; i++; } while (v >= 1024 && i < units.length - 1);`
  — then 1024 → "1.0 KB", 1048576 → "1.0 MB". Always unit-test the exact powers (1024, 1024**2, 1024**3)
  or this slips through silently.
- **A failing test may assert wrong SEMANTICS, not wrong code**: before "fixing" the implementation,
  re-read the test's assumption and the function's call sites. Real case: `isHiddenDir('.hidden-file.txt')`
  was asserted false ("hidden FILES are scanned") but the helper is only ever called on DIRECTORY names,
  where dot-prefix ⇒ skip is correct — the test was wrong, the code was right. Fix the test, keep the code.
- **`stdout.isTTY` is a TS2339 when streams are injectable**: typing CLI output as `Writable` (so
  tests can inject a capture stream) loses `isTTY`, which only exists on `process.stdout`'s
  `WriteStream & { fd: 1 }` union member. Read it via a cast:
  `Boolean((stdout as { isTTY?: boolean }).isTTY)` — still respect `--no-color` + `NO_COLOR`.
- **In-process CLI tests: inject `{stdout, stderr, cwd}`, never spawn**. `main(argv, opts?)`
  defaults to `process.*`/`process.cwd()`; tests capture with
  `class Capture extends Writable { chunks: string[] = []; _write(c,_e,cb){ this.chunks.push(c.toString()); cb(); } get text(){ return this.chunks.join(''); } }`.
  Works with `node:test` in-process — no subprocess, no shell-quoting or temp-path-with-spaces
  hazards on Windows. Fixtures in `os.tmpdir()` via `mkdtemp`, cleaned with try/finally `rm`.
- **Entry-guard invocation gotcha**: the
  `resolve(process.argv[1]).toLowerCase() === fileURLToPath(import.meta.url).toLowerCase()` boot
  guard only fires when the CLI path resolves against the CURRENT cwd. Running
  `node dist/src/cli.js --env /other/dir/.env` from a different directory with a RELATIVE cli path
  silently no-ops (no output, exit 0). For cross-directory demos run from the repo root (relative
  resolves) or pass an ABSOLUTE path to the CLI file.
- **`--fix`-style mutation flags**: print exactly what will be written BEFORE writing (that IS the
  consent), then RE-VALIDATE after the write and report the honest post-fix state — appended empty
  values can surface new errors (a typed key filled with `KEY=` is a mismatch for non-string hints).

Full session detail (Open-Meteo endpoints/params, WMO code table, JSON fixtures, demo evidence):
`references/weather-cli-open-meteo.md`.
Full env-validator session detail (.env/.env.example parsing rules, type-hint regex table,
exit-code mapping, --fix consent design, 37-test structure, live demo evidence):
`references/envguard-env-validator-cli.md`.
Full link-checker session detail (linkrot: markdown/HTML extraction regexes, code-fence masking,
classify rules, HEAD→GET fallback + timeout mapping, concurrency pool, DOMException-not-Error,
31-test structure, demo-with-in-process-server traps):
`references/linkrot-link-checker-cli.md`.

## Port/process inspection CLIs (netstat / tasklist / lsof)

Building a "what is using port N?" style tool (parse OS socket output, map PID → process name, offer a kill): see `references/windows-process-port-inspection.md` for the full recipe. Key pitfalls (all verified 2026-08-01):
- Windows `netstat -ano` rows: proto = first token, PID = trailing token, UDP lines have NO state column, IPv6 is bracketed (`[::]:135`, `[fe80::1%12]:546`), foreign `*:*` is normal. ALWAYS split output on `/\r?\n/` — CRLF is present on Windows.
- `tasklist /FO CSV /NH` fields are double-quoted and names/memory values contain commas — needs a quote-aware CSV state machine (with `""` escape), never `split(',')`.
- `lsof -i` (non-Windows fallback): the COMMAND column can contain spaces ("Code Helper"), so `tokens[1]` is NOT the PID. Get the PID as the first purely-numeric token; command = everything before it.
- Kill-gate safety: gate `--kill` behind `--force` as a PURE decision function (`pid !== undefined && force`); unit-test the gate, never perform an actual kill in tests. Node spawn passes single-slash args (`spawnSync('taskkill', ['/F', '/PID', pid])`) — `//F //PID` double-slashes are ONLY a git-bash shell-escape need.
- Integration test that proves the parser against real output: `server.listen(0)` → read port → `spawnSync('netstat', ['-ano'])` → parse → assert row's PID === `process.pid`; guard non-Windows CI with `t.skip()`.

## Zero-dependency file-watcher CLI (fs.watch / fs.watchFile, "run on change")

Building a nodemon-style watcher (`watch-run`-class tool: watch a tree, re-run a shell command on change, zero runtime deps). Full build notes (watcher strategy, debounce design, gitignore matcher, demo evidence): `references/zero-dep-watcher-cli.md`. Key pitfalls, verified 2026-08-01 on Windows:

- **`tool <command> [flags]` arg parsing**: when the spec lets flags legally follow the command, "everything after the command belongs to the command" BREAKS it — flags after the command must still be consumed. Parse known flags anywhere (before or after the command), fold unknown flags/extra tokens into the command, and reserve `--` as the escape hatch for command flags that collide with tool flags (`tool --watch lib -- tsc -w` → watchDir=lib, command='tsc -w'). Keep the parser PURE (no `process.exit` — return a discriminated union incl. help/version/error kinds) so unit tests hit every branch; `main()` owns exit codes.
- **Testable ESM CLI entry guard**: run `main()` only when `path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)` (lowercase both on win32) — the module imports cleanly for unit tests AND runs directly via `node dist/src/cli.js`.
- **Spawned commands via `shell: true` are not portable if the command string contains quotes**: single quotes are consumed by `sh -c`, double quotes nest badly under `cmd /s /c`, and Windows temp paths contain SPACES that split into multiple cmd tokens (a `--watch C:\Users\PREM KUMAR\...` inside a joined command silently becomes two tokens). For tests/demos spawning `node -e <script>` through a shell, keep the script QUOTE-FREE and pass paths/data via env vars: `require(process.env.WR_FS).writeFileSync(process.env.WR_MARKER,'done')` with `WR_FS='fs'` — identical behavior on cmd.exe and Linux CI sh. Never embed a `mkdtemp` result (spaces under %TEMP%) inside a joined command; consume it as a parsed option or env var. A `;` inside the -e script is a JS separator on Windows but splits commands under sh (second half fails as command-not-found) — fine if you only need output + non-zero exit, but design for it.
- **`assert.equal` does not narrow TS unions** — narrow with `if (r.ok)` first, or tsc reports TS2339 on the other variant's missing property.
- **Bounded live demo for long-running watchers**: background shells have no tty (`bash: no job control in this shell`, output uncaptured). Instead run a FOREGROUND `timeout --signal=TERM N node dist/src/cli.js "<cmd>" --watch <dir>` whose command writes into the watched dir — run #1 triggers run #2, demonstrating initial run + change→re-run + debounce merging in seconds. Note: on Windows an external SIGTERM terminates the process WITHOUT running JS handlers (no shutdown message printed); console SIGINT is catchable — keep handlers for both.

## Shipping to CI (cross-platform verification)

Verified 2026-08-01 on watch-run + json-tail (both passed locally, both failed Linux CI first).

- **POSIX quote-join is the fix for `shell: true` portability, not avoidance**: when the CLI itself must
  re-join `process.argv` command parts for `spawn(cmd, {shell:true})`, a bare `parts.join(' ')` works on
  Windows cmd.exe but Linux `/bin/sh` dies with `Syntax error: "(" unexpected` (any `(`, `;`, quotes in
  the args). Canonical fix — platform-aware joiner, testable on Windows:
  ```ts
  export function buildCommand(parts: string[], platform: NodeJS.Platform = process.platform): string {
    if (platform === 'win32') return parts.join(' ');           // cmd.exe: keep proven bare join
    return parts.map((a) => (/^[A-Za-z0-9_@%+=:,./-]+$/.test(a) ? a : `'${a.replace(/'/g, `'\\''`)}'`)).join(' ');
  }
  ```
  The `platform` param lets a unit test assert the POSIX branch deterministically on a Windows dev box;
  the win32 branch stays byte-identical to the previously-working behavior. CI re-run is the real proof.
- **Stale `dist/` can mask a missing test source**: if the npm test script lists
  `dist/test/x.test.js` but `test/x.test.ts` was never written, `npm test` can still report green
  locally (node --test on Windows tolerates the missing file arg), while CI hard-fails immediately:
  `Could not find '<abs>/dist/test/x.test.js'`. Before pushing, diff the test script's file list
  against `ls dist/test/`. When the missing file is a CLI test, write REAL integration tests against
  the injectable `main(argv, {stdout, stderr, signal})` (see in-process test pattern above) — no
  spawn, no shell quoting, works on both platforms.
- **Verify Actions CI after every push** (a green local build is not a shipped project):
  ```bash
  TOKEN=$(python -c "import json;print(json.load(open('C:/one/.acc2_token.json'))['access_token'])")
  curl -s -H "Authorization: token $TOKEN" "https://api.github.com/repos/<owner>/<repo>/actions/runs?per_page=1" \
    | python -c "import json,sys;d=json.load(sys.stdin);r=d.get('workflow_runs',[{}])[0];print(r.get('status'),r.get('conclusion'))"
  ```
  On failure: `RUN_ID` from the runs call → `.../actions/runs/$RUN_ID/jobs` → `JOB_ID` →
  `.../actions/jobs/$JOB_ID/logs` (save to `C:/one/_log.txt`, NEVER MSYS `/tmp` — curl can't resolve
  it), then `grep -nE "not ok|# fail|error"`. 429s on the token API → sleep 60–90s and re-poll; the
  first run may still be `in_progress` right after a push.

## Verification (after "done")

Before claiming done:
1. `node src/index.js --version` — prints version.
2. `node src/index.js --help` — prints usage.
3. `node -e "require('./package.json')"` — valid package.json.
4. Config builder logic — unit-test the output shape matches expectations.
5. Premium template (if any) — `JSON.parse(fs.readFileSync('pro/...'))` — valid JSON.

## npm publish checklist

- [ ] `package.json`: `name`, `version`, `bin`, `files`, `repository`, `license` all set
- [ ] `npm pack --dry-run` — verify only intended files are shipped
- [ ] README badges point to real npm and GitHub URLs
- [ ] LICENSE file present (MIT recommended)
- [ ] Run `npm test` — green
- [ ] `npm publish` — or `npm publish --access public` for scoped packages
