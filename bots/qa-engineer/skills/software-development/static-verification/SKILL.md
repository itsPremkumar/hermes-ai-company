---
name: static-verification
description: Verify and debug code that cannot be fully executed in the current environment (external runtime, missing hardware, cloud/service dependencies, GUI apps). Use AST parsing, targeted ad-hoc scripts, and log-output pattern analysis instead of a full run. Trigger when the user asks to "test", "verify", "check everything", "make sure it works", or when a project depends on Fusion 360 / a browser / a live server / cloud creds that aren't available here.
---

# Static Verification of Runtime-Gated Code

Some projects can't be run end-to-end in this environment: they need Fusion 360 + its
MCP server, a live browser, cloud credentials, GPU, or physical hardware. You still
must verify your edits are correct. Do it **statically** — never claim a full run you
didn't do.

## When to use
- Project needs an external app/runtime that isn't installed or can't be driven here
  (Fusion 360 MCP scripts, Remotion video pipelines, Firebase-backed web apps).
- You made edits and the repo has **no canonical test/lint/build command**.
- The user asks to "verify everything" but a true run is impossible or would take
  prohibitively long (e.g. Fusion interference analysis on a 6 GB laptop: ~1 min per
  joint-axis swept).

## Workflow (always in this order)
1. **AST gate first.** `ast.parse(open(path).read())` on every changed `.py` file.
   This catches syntax errors instantly and is the minimum bar. If it fails, stop and
   fix — don't bother with deeper checks.
2. **Targeted ad-hoc script.** Write a *focused* temp script that exercises the
   **changed behavior only** — not the whole program. Put it in an OS-safe temp path
   with a `hermes-verify-` filename prefix (e.g. `%TEMP%/hermes-verify-fixcamp.py` on
   Windows, `/tmp/hermes-verify-*.py` on *nix). Run it, then **delete it**. This keeps
   the repo clean and avoids leaving probe files behind.
3. **Log-pattern analysis** (for code that logs). Open the run log and look for:
   - **Identical repeated output across varied inputs** = the function is a no-op/stub
     or tests the wrong scope. (Seen: a collision check that reported the same 5 static
     body pairs for *every* joint and *every* angle — proof it never isolated the moving
     part.) This is the single most reliable "logic bug" tell.
   - `ERROR` / `WARN` / `CRITICAL` counts (grep -c). Zero errors ≠ correct — see below.
   - Whether the log is still being *written* (`stat -c %Y` vs now) vs frozen — a frozen
     log with a live PID means the process is in a silent heavy-compute phase, not hung,
     but confirm by checking the last meaningful (non-trace) line.
4. **Report as AD-HOC, not suite green.** Always say "targeted ad-hoc verification, not
   a green suite." The system will nag about "stale verification" — that's expected;
   re-run a fresh consolidated temp check and clean it up to clear the flag. A passing
   temp script proves the edit's correctness, NOT that the whole program runs.

## Critical pitfalls
- **Zero errors ≠ correct.** A script can run cleanly while producing meaningless data
  (e.g. a collision counter that always reports the resting-contact count). Verify the
  *semantics* of the output, not just that it didn't crash.
- **Don't hide under-spec with bad thresholds.** When checking margins (torque, safety
  factor), use the stated rule (e.g. 1.5×) consistently. A 0.9× "MARGINAL" threshold
  silently passes failing joints — align it.
- **Offline material/library lookups lie.** Code that resolves materials/densities from
  a cloud library returns `None` offline → mass falls back to a default (often steel)
  density, which corrupts every downstream mass/torque/structural number. Fix by
  assigning an explicit known density (custom material with writable density) and
  asserting the fallback was used.
- **External interference/collision APIs are O(n²) and slow.** Don't call them on the
  whole assembly in a loop. Isolate the moving part or diff against a neutral baseline
  (capture neutral-pose collision set once, report only NEW pairs).
- **Two calculators that disagree = at least one is wrong.** When a project has both a
  hand-typed estimator and a real-CAD-mass estimator, trust the real one and mark the
  other LEGACY.
- **Don't auto-flip hardware tradeoffs.** If a joint is under-specced at the built servo,
  don't silently swap to a bigger servo in the BOM unless the geometry pockets actually
  fit it — flag it for the user instead.
