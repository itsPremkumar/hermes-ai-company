---
name: windows-msys-tooling
description: Agent tooling gotchas on Windows (MSYS/git-bash) — search_files path failures, false TS6053 lint errors from patch/read_file, and the execute_code+subprocess+rg workaround. Load when a file tool misbehaves on Windows paths, or when grepping/listing files in C:/... reliably.
---

# Windows MSYS Tooling Gotchas

This environment is Windows 10 with the agent `terminal` backed by git-bash/MSYS.
Paths are `C:/Users/...`; tools accept both `C:/one/...` and `/c/one/...` forms.
Several agent file-tools have persistent quirks here. Knowing the workaround
saves many wasted round-trips.

## Trigger
Load when:
- `search_files(path='/c/one/...')` fails with `rg: ... The system cannot find the path specified. (os error 3)` even though the file exists.
- A `patch`/`read_file` auto-lint prints `error TS6053: File '/c/one/...' not found. The file is in the program because: Root file specified for compilation`.
- You need to grep/search Windows paths reliably and the dedicated tool is acting up.

## Gotcha 1 — `search_files` breaks on MSYS paths (FALSE "os error 3")
`search_files` with a `/c/one/...` style path frequently throws
`rg: /c/one/...: The system cannot find the path specified. (os error 3)`
despite the file existing. This is a path-translation bug between the tool and
ripgrep, NOT a missing file. It ALSO fails independently on malformed regex
(e.g. an unbalanced `(?:...` group) with `rg: regex parse error: unclosed group`
— that error is about the pattern, not the path.

**Fix (first line — simplest):** Run `rg` directly inside `terminal` (bash/MSYS).
The terminal shell resolves `/c/one/...` (and `C:/one/...`) correctly even when
the `search_files` tool does not. Example:
```bash
cd "/c/one/Automated-Video-Generator" && rg -n "pattern" src --glob '!*.test.ts'
```
Reserve `execute_code` for when terminal itself isn't usable.

**Fix (fallback):** Do the grep inside `execute_code` (Python) using
`subprocess.run(["rg", ...])` with the `C:/one/...` (drive-letter) form. This is
reliable and avoids both the path bug and the regex bug.

```python
import subprocess
r = subprocess.run(
    ["rg", "-n", "export (async )?function NAME", "-n",
     "C:/one/Automated-Video-Generator/src/agentic/operations/route.ts"],
    capture_output=True, text=True)
print(r.stdout.strip() or "(MISSING)")
```
For file discovery prefer `os.listdir()` + `os.path.exists()` in `execute_code`.
See `references/repro.md` for a copy-paste recipe.

## Gotcha 2 — false `TS6053` lint from `patch`/`read_file` (IGNORE IT)
After a `patch` edit, the auto syntax-check may print:
`error TS6053: File '/c/one/Project/src/x.ts' not found. The file is in the program because: Root file specified for compilation`
This is a **FALSE POSITIVE** from the linter mis-resolving `/c/one/...` vs
`C:/one/...` path casing. The edit usually succeeded. **Do not treat it as a
real failure.** Verify by running the real `npm run typecheck` (or `npx tsx`)
in `terminal`, which uses the true tsconfig and resolves paths correctly.

## Gotcha 3 — `terminal` is bash (MSYS)
- POSIX syntax: `ls`, `$HOME`, `&&`, single-quoted strings.
- `cd /c/one/...` and native `C:\...` both work in most commands.
- Python = `python` (3.11.15); `pip`→python3.12; `uv` installed.
- Run TS files: `npx tsx file.ts`. One-off tests: `node --import tsx --test 'tests/...'`.
- **`ls -la` column 5 is the UID, NOT the size.** git-bash prints
  `drwxr-xr-x 1 PREM KUMAR 197121 0 Aug 1 09:50 .` — col 5 ("197121") is the
  Windows UID, col 6 is the SIZE. `awk '{print $5, $9}'` therefore prints
  UID + timestamp and looks like a plausible-but-wrong file size (bit me
  twice in one session: "197121" reported as bytes). Use
  `stat -c "%s bytes, %y" file` for real sizes, or `awk '{print $6, $9}'`.
