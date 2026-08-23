# Zero-dependency file-watcher CLI (watch-run v1.0.0 build notes)

Verified 2026-08-01 building `C:\one\watch-run`: a nodemon-style, zero-runtime-dependency
file watcher for Node >= 18 (`fs.watch` / `fs.watchFile` only), 35/35 tests green
(node:test) on Windows, committed locally. Everything below is a pattern that worked.

## Watcher strategy (createWatcher)

1. **Recursive first**: `fs.watch(root, { recursive: true })` only when the platform
   supports it — keep an explicit whitelist (`process.platform === 'win32' || 'darwin'`).
   Linux recursive support is version-dependent; don't guess.
2. **Per-directory fallback** (Linux, or recursive threw): walk the tree, one `fs.watch`
   per directory. MUST rescan after every debounced batch, or subdirectories created
   after startup are never watched. During rescan, close watchers whose dir vanished.
3. **fs.watchFile polling last resort**: interval ~150ms, fire on
   `cur.mtimeMs !== prev.mtimeMs`. CAVEAT: polling only covers files present at STARTUP —
   files created later are invisible. Tests must pre-create the file before constructing
   the watcher, then rewrite it.
4. **Filter BEFORE the debouncer** (ignore patterns + ext filter applied to each raw
   event), so ignored churn (node_modules) never enters the debounce window at all.
5. **Testability flags**: expose internal `forcePerDir` / `forcePolling` config options so
   tests can exercise every mode on any platform (on Windows the recursive path is taken
   by default). Also inject `log` and `verbose` so the CLI can reuse the watcher's own
   log sink and tests can silence it.
6. Raw fs.watch callback details: `filename` is relative to the watched dir; may be null
   (use the dir itself). `statSync` the target for isDir, tolerating ENOENT (deleted
   mid-flight). Directory events only trigger a run when the ext filter is empty —
   otherwise a mkdir fires but the file creation inside produces its own event.

## Debounce design (pure module, injectable timers)

- Trailing-edge: every `push` clears and reschedules the timer; the accumulated event
  array is delivered in ONE call after `delayMs` of quiet. Multiple saves in 200ms = 1 run.
- Inject `setTimeout`/`clearTimeout` via options → fake-timer unit tests: assert push
  reschedules (previous handle marked cleared, latest handle runs the batch).
- Expose `flush()` (force-fire; used by graceful shutdown + tests), `cancel()`, and
  `pendingCount()`.
- Real-timer tests: delayMs 25–40 with 60–80ms waits are reliable on CI and Windows.

## Extension filter semantics

- Extension comes from the BASENAME (same as `path.extname`): dotfiles like `.env` and
  `.gitignore` have NO extension, and `src/.env` must behave identically to `.env`.
  `lastIndexOf('.')` on the full rel path is wrong — it makes `src/.env` match `['env']`
  while bare `.env` doesn't (dot at index 0).
- Case-insensitive match; empty extension list = everything matches.

## Gitignore-style matcher (no minimatch dependency)

- `*` → `[^/]*`, `?` → `[^/]`, `**/` → `(?:.*/)?`, bare `**` → `.*`.
- Pattern with NO slash → match ANY single segment (so `node_modules` ignores the whole
  subtree at any depth; `*.log` hits basenames at any depth).
- Pattern with a slash or leading `/` → root-anchored: `new RegExp(\`^${rx}(?:/.*)?$\`)`
  matches the pattern itself or anything under it.
- Trailing `/` = directory pattern; leading `!` = re-include, last match wins
  (`['*.log', '!important.log']`).
- Escape regex specials char-by-char via a `Set` lookup returning `BACKSLASH + c`
  (`String.fromCharCode(92)`), and build final regexes with template literals — avoids
  backslash regex literals that write_file JSON transport mangles (see SKILL.md regex pitfall).

## Windows cmd.exe / sh -c command portability (shell: true)

- Spawn the user command with `shell: true` on all platforms (the CLI gets a single joined
  string; splitting argv yourself is fragile).
- For test/demo commands spawned through that shell: `require('fs').writeFileSync("C:\\Users\\PREM KUMAR\\...")`
  fails on Windows (nested double quotes under `cmd /s /c`) or Linux (single quotes eaten
  by sh). The pattern that works on BOTH:
  `script = 'require(process.env.WR_FS).writeFileSync(process.env.WR_MARKER,process.env.WR_DATA)'`
  with `env = { ...process.env, WR_FS: 'fs', WR_MARKER: marker, WR_DATA: 'done' }`.
  Zero quotes, zero spaces in the script → cmd and sh both pass it as one token.
- Keep `assert.equal(r.status, 0)` + `fs.existsSync(marker)` as the real end-to-end proof
  of a spawned command; exit-code propagation test: `node -e process.exit(3)` → status 3.
- Debugging note: a test that fails in the FULL `node --test` multi-file run but passes in
  isolation is usually a REAL interaction, not runner flakiness — here, the old arg parser
  joined `--watch C:\Users\PREM KUMAR\...` (space!) into the cmd.exe command string and
  the path silently split into two tokens. Fix = consume the path as a parsed option.

## Watcher-mode main loop

- Initial run at startup (nodemon behavior) + re-run per debounced batch; if the child is
  still running, set a `pending` flag and run after its exit (no overlapping runs, no lost
  changes).
- Non-zero exit → report `FAILED (exit code N) — keeping watch.` and keep watching.
- Ctrl+C (SIGINT) → kill child, close watcher, exit. On Windows, external SIGTERM
  terminates without running handlers; console SIGINT IS catchable — register both.

## Bounded live demo (no background shell needed)

Background shells have no tty and don't capture child output. Instead:
`timeout --signal=TERM 7 node dist/src/cli.js "node -e require('fs').writeFileSync(process.env.DEMO_WATCH_FILE,'x')" --watch <dir> --debounce 300`
where `DEMO_WATCH_FILE` lives INSIDE the watched dir — run #1 writes it, the change
triggers run #2, etc. Observed: 17 runs in 7s, each burst of 2–3 raw Windows fs.watch
events merged into one run ("change detected (3 events)"), timestamped banners + exit
codes throughout. `timeout` returns 124 when it had to signal; that's expected.
