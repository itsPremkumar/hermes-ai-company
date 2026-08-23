# 14 — Testing Standards

Every project MUST meet these minimums before `kanban complete` is allowed.

## 1. Required test types

| Type | When required | Tool |
|------|---------------|------|
| Unit tests | Any non-trivial logic (API routes, utils, parsers) | `node:test` / `pytest` |
| Integration tests | Any external API call (Google, GitHub, LLM) | `node:test` / `pytest` |
| CLI smoke test | Every CLI command — run with `--help` and one real invocation | shell script |
| Self-test | Every CLI tool MUST have a `--self-test` subcommand that exits 0 | built-in |

## 2. Minimum coverage

- **API routes**: 80% line coverage
- **Utility functions**: 90% line coverage
- **CLI commands**: 100% of commands must have at least one happy-path test
- **Error paths**: Every `error()` / `throw` must have a matching test

## 3. Framework by language

| Language | Framework | Config file |
|----------|-----------|-------------|
| TypeScript / Node.js | `node:test` (built-in) + `tsx` for execution | `tsconfig.json` |
| Python | `pytest` + `pytest-cov` | `pyproject.toml` |

## 4. When tests must pass

1. **Before `kanban complete`** — assignee runs the project's own test suite
2. **Before `kanban complete`** — assignee runs `python qa_harness.py <project_dir>`
3. **Both must exit 0** for the card to be marked `complete`

## 5. Test file layout

```
project/
├── src/
│   ├── commands/
│   │   └── create.ts
│   └── utils/
│       └── parser.ts
├── tests/
│   ├── unit/
│   │   ├── commands/
│   │   │   └── create.test.ts
│   │   └── utils/
│   │       └── parser.test.ts
│   ├── integration/
│   │   └── google-calendar.test.ts
│   └── smoke/
│       └── cli.test.sh
└── package.json
```

## 6. Running tests

```bash
# TypeScript / Node.js
npm test                          # runs node --test
npm run test:coverage             # runs with coverage

# Python
pytest tests/ -v                  # all tests
pytest tests/ --cov=src --cov-report=term-missing  # with coverage
```

## 7. QA gate

`qa_harness.py` runs automatically when a card enters `request-review`. It checks:
- All `.py` files compile
- `pytest` passes if tests exist
- Every `--self-test` subcommand exits 0
- No hardcoded secrets
- README/SKILL presence

A non-zero exit sends the card back with `request-changes`.