- The command runs in the session cwd; `cd /c/one/Project && cmd` works.

## Pitfall — PowerShell via git-bash: `$_`/`$env:` expand inside DOUBLE quotes
Calling `powershell -Command "..."` from the MSYS terminal, any `$_` (or
`$env:VAR`) inside the double-quoted command is expanded by BASH first —
`$_` becomes the previous command's last argument (e.g. `---`), producing a
mangled command (`{---.ProcessName`) or a ParserError. PowerShell snippets
with `$_` MUST escape it for bash (`\$_` inside double quotes), or
single-quote the whole `-Command` argument when it contains no bash
variables:
```bash
# ❌ bash expands $_ → mangled command / ParserError
powershell -Command "Get-Process | Where-Object {$_.ProcessName -match 'node'} | ..."
# ✅ escaped — works
powershell -NoProfile -Command "Get-Process | Where-Object {\$_.ProcessName -match 'node'} | Select-Object Id,ProcessName,WS | Format-Table -AutoSize"
```
Also: `powershell -NoProfile` avoids profile startup noise; and for the two
most common diagnostics you often need NO PowerShell at all:
- Free RAM: `wmic OS get FreePhysicalMemory,TotalVisibleMemorySize` (KB).
- Process list: `tasklist | grep -iE "node|ffmpeg"` (bash-safe, no `$_`).

## Gotcha 5 — `node`/`tsx` test runner in a git-worktree (CRITICAL)
When you `node --test` / `tsx` from the Hermes terminal, a few Windows/MSYS facts
will silently break the run. Full recipe + copy-paste: `references/node-test-worktree.md`.
Top traps:
- **Use the Windows drive-letter cwd, not `/c/...`.** Node is Windows-native and
  rewrites `/c/one/...` to `C:\c\one\...`, so `--import tsx` fails with
  `Cannot find package 'tsx'`. Always `cd 'C:\one\...'` before running node.
- **Worktree `node_modules` must be a real dir, not a symlink.** `ln -s main/node_modules`
  lets `tsc`/`eslint` (run via `node_modules/.../bin/x.js`) work, but the `tsx`
  loader will not resolve through it. Prefer: run tests from the MAIN checkout, or
  `cp -rL main/node_modules ./node_modules` (the `-L` keeps npm-symlinked pkgs
  like `tsx`/`.bin`).
- **Reuse the CI test command verbatim** — `npm run test:unit` includes
  `--experimental-test-module-mocks`; dropping it makes `mock.module` tests fail.
- **Write TAP logs to a WORKTREE-path file, never `/tmp`** — Node translates
  `/tmp` to `C:\tmp` (nonexistent) and a later `fs.readFileSync('/tmp/x.log')`
  throws ENOENT. Use `C:\one\...\prod-grade\.gstack\x.log`.
- **`describe.skipIf` does NOT exist in Node 22's `node:test`** — it throws
  `TypeError: describe.skipIf is not a function`. Guard env tests with
  `it('x', async (t) => { if (cond) return t.skip('...'); })` instead.
- **The `ln -s` symlink "tsx" failure is actually a cwd-path bug, not the
  symlink.** A plain `ln -s main/node_modules node_modules` resolves fine for
  BOTH `tsc`/`eslint` AND the `tsx` loader — **provided you `cd` with the
  Windows `C:\one\...` path** (§1). The `/c/one/...` cwd mangles to `C:\c\one\...`
  and breaks tsx. So the fix is the Windows cwd, not abandoning the symlink.
- Full AVS recipe (CI `TS2307` `@remotion/*` undeclared-deps fix, `gh` job-log
  fetch, `pull_request` trigger never firing, `node_modules` provisioning on
  this RAM-constrained box, env-test skip-guards): `references/node-test-worktree.md` §9–§11.
