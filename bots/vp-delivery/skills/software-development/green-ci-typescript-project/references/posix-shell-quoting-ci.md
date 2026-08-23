# POSIX shell-quoting CI failure — real case (watch-run, Aug 2026)

## Symptom
- `npm test` green locally on Windows (35/35), but GitHub Actions CI fails on
  BOTH node 20 and node 22 Linux runners: `# pass 32 / # fail 3`.
- Only the integration tests that spawn real commands failed. The log shows:
  ```
  not ok 9 - cli --once: runs a real command that writes a marker file
  error: |-
    stderr: /bin/sh: 1: Syntax error: "(" unexpected
    2 !== 0
  ```
  Exit code 2 = the shell itself rejected the command line (syntax error),
  NOT the spawned program failing.

## Root cause
The CLI joined parsed argv with spaces and handed it to the shell:
```ts
options.command = commandParts.join(' ');
...
const child = spawn(command, { shell: true, stdio: 'inherit' });
```
The test spawned `node -e "require(process.env.WR_FS).writeFileSync(...)"` as
argv elements. The join produced `node -e require(process.env.WR_FS)…`
— quotes gone, parens bare. Windows cmd.exe tolerates bare parens (passes
locally); POSIX `/bin/sh` rejects them.

## Fix
```ts
export function buildCommand(
  parts: string[],
  platform: NodeJS.Platform = process.platform,
): string {
  if (platform === 'win32') return parts.join(' '); // cmd.exe semantics
  const safe = /^[A-Za-z0-9_@%+=:,./-]+$/;
  return parts
    .map((p) => (safe.test(p) ? p : `'${p.replace(/'/g, `'\\''`)}'`))
    .join(' ');
}
```
- win32 keeps the bare join (matches how users type commands on Windows).
- POSIX single-quotes anything outside the safe set; embedded `'` → `'\''`.
- The `platform` param makes the POSIX path unit-testable on any OS.

## Unit test (asserts exact strings, runs anywhere)
```ts
test('buildCommand: quotes shell metacharacters on POSIX, bare join on win32', () => {
  assert.equal(
    buildCommand(['node', '-e', 'require(process.env.WR_FS).writeFileSync(process.env.WR_MARKER,"x")'], 'linux'),
    `node -e 'require(process.env.WR_FS).writeFileSync(process.env.WR_MARKER,"x")'`,
  );
  assert.equal(buildCommand(['echo', 'hi', '&&', 'ls'], 'linux'), `echo hi '&&' ls`);
  assert.equal(buildCommand(['node', 'dist/src/cli.js', '--once'], 'linux'), 'node dist/src/cli.js --once');
  assert.equal(buildCommand(['sh', '-c', "echo 'a b'"], 'linux'), `sh -c 'echo '\\''a b'\\'''`);
  assert.equal(
    buildCommand(['node', '-e', 'require(process.env.WR_FS)'], 'win32'),
    'node -e require(process.env.WR_FS)',
  );
});
```

## Triage path for GitHub Actions failures (no gh CLI needed)
1. List runs: `curl -s -H "Authorization: token $TOKEN" "https://api.github.com/repos/<o>/<r>/actions/runs?per_page=1"`
   → take `workflow_runs[0].id` + `.status` / `.conclusion`.
2. Jobs: `.../actions/runs/$RUN_ID/jobs` → `jobs[0].id`.
3. Logs: `curl -s -L .../actions/jobs/$JOB_ID/logs -o C:/one/_log.txt` —
   **write to a REAL Windows path, NOT /tmp** (MSYS `/tmp` ≠ Windows temp;
   the file lands where a later `/tmp/...` read can't see it).
4. Grep the log for `not ok`, `# fail`, `# pass`, `Syntax error`, `Error`.

## Also true in this class of bug
- Tests failing identically on BOTH matrix node versions usually means the
  failure is platform/quoting related, not node-version related.
- After the fix: local tests green (36/36 with the new unit test) → push →
  poll `actions/runs` until `completed success` on both versions → then the
  repo-health dogfood shows the true grade (it reads "runs in progress"
  and scores CI 50 until Actions finishes, ~90s after push).
