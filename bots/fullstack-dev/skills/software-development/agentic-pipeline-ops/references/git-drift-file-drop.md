# File-drop, branch-drift, and router-integrity traps (2026-07-18 session)

Concrete recipes for three failure modes hit while extending the
Automated-Video-Generator agentic operations layer. All observed on the
user's Windows/MSYS box with the Hermes file tool + git.

## 1. `write_file` / `patch` silently drops files

Symptom: tool reports "wrote X bytes" / "success" but the file is ABSENT.
No tsc error (it just isn't imported), so you only notice when a later
grep/require/run says `Cannot find module './foo.js'` or `No such file`.

Discipline:
- After every `write_file` / `patch`, immediately run:
  `test -f <path> && echo OK || echo MISSING` (via `terminal`).
- If MISSING, do NOT re-call `write_file` (it drops again). Rewrite
  deterministically with Python through `terminal`:
  ```python
  p = r"C:/one/Automated-Video-Generator/src/agentic/operations/foo.ts"
  open(p, "w", encoding="utf-8").write(content)   # raw string, no template-literal unicode
  ```
  This path PERSISTS. Re-verify with `test -f`.
- Use `python` (not `python3`) on this box — `python3` is not aliased.

## 2. Untracked files scrubbed from the working tree

Symptom: modules you know exist (`silence.ts`, `scene.ts`, ...) vanish;
`require`/`import` fails; `git status` shows nothing because they were
never committed to the current branch.

Recovery:
- Is it committed anywhere? `git ls-files <path>` -> if empty, never
  committed (recreate). If present on another branch, restore:
  `git checkout <branch> -- src/.../foo.ts` (e.g. `feat/new-features`).
- After restoring, the restored version may DIFFER from `main` HEAD.
  Check `git status` / `git diff --stat` — if it shows the file modified
  vs HEAD, decide: keep the restored (feature-branch) version and commit,
  OR `git checkout HEAD -- <file>` to revert to main's version. Do NOT
  leave uncommitted modifications in the tree.
- Verify `git status` is clean before committing.

## 3. Branch-drift: commits land on the wrong branch

Symptom: `git push origin main` prints "Everything up-to-date" but your
commit isn't on `main`; `git status -sb` shows `## feat/agentic-ops`
(not `main`). A prior `git checkout` left HEAD on a stray local branch.

Recovery / verification:
- Always after commits: `git status -sb` + `git rev-parse HEAD` vs
  `git rev-parse origin/main` (or `git rev-parse @{u}`).
- If drifted: `git checkout main && git merge --ff-only <stray-tip> &&
  git push origin main`.
- Never trust "push succeeded" — confirm the remote tip moved
  (`git rev-parse origin/main`).

## 4. Classify-without-execute is a broken router path

Symptom: you add a `route.ts` classify rule (`remove_silence`, etc.)
so `do_task` recognizes it, but `dispatch.ts` has NO matching `case`
and no `import` of the module. The op routes, then hits `default` and
fails — worse than leaving it unclassified.

Discipline:
- Add route rule + dispatch `case` + `import` TOGETHER.
- If you can only do one half, leave the op as a granular MCP tool
  (already tested) and do NOT add the route rule.
- Verify with BOTH the route-classification tests AND a real dispatch
  run before committing.
