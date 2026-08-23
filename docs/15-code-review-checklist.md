# 15 — Code Review Checklist

Every PR into `main` MUST be reviewed against this checklist before merge.

## 1. Correctness

- [ ] Does the code do what the PRD/task description says?
- [ ] Are there any logic errors or off-by-one bugs?
- [ ] Are error paths handled (network failure, missing file, invalid input)?
- [ ] Are there any race conditions in concurrent work?

## 2. Performance (6GB RAM box)

- [ ] Does the code load large files into memory all at once? (Should stream.)
- [ ] Are there any unbounded loops or recursion without depth limits?
- [ ] Does the code close file handles / DB connections / browser instances?
- [ ] Will this work within 6GB RAM? (Peak RSS < 1.5GB per worker.)

## 3. Security

- [ ] No hardcoded secrets (API keys, tokens, passwords) — `qa_harness` enforces.
- [ ] No `eval()` or `exec()` on user input.
- [ ] No SQL injection (parameterized queries only).
- [ ] `.env` files are gitignored and never committed.
- [ ] Dependencies are from trusted sources (npm/pypi, not arbitrary URLs).

## 4. Style & Conventions

- [ ] TypeScript: strict mode enabled, no `any` without comment.
- [ ] Python: type hints on public functions.
- [ ] Naming: descriptive, consistent (camelCase for TS, snake_case for Python).
- [ ] File structure follows the project layout in `docs/14-testing-standards.md §5`.
- [ ] No commented-out code blocks (delete or explain with TODO).

## 5. Documentation

- [ ] New CLI commands have `--help` text.
- [ ] New API endpoints have JSDoc/docstring.
- [ ] README updated if user-facing behavior changed.
- [ ] ARCHITECTURE.md updated if system design changed.

## 6. Testing

- [ ] Tests exist for new logic (see `docs/14-testing-standards.md`).
- [ ] Tests pass locally before PR is opened.
- [ ] Coverage did not decrease.

## 7. Merge discipline

- [ ] PR targets `main` branch.
- [ ] PR description explains what and why.
- [ ] No merge conflicts with `main`.
- [ ] `SECURITY-APPROVED` comment from `security-engineer` is present.

## Review verdict

The reviewer MUST conclude with exactly one of:

- `APPROVED` — all checks pass, safe to merge.
- `REQUEST-CHANGES: <specific items>` — fixes required before merge.
