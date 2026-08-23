# Windows process/port inspection: netstat, tasklist, lsof parsing

Verified 2026-08-01 while building `port-sentinel` (a zero-dep "what is using port 3000?" CLI,
30/30 tests green incl. a real netstat integration test).

## netstat -ano (Windows)

Output rows look like (`Proto  Local Address  Foreign Address  State  PID`):

```
TCP    0.0.0.0:135    0.0.0.0:0    LISTENING    812
UDP    0.0.0.0:5353    *:*    1234
TCP    [::]:135    [::]:0    LISTENING    812
TCP    [fe80::1%12]:546    [::]:0    LISTENING    812
```

- UDP lines have NO state column. IPv6 addresses are bracketed and may carry zone ids (`[fe80::1%12]:546`). Foreign `*:*` is normal. PID can be 0 (System).
- Header line (`Proto  Local Address ...`) and `Active Connections` banner must be skipped.
- ALWAYS split the captured stdout on `/\r?\n/` — Windows emits CRLF and a trailing `\r` silently breaks token matching.

Robust hand-rolled parse — never assume a fixed column count:
1. `trim()` each line; skip empty.
2. `tokens = line.split(/\s+/)`; `proto = tokens[0].toUpperCase()` must match `/^(TCP6?|UDP6?)$/` (this also skips the header).
3. `pid = Number(tokens[tokens.length - 1])` — the PID is always the trailing token; require `Number.isInteger(pid) && pid >= 0`.
4. `body = tokens.slice(1, -1)`; `localAddr = body[0]`; `state = body[last]` only if it matches a known-state list (`LISTENING|ESTABLISHED|TIME_WAIT|CLOSE_WAIT|SYN_SENT|...`), else `null` (UDP).
5. Port: `Number(localAddr.slice(localAddr.lastIndexOf(':') + 1))` — works for `[::]:135`, `[fe80::1%12]:546`, `0.0.0.0:135`; `*:*` yields NaN → 0.

Proto narrowing: `netstat -ano -p tcp` / `-p udp` (spawn args `['-ano', '-p', 'tcp']`).

## tasklist /FO CSV /NH (Windows)

```
"node.exe","15088","Console","1","23,456 K"
```

- Fields are double-quoted; process names AND memory values contain commas (`"my, app.exe"`, `"23,456 K"`) — a naive `split(',')` breaks.
- Use a small quote-aware state machine: toggle `inQuotes` on `"`, treat `""` as an escaped literal quote, split on `,` only outside quotes.
- Field 0 = image name, field 1 = PID. PID 0 = `System Idle Process`. tasklist truncates very long names with a `#` suffix (best effort).
- Missing tasklist (e.g. non-Windows): return empty map, don't crash.

## lsof -i (macOS/Linux fallback)

```
COMMAND    PID   USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
node     1234  alice   21u  IPv4 0x1234    0t0  TCP *:3000 (LISTEN)
```

- **The COMMAND column can contain spaces** ("Code Helper") — whitespace-splitting and reading `tokens[1]` as the PID is WRONG (real bug found by a fixture test: returned `'Helper'`).
- PID = the first purely-numeric token: `line.match(/^(\D+?)\s+(\d+)\s/)`; command name = `m[1].trim()`.
- Socket info lives in the trailing NAME field:
  `/(TCP|UDP)\s+(\S+):(\d+)(?:\s+\((\w+)\))?\s*$/` — the `(LISTEN)` group is optional (UDP lines have none).
- Header line has no digits → naturally skipped by the numeric-PID rule.

## Kill-gate safety pattern (`--kill` requires `--force`)

- Pure decision function: `shouldKill(pid, force) = pid !== undefined && force`. main() prints `Refusing to kill PID X: --kill requires --force.` and exits 1 when the gate fails.
- Unit-test the GATE, never perform an actual kill in tests.
- Node `spawnSync` passes single-slash args: `spawnSync('taskkill', ['/F', '/PID', String(pid)])`. The `//F //PID` double-slash form is ONLY a git-bash/MSYS shell-escape need (to stop path mangling) — never inside Node.
- Non-Windows: `spawnSync('kill', ['-9', String(pid)])`.

## Integration test: real netstat resolves your own server

```ts
const server = createServer((_q, res) => res.end('ok'));
server.listen(0, '127.0.0.1', () => {
  const port = (server.address() as AddressInfo).port;
  const res = spawnSync('netstat', ['-ano'], { encoding: 'utf8' });
  server.close(); // close AFTER netstat ran
  const rows = parseNetstat((res.stdout ?? '').split(/\r?\n/))
    .filter((r) => r.localPort === port && r.proto === 'TCP');
  assert.ok(rows.length >= 1, ...);
  assert.equal(rows[0].pid, process.pid); // the socket owner IS the test process
});
```

- Bind `127.0.0.1` explicitly for a clean IPv4-only row (dual-stack default binds `[::]`).
- Guard non-Windows CI (ubuntu runners have no netstat): `if (process.platform !== 'win32') { t.skip('...'); return; }` — keeps the GitHub Actions matrix green while still exercising the real path locally.
- Return the Promise from the test so node:test waits for the async callback.

## ESM CLI entry guard (so tests can import cli.ts safely)

```ts
const isMain =
  process.argv[1] !== undefined && pathToFileURL(process.argv[1]).href === import.meta.url;
if (isMain) process.exitCode = main(process.argv.slice(2));
```

`node --test` spawns test files as their own entry points, so `argv[1]` is the test file — main() never runs on import. tsc preserves a `#!/usr/bin/env node` shebang when it is the file's first line.

## Project layout for tsconfig `rootDir: "."`

- `src/*.ts` → `dist/src/*.js`, `test/*.test.ts` → `dist/test/*.test.js`. Test imports use relative `.js` extensions (`../src/parser.js`) and resolve into `dist/`.
- package.json: `bin` → `dist/src/cli.js`; test script must list explicit files — `node --test dist/test/` (trailing slash) FAILS on Windows (tries to `require("dist\test")`).
- Demo tip: when starting a demo server via a background bash wrapper, the wrapper may exit while the node child detaches and keeps listening — netstat shows the child's real Windows PID, which differs from the MSYS-side wrapper PID. That's normal; it also gives you a live process to exercise the `--kill --force` path against.