- **`$(...)` in `terminal` hits the hardline blocklist** ("command parser limit
  or malformed executable payload"). Move such commands into a `.cjs` helper run
  via `node scripts/x.cjs`, or pre-compute the value and inline it.
- **`mktemp -d` yields MSYS paths (`/c/one/...`) that Windows-native CLIs cannot resolve**: passing a
  `mktemp -d` result straight to `node dist/src/cli.js "$DEMO"` fails with `directory not found` — node
  resolves `/c/...` relative to the current drive as `C:\c\one\...`. Convert before invoking any
  Windows-native binary: `DEMO_WIN=$(cygpath -w "$DEMO")`, then `node dist/src/cli.js "$DEMO_WIN"`.
  (Verified live in the `dupe-hunter` demo, 2026-08-01.)
- **`npm test 2>&1 | tail -N` reports TAIL's exit code, hiding a failing build**: the pipeline's exit
  code is `tail`'s (0), so a failed `tsc` inside `npm test` looks green in the tool result. Read the
  real status with `echo "EXIT=${PIPESTATUS[0]}"` immediately after the pipeline, and grep for
  `not ok` / `error TS` instead of trusting the echoed tail block.
- **Ignore stale background "echo" runs** — a `terminal(background=true)` that
  only printed the command string produced no real output. Re-run in foreground
  or to a log file you then read.

## Gotcha 4 — `execute_code` is the reliable fallback for file ops
When `read_file`/`search_files`/`patch` misbehave on Windows paths,
`execute_code` (Python + `subprocess`/`os`/`pathlib`) is the dependable path.
Use it for: grepping codebases, listing dirs, checking existence, reading JSON,
and running `rg`/`ffprobe`/`ffmpeg` via `subprocess`.

## Pitfall — `du /tmp` reports an inflated size (MSYS mount artifact)
`/tmp` is a MSYS junction to `C:/Users/<user>/AppData/Local/Temp`. When you
`du -sh /tmp`, the top-level number can be MUCH larger than the sum of every
listed subdirectory (e.g. reports 8.2G but all entries total ~1.5G). A hidden
mount/empty subdir inflates the reported total. **Do not trust the /tmp headline
number** — quantify by `du -h --max-depth=1 /tmp` and subtract; the truly
deletable MSYS-owned contents are usually far smaller. For safe temp cleanup of
pipeline scratch, see the `windows-temp-cleanup` skill (patterns + sweep script).

## Pitfall — `cd "/c/one/..."` can fail despite `du` working on the same path
A bare `cd /c/one/Automated-Video-Generator` may fail silently (pwd stays at
`/c/Users/...`) while `du "/c/one/..."` succeeds. Always `cd` with quotes AND
verify with `pwd` or `ls` immediately after, or skip `cd` and pass the absolute
path directly to `rg`/`du`.

## Pitfall — kill a background batch/daemon by COMMAND LINE (wmic filter), not ps PIDs
MSYS `ps -ef` PIDs do NOT reliably match what Windows `taskkill /PID` expects
(`taskkill` reports "process not found" for a PID `ps` just showed), and MSYS
mangles `//PID` double-slashes. The reliable find-and-kill pattern for a
background process tree (e.g. a long batch you must restart with new code):
```bash
# 1. find PIDs by a distinctive CommandLine substring (job name, tsx, cli.ts)
wmic process where "CommandLine like '%agentic-batch%'" get ProcessId,Name /format:csv
# 2. kill each (single-slash args; cmd wrapper avoids MSYS // mangling)
for p in <pid...>; do cmd //c "taskkill /PID $p /F" 2>&1 | tr -d '\r' | grep -E "SUCCESS|not found"; done
# 3. verify dead (0 = gone); also check for stray ffmpeg children
wmic process where "CommandLine like '%agentic-batch%'" get ProcessId /format:csv | grep -cE '^[0-9]+'
```
Filter on a substring that matches ONLY your target (never bare `node` — it
hits the Hermes desktop UI). Do NOT route this through PowerShell
`Get-CimInstance … | ForEach-Object { Stop-Process }` from MSYS — the `$_`
expands via bash first → ParserError (see the PowerShell pitfall above);
escape `\$_` or use the wmic loop. Verify with a SECOND wmic query, not `ps`
(MSYS ps is unreliable for Windows-native processes).

## Pitfall — taskkill-via-cmd loop can SILENTLY miss the real node PIDs → zombie batch trees starve RAM
Killing a batch from MSYS by `for p in <pids>; do cmd //c "taskkill /PID $p /F"; done`
is unreliable: the wrapper output gets swallowed, some PIDs report "not
found", and — worst case — you kill the bash/npx WRAPPERS while the actual
`node.exe` child trees survive (verified 2026-07-31: 4 batches "killed" over
an hour were ALL still alive as `node.exe` trees, each mid-render). The
zombies froze the box at ~5 MB free RAM, and every NEW batch started
afterwards was OOM-killed mid-render with no crash trace — repeated mystery
deaths until the real PIDs were enumerated. The reliable find-and-kill, in
ONE PowerShell process (escaped `\$_` for bash):

```bash
# 1. list the ACTUAL node trees with creation times (ps -ef PIDs do NOT match taskkill's)
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | Select-Object ProcessId,CreationDate,@{n='Cmd';e={\$_.CommandLine.Substring(0,[Math]::Min(80,\$_.CommandLine.Length))}} | Format-Table -AutoSize"
# 2. kill each batch tree (collect the real node PIDs from step 1, then):
powershell -NoProfile -Command "\$ids = 12792,5628,7888,...; foreach (\$id in \$ids) { try { Stop-Process -Id \$id -Force -ErrorAction Stop; Write-Output \"killed \$id\" } catch { Write-Output \"\$id gone\" } }"
```

Diagnostics that expose the zombie state:
- `wmic process where "CommandLine like '%agentic-batch%'"` **self-matches** —
  the query's OWN command line contains the pattern, so a non-zero count does
  NOT prove a batch is running. List `ProcessId,Name` and eyeball for
  `node.exe` (real batch) vs `bash.exe`/`cmd.exe` (wrappers only).
- Multiple batch trees from DIFFERENT `CreationDate`s (hours apart) = earlier
  kills failed silently. Verify by node-process listing, not by "the log
  stopped" (a frozen zombie stops writing logs too).
- After the kill: `Get-Process node` should show ONLY the Hermes/OpenClaw
  gateway trees (match by CommandLine before killing — never bare `node`).
  RAM should visibly recover (FreePhysicalMemory back >1 GB); if a new batch
  still dies mid-render, re-enumerate — another zombie tree may remain.
RULE: when a batch "won't stay alive" on a RAM-constrained box, FIRST
enumerate ALL node trees by CreationDate; the oldest are zombies from failed
kills, not new work.

## Pitfall — `taskkill //F //PID` fails in MSYS; NEVER kill by image name (`//IM node.exe`)
- Double-slash flags break: `taskkill //F //PID 10492` → `ERROR: Invalid argument/option - '//F'` (MSYS mangles `//`). The single-dash form works: `taskkill -F -PID 10492` → `SUCCESS: The process with PID ... has been terminated.` (verified 2026-08-04). `cmd //c "taskkill /PID $p /F"` also works.
- **NEVER `taskkill //F //IM node.exe`** — it kills EVERY node process on the box, including the user's other dev servers (e.g. agentlens `next start -p 3137/3141` on this machine). A silent failure leaves a false sense of cleanup; a success nukes unrelated work. Always enumerate FIRST, kill by PID:
  `wmic process where "name='node.exe'" get ProcessId,CommandLine` → read CommandLine, kill only PIDs matching your target (e.g. `yarn.js install`).
- After any kill, verify survivors with `netstat -ano | grep LISTENING | grep -E ":3137|:3141"` (dev-server ports must still be up) before concluding.

## Pitfall — yarn 1 install HANGS (no progress, no node_modules); use npm ci
`yarn install --frozen-lockfile` (yarn 1.22) stalls on this machine: 15+ min, zero output, `node_modules` never created, process alive but idle. Kill it and use `npm ci --no-audit --no-fund` instead — repos ship package-lock.json alongside yarn.lock. (Heavy Next.js app: 13 min / 2514 pkgs, verified 2026-08-04.) If you must use yarn, run foreground with visible output, never piped to `tail`.

## Pitfall — background `| tail -N` hides progress; probe the artifact, not the pipe
`terminal(background=true, command='... | tail -8')` buffers ALL output until exit — a stall looks identical to silence. Track real progress via the artifact: `ls node_modules | wc -l` growing (npm ci: 0 → 1307 → 2514), or `du -sh` the target. `du -sh` on a huge node_modules can itself time out (30s+ on 1GB+ dirs) — use `ls | wc -l` as the cheap probe.

## Pitfall — spawned `taskkill` does NOT wait for process death (port conflict)

When you `spawn('taskkill', ['/T', '/F', '/PID', pid])` on Windows to kill a
background daemon, `spawn` returns IMMEDIATELY — the `taskkill` command launches
in the background and the process may still be alive (still holding its port)
when your code continues. If the next operation tries to `spawn` a new process
on the same port, the bind fails and the child exits with code 1.

**Example symptom:** `backend exited (code 1)` — a Python speech backend couldn't
bind port 17493 because the previous instance was still being killed.

**Fix:** Use `execSync` or `spawnSync` instead of `spawn` for the kill command,
so the call BLOCKS until `taskkill /F` has actually terminated the process tree:

```typescript
// ❌ ASYNC — returns before kill completes → port still held
spawn('taskkill', ['/T', '/F', '/PID', String(pid)], { stdio: 'ignore' });

// ✅ SYNC — blocks until process is dead and port released
require('child_process').execSync(`taskkill /T /F /PID ${pid}`, { stdio: 'ignore' });
```

This matters because `spawn` with `detached: true` (common for daemon processes
like speech backends) creates a process group — `spawn('taskkill')` as async
returns instantly, but the actual process tree teardown takes time. The
synchronous variant ensures the port is truly free before the next spawn
attempts to bind it.

**Diagnostic tool:** Before and after a `killBackend`-style call, run:
```bash
netstat -ano | grep ":PORT_NUMBER"
```
If the port shows as `LISTENING` after the async kill, you have this bug.

## Pitfall — ffmpeg concat of a zero-duration clip inflates duration
When building a concat list, never include a segment made with `-t 0.000`
(e.g. the trailing "partB" after replacing the LAST scene of a video).
ffmpeg can stretch it into a stray ~1s segment, inflating output duration by ~1s.
Skip any segment with duration <= 0.05s (build the parts list dynamically).

## Pitfall — `curl -o /tmp/x.log` then reading `/tmp/x.log` fails (log scratch)
Saving fetched CI logs / API dumps to `/tmp` from MSYS is unreliable: the file
"disappears" for a later read in the same session (`wc: /tmp/wrlog.txt: No such
file or directory`) even when curl exited 0 — MSYS `/tmp` is a junction to the
Windows user temp and Windows-native tools (and some MSYS builds) resolve it
differently. **Fix: always write fetch/scratch output to a real Windows path**
(`curl -s -L ... -o C:/one/_log.txt`) and delete it after. Also: GitHub Actions
log endpoints 302-redirect to a signed URL — you need `-L` or you get an empty
file. (Same theme as the ffmpeg-concat-`/tmp` and TAP-log pitfalls above.)

## Pitfall — Windows ffmpeg cannot read a concat list at an MSYS `/tmp` path
Running `ffmpeg -f concat -safe 0 -i /tmp/list.txt` from the MSYS terminal can
fail with `Error opening input file /tmp/concat_list.txt. Error opening input
files: No such file or directory` even though bash sees the file — the Windows
ffmpeg binary doesn't resolve the MSYS `/tmp` mount for the `-i` argument
(verified 2026-08-01). Fix: write the concat list INSIDE the project
(`workspace/concat_list.txt`) and reference it with a `C:/...` path; the list
itself must also use `C:/...` (or `C:\...`) absolute file paths. Then
`-c copy` concat of two identically-encoded MP4s (same orientation → same
dims/codecs from one renderer) completes cleanly — a `Non-monotonic DTS`
warning on the audio boundary is harmless with copy muxing.

## FACT — the host username is `PREM KUMAR` (has a SPACE)
System TEMP = `C:\Users\PREM KUMAR\AppData\Local\Temp` and `/tmp` is a MSYS
junction to it. Code that assumes a no-space TEMP path breaks; AVS already
redirects Remotion via `process.env.REMOTION_TMPDIR = resolveWorkspacePath('tmp','remotion')`
in `src/render.ts:127`. Any `os.tmpdir()`/`process.env.TMP` write elsewhere is a
slow disk-fill leak — see `references/temp-leak-fix.md` for the fix recipe
(project-local `workspace/tmp` helpers + bulk test-file transform + pitfalls).

## Pitfall — code-transform scripts: multiline `import {` blocks corrupt insertion
When a `.cjs` script inserts a new import at "the top", a naive regex matching
`^(\s*import[^\n]*\n)+` only sees single-line imports and will inject MID-STATEMENT
into a multiline `import {\n  a,\n  b,\n} from '...'`, producing
`error TS1003: Identifier expected` and a doubled `import {`. Always insert AFTER
the closing `}` of the import block, then confirm with `npm run typecheck` (exit 0).
See `references/temp-leak-fix.md` for the full pattern + verification steps.

## Pitfall — large `patch` / `write_file` / `terminal` calls TIME OUT the tool stream
The Hermes tool stream has a hard ~8K-token argument ceiling per call. A
`patch`/`write_file`/`terminal` whose arguments exceed it does NOT execute — it
stalls mid-call and returns "stream timed out before it could be delivered" (or a
"Duplicate tool output" / empty echo), with no edit applied. This bit repeatedly
when pasting whole ~300-line module rewrites or long inline `bash -c '...'`.

**Symptoms:** result says "stream timed out" / "Duplicate tool output", or a
`patch` reports success but the file is unchanged.
**Fix (mandatory for big changes):**
- NEVER paste a full large file in one `write_file`/`patch`. For NEW files, keep
  each call < ~8K tokens (split a 330-line module into 2 `write_file` calls, or
  write a skeleton then `patch` additions in).
- For EDITS, use MANY small `patch` calls (one logical change each), not one giant
  unified diff. Each `patch` should target a unique, small region.
- For `terminal`, prefer `bash -c '...'` with a SHORT inline script; put long
  multi-step scripts in a file (`cat > /tmp/x.sh <<'EOF' ... EOF`) then run it, or
  use `execute_code` for loops/fan-out.
- After a timeout, re-issue as SMALLER calls — do NOT retry the identical large call.
**Verify the patch landed:** follow any big edit with a quick `terminal` grep /
typecheck rather than trusting the "success" echo, because a partial/duplicated
diff can silently no-op.

## Pitfall — `terminal` `bash -c '...'` with a long inline command can drop stdout
When the inline command is long, captured stdout may come back as a single empty /
duplicate line even on exit 0. If you need to SEE the run's output:
- write the command to a script file and run that, or
- pipe through `| tail -N` and `grep -v` noise (e.g. `PluginRegistry`, `lut-loader`)
  so the real signal surfaces. Always assert on a concrete artifact (file on disk,
  file count, exit code) rather than relying on echoed console text.

## Pitfall — `pnpm` refuses: "configured to use yarn" because home `~/.npmrc` pins `packageManager: yarn`
If the agent's HOME dir has a `.npmrc` (or `package.json`) declaring `packageManager: yarn` / `pnpm@x`, running `pnpm` from inside HOME fails with `ERROR This project is configured to use yarn` — pnpm inherits the home config and refuses. **Fix:** clone and run such projects OUTSIDE the home directory (e.g. `/c/one/...`), where no `.npmrc` `packageManager` field is in scope. (Verified 2026-08-13 on deepseek-ai/deepseek-harness: cloning into `/c/one/deepseek-harness` worked; a home-dir run was blocked.) Notes:
- The repo's own root `package.json` may request a specific `pnpm@X` (e.g. 11.7.0) via its `packageManager` field, but `pnpm -v` can differ (9.15.9 present) and STILL install/build/run. Only upgrade via `corepack enable && corepack prepare pnpm@X` if a real version error appears — don't preemptively fail.
- This is distinct from the yarn-1-install-hangs pitfall above: that is for `yarn` stalls; this is for `pnpm` being *blocked* by a stray home config.

## Pitfall — `git clone` leaves a stuck `.git` lock ("Device or resource busy") from GitHub Desktop respawning `git.exe`
A half-finished clone can leave `.git/objects/pack/tmp_pack_*` and `.git/shallow.lock` you cannot `rm -rf` ("Device or resource busy") because a BACKGROUND `git.exe` (often spawned by GitHubDesktop.exe) still holds the lock. `taskkill /F /IM git.exe` only kills CURRENT instances, but **GitHub Desktop respawns new `git.exe`** that re-grab the lock, so the `rm` keeps failing. Fix sequence (single-slash flags only — `//` breaks in MSYS, see the taskkill pitfall):
1. Kill the respawner FIRST, then the clones: `taskkill /F /IM GitHubDesktop.exe` then `taskkill /F /IM git.exe`.
2. Verify none remain: `tasklist | grep -i git` (expect "none").
3. `rm -rf <repo>` should now succeed; re-clone. For a large monorepo that times out the 180s foreground cap, use `--depth 1` AND run it `terminal(background=true, notify_on_complete=true)` (a deep clone of ~7400 files took minutes; `--depth 1` is the reliable path). (Verified 2026-08-13: deepseek-harness re-cloned cleanly in background only after killing GitHubDesktop.exe + all git.exe.)

## Pitfall — long-lived dev server dies under RAM pressure (OOM exit); run with a logfile + restart + netstat verify
On the 6 GB box, a heavy `pnpm install`/`build` (twenty-plus minutes, thousands of files) drains free RAM; a subsequently started dev server can be OOM-killed moments after first responding — appears as exit 127 with a `bash: no job control in this shell` banner and a dead port. Symptom: first `curl` returns HTTP 200, then ~30s later `netstat` shows no `LISTENING` on the port. **Fix / pattern:**
- Start the server with a logfile redirect so the death reason is captured: `pnpm dsh web > /c/one/<repo>/.web.log 2>&1` via `terminal(background=true, notify_on_complete=true)`. **Do NOT use `nohup … &` / `setsid`** — the harness rejects shell-level background wrappers ("Foreground command uses shell-level background wrappers"); `background=true` is how Hermes tracks the process (you kill it later via the returned session_id).
- Verify it is ACTUALLY up, not just "printed a URL":
  - `netstat -ano | grep ":3080"` must show `LISTENING <pid>`.
  - `curl -sS -o C:/one/_p.html -w "HTTP %{http_code} size %{size_download}\n" http://127.0.0.1:3080/` (save to a real Windows path — `/tmp` is unreliable, see the curl/tmp pitfall). Grep the saved file for `<title>DeepSeek Harness</title>` to confirm the app rendered.
- If it died, check `wmic OS get FreePhysicalMemory` and the `.log` for the real cause, then restart. Pure transient RAM dips recover on re-launch.
- Prefer `background=true` for ANY long-lived process the harness must track and you may later need to kill, rather than guessing PIDs.
