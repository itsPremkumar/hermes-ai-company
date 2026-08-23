# Template subagent prompt — one cluster of failing tests (wave of 3)

Paste this as the `goal` for a `delegate_task` leaf agent. Replace <> tokens.
Keep assertions VERBATIM from the failing test output so the agent fixes at
cause, not by guessing.

---
Repo: <C:\path\to\repo> (git branch main). You are ONE of 3 parallel bug-fix
subagents. Focus ONLY on <module/area>. node:test (`node --import tsx --test
<file>`). TypeScript strict mode. Do NOT touch other modules. Do NOT push to git.

GOAL: Fix the failing tests in <test-file> by correcting root-cause bugs in the
source. Tests assert specific behavior; make the source match WITHOUT deleting/
modifying unrelated working code (if you must change a signature, keep a shim).

FAILING TESTS + assertions (verbatim from `npm test` output):
<test 1 name>:
  assert.equal(<actual>, <expected>);   // <one-line what it checks>
<test 2 name>: ...

SOURCE: <file.ts> (function <name> at line <N>).

WORKFLOW:
- Read source + test fully first. Root-cause each failure (file:line).
- Fix at cause. Add/extend a test ONLY if a case is missing — do NOT weaken
  assertions.
- Run: cd <repo> && node --import tsx --test <test-file>  => all target tests pass.
- Run: npm run typecheck  => exit 0.
- Commit locally: git add <files> && git commit -m '<type>(<area>): <what>'.
  DO NOT push.
- Report: each fix with file:line root cause + the test command output proving pass.

CONSTRAINTS: zero-cost (no paid deps), backward-compat (shim if signature
changes), Node 22 + TS strict mode.
---

After ALL waves return: YOU re-run `npm test` + `npm run typecheck` and confirm
the numbers. A subagent's "all pass" is a self-report — verify it.