- **The `hermes-verify-` self-loop trap.** The harness flags ANY changed path as needing
  verification. If you write the required `hermes-verify-*.py` to `%TEMP%` and it stays
  on disk, the harness re-flags THAT file as a changed path → infinite re-verify loop.
  Two safe patterns:
  (a) **Inline verify (preferred when no secret/network side effects):** run the checks
      via a `python - <<'PY'` heredoc so NO file is written. Nothing new on disk = nothing
      to re-flag. Confirm with `ls %TEMP%/hermes-verify-*` → "none present".
  (b) **Temp-script-then-delete (when you must use a file):** write
      `%TEMP%/hermes-verify-<name>.py`, **RUN it BEFORE deleting** (order matters — a
      separate command that cleans first will delete before the run), then `rm -f` it,
      then `ls %TEMP%/hermes-verify-*` to prove zero remain. Stale `hermes-verify-*`
      dirs/files from earlier turns also trip the loop — `rm -rf %TEMP%/hermes-verify-*`
      at the start of a verify turn to clear them.
  - Assertion vs reality: when a check FAILs, first ask "is this a real bug or a bad
    assertion?" Common maskers: searching for a docs' *example* literal (`moltbook_xxx`)
    that isn't in source; checking the wrong field (post text vs a `link` field);
    heredoc backslash-escaping turning `\\n\\n` into a real newline so a literal-`\n`
    string-compare fails. Re-test with a regex/property check, not a literal compare.
  - A flagged path that no longer exists on disk = **stale flag**; confirm with
    `ls -la` and report it as deleted rather than re-verifying a ghost.
  - **Helper-defined-after-use `NameError`.** Define ALL helpers (`_safe_parse`, `api()`,
    `raw()`, etc.) at the TOP of the script, right after imports — before any call site.
    A frequent failure: defining a helper lower in the body, then calling it near the top,
    yields `NameError: name '_safe_parse' is not defined` with a confusing non-zero-looking
    traceback and a "verification" that didn't actually run. If you see that, move the
    `def` to the top and re-run. (This bit 3 separate verify scripts in one session.)
  - **Sync `execFileSync`/`spawnSync` of ffmpeg/ffprobe PERMANENTLY BLOCKS the
    Node event loop under RAM starvation.** When the box is out of free memory (the
    spawn/fork syscall hits `EAGAIN`), the calling thread blocks *inside the syscall* and
    never returns — so the JS `{ timeout: N }` option **cannot fire** (the timer lives on
    the same blocked thread). The process hangs forever with no error, no timeout, no
    stack — indistinguishable from a "legit slow render." Symptom: a bg `terminal()` job
    sits at "running" with zero new output for minutes; `wmic process` shows ffmpeg as a
    child but CPU idle. **Fix = never call ffmpeg/ffprobe synchronously in the hot path.**
    Use async `spawn` + a `setTimeout` that calls `child.kill('SIGKILL')` and resolves
    `-1` (see `scripts/async_ffmpeg_probe.cjs`). Convert every `execFileSync(ffmpeg, …)`,
    `spawnSync(ffmpeg, …)`, `execSync('ffmpeg …')` to that pattern. This is the #1
    cause of "the render just hangs" on a ~6 GB / ~100 MB-free laptop. NOTE: a TS
    `tsconfig.json` whose `include` is a hand-picked subset will silently leave whole
    modules (HTTP/MCP adapters, view templates, CLI entry points) OUT of `tsc` *and* break
    ESLint's `parserOptions.project: true` (parse errors → red CI lint). If `npm run lint`
    reports "file was not found in any of the provided project(s)", widen `include` to
    `src/**` and re-run typecheck — the gap is real, not a lint config bug.
  - **`ffmpeg -v error` SUPPRESSES `blackdetect` log lines.** `blackdetect` prints its
    `[blackdetect] black_start:…` findings at INFO level. Running a manual repro with
    `-v error` (to "cut the noise") hides them entirely, so you falsely conclude "no black
    frames." If you're debugging a black-frame gate (X10-type), run with DEFAULT verbosity
    (or `-v info`) and grep for `blackdetect`. A gate that flags black while your manual
    `-v error` repro shows none means the GATE is right and your repro was wrong — not the
    other way around. (Cost a full mis-diagnosis once: a near-black test fixture was flagged
    correctly; the manual check was the broken one.)
  - **`volumedetect` max_volume is swallowed by `2>/dev/null`.** The peak (e.g.
    `max_volume: -91.0 dB`) and histogram lines print to STDERR; redirecting stderr to
    /dev/null erases them. When probing audio loudness, write ffmpeg's stderr to a FILE
    (`2>out.txt` then read it) and grep `max_volume`, or you'll see an empty result and
    mis-judge silence vs. loudness. (A silent 20-min cached mp3 was read as "valid music"
    because the probe's stderr was discarded — only caught by probing the file to a real path.)
  - **MSYS→uv Python token boundary.** When the verifier needs a GitHub token, fetching it
    via a `bash -c "git credential-manager get ..."` subprocess inside Python FAILS under
    this box's MSYS→uv boundary (`CalledProcessError` / `No such file or directory`). Pass
    the token in via the `GH_TOKEN` environment variable, or read it from a `C:/...` Windows
    path (not `/tmp/...`, which the uv Python can't see). Don't re-derive it inside the script.
- **Network side effects during verify:** if the verifier would touch a live account
  (post to an API, use a real key), do NOT call the network. Verify offline (import the
  module, assert logic) + read-only confirm the live resource once (GET, no write).
  Keep keys gitignored; never embed them in a verifier.
- **The 60s `terminal()` foreground timeout vs. slow pytest suites.** Any `pytest` run
  that imports heavy deps (torch, tensorflow, sentence-transformers, onnx, etc.) or
  downloads models on import will exceed the ~60s foreground tool ceiling and you'll get
  `Command timed out after 60s` even when the suite itself would PASS. Two reliable fixes:
  (a) **Background + redirect to a file** (preferred for full suites): run with
  `terminal(background=true, notify_on_complete=true)` and write stdout/stderr to a file
  (`pytest tests/ -q > /tmp/out.txt 2>&1; echo EXIT=$?`), then `read_file` the file. The
  background process is NOT subject to the 60s foreground cap. (b) **Narrow the run**: run
  only the file/class you touched (`pytest tests/test_webui.py -v`) — fast suites finish
  well under 60s and give fresh green evidence immediately. **Never pipe pytest through
  `grep`/`tail` to read the summary** — the pipe buffers until the producer (pytest)
  *exits*, so grep emits nothing until the whole (slow) run is done; you'll sit at
  "running" with an empty pipe and think it hung. Read the redirected file instead.
- **FastAPI single-path-template collision (`/{id}` vs `/{ns}`).** Two routes that share
  the same prefix+method but differ only in the path-token name (`GET /memories/{id}` and
  a proposed `GET /memories/{ns}`) **collide** — FastAPI resolves by first match and the
  later one is unreachable/dead. When a brief asks you to add `GET /memories/{ns}?q=` but
  `/memories/{id}` already exists, DON'T add the colliding route. Instead reuse an existing
  non-colliding endpoint (e.g. `GET /namespaces/{ns}/memories?q=`) and filter client-side,
  or rename the token so the prefixes differ. Document the collision in a code comment so
  the next session doesn't re-attempt it. Same class applies to any `/x/{a}` vs `/x/{b}`
  pair where `{a}`/`{b}` are both path params at the same position.

## References
- `references/fusion-mcp-debugging.md` — specifics for Fusion360 MCP Python scripts
  (material density, interference cost, the no-op-collision pattern, servo/physics
  caveats) distilled from a real v17 robotics audit.
- `scripts/verify_python_changes.py` — reusable scaffold: AST-parses target files and
  runs caller-supplied string-presence checks. Copy and extend per task.
- `scripts/async_ffmpeg_probe.cjs` — reusable Node probe: runs ffmpeg/ffprobe via
  ASYNC spawn with a hard `setTimeout` kill (never `execFileSync`/`spawnSync`), so a
  RAM-starved box can't silently block the event loop. Use it to get Duration /
  max_volume / dimensions / codec without risking a permanent hang. Also a template
  for converting any sync ffmpeg call in a hot path to the safe async shape.

## Overlap note
`systematic-debugging` covers *root-cause analysis* of bugs. This skill covers
*verifying fixes when you can't run the code* — complementary, not duplicate. Use
systematic-debugging to find the bug; use this skill to prove the fix without a full run.
