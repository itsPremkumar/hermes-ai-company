---
name: prem-the-dev-project-factory
description: Publish the next unique CLI project for prem-the-dev.
---

# prem-the-dev Project Factory

Build one complete, unique, live-verified TypeScript CLI project and publish it to the `prem-the-dev` GitHub account (2nd account; `itsPremkumar` is account 1 and must stay untouched).

## Trigger
- User asks for a new project for prem-the-dev, or the pipeline roadmap says the next project is due.
- Roadmap file: `C:\one\prem-the-dev-roadmap.md` (statuses: ✅ shipped / 🔨 building / ⏳ queued / 💡 idea). Pick the next ⏳.

## Uniqueness rule (critical)
Every project must be a NEW niche. Existing shipped: gh-repo-health (repo health audit), todoscope (code-debt scanner w/ git blame), latency-watch (endpoint latency monitor), cryptotick (crypto ticker), watch-run (file-watch→run command), weather-cli (live weather), port-sentinel (port→process finder). Never overlap these. Check the roadmap before choosing.

## Recipe (zero runtime deps, TS, node:test, CI)
1. Project dir: `C:\one\<name>`. Files:
   - `package.json`: name `<name>`, v1.0.0, `"type": "module"`, `"bin": {"<name>": "dist/src/cli.js"}`, engines node>=18, scripts `build=tsc`, `test="npm run build && node --test dist/test/<f1>.test.js dist/test/<f2>.test.js ..."` — **explicit file list, NOT a glob** (Windows glob quirk). devDeps typescript ^5.5 + @types/node ^22.
   - `tsconfig.json`: ES2022, NodeNext, rootDir '.', outDir dist, strict, resolveJsonModule.
   - `.gitignore`: node_modules/, dist/, *.log, .DS_Store, coverage/
   - `LICENSE`: MIT Copyright (c) 2026 Premkumar M
   - `.github/workflows/ci.yml`: node [20, 22] matrix, npm ci, npm test.
   - `README.md`: CI badge `https://github.com/prem-the-dev/<name>/actions/workflows/ci.yml/badge.svg`, usage, example output.
   - `src/*.ts` + `test/*.test.ts` (node:test + assert/strict; include at least one REAL integration test against a local `node:http` server on port 0 — never mock the happy path).
2. `npm install` then iterate `npm test` until `# pass` == `# tests`.
3. **Live demo**: run the CLI for real (real API / real filesystem / local server), capture output as proof. "Realtime working" is the account's brand.
4. Commit locally: `git init -b main`; `git config user.name "Premkumar M"`; `git config user.email premkumar995252@gmail.com`; `git add -A; git commit -m "feat: <name> v1.0.0 — <one-line pitch>"`.
5. **Create the GitHub repo via API BEFORE pushing** (forgetting this is a proven mistake — SSH push fails with "repository not found"):
   ```
   TOKEN=$(python -c "import json;print(json.load(open('C:/one/.acc2_token.json'))['access_token'])")
   python -c "import json; open('C:/one/_repo.json','w',encoding='utf-8').write(json.dumps({'name':'<name>','description':'<pitch>','private':False,'has_issues':True,'has_wiki':False}))"
   curl -s -X POST https://api.github.com/user/repos -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" --data @C:/one/_repo.json
   rm -f C:/one/_repo.json
   ```
   (JSON payload FILES for curl `--data @file` — git-bash mangles UTF-8 in inline `-d`.)
6. Push: `git remote add origin git@github-acc2:prem-the-dev/<name>.git && git push -u origin main`.
7. Topics: `curl -s -X PUT https://api.github.com/repos/prem-the-dev/<name>/topics -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" -d '{"names":[...]}'`.
8. **Verify externally**: `curl https://api.github.com/repos/prem-the-dev/<name>/git/trees/main?recursive=1` (count files), then dogfood `node C:/one/gh-repo-health/dist/src/cli.js prem-the-dev/<name>` (expect grade A/B). Update `C:\one\prem-the-dev-roadmap.md` status → ✅. Optionally update profile README (`C:\one\premkumar995252-profile\README.md`) + push it.

## Windows / git-bash pitfalls (all learned the hard way)
- Regexes: in write_file/patch payloads, backslashes get doubled. ALWAYS write regexes as `new RegExp(\`\\b...\\\`, 'i')` template strings with double backslashes — regex LITERALS with backslashes break the TS build. Verify bytes with `od -c` when in doubt.
- `git` subprocess output is CRLF → always split with `/\r?\n/`.
- `node --test` needs explicit file list in the test script (shell globs don't expand on Windows npm).
- Test fixtures referenced via `new URL('../../test/fixtures/x.json', import.meta.url)` + `fileURLToPath` — NOT `.pathname` (yields `/C:/...` → broken on Windows).
- write_file refuses invalid-JSON fixtures — create those with `printf` in terminal.
- Background `node server` processes die instantly in this shell (no job control) — run demo servers inside a single foreground command via `timeout N bash -c '...'`, or use a standalone demo script file in the project dir (delete after).
- `--once`-style network demos against real APIs: watch rate limits (CoinGecko 429s — the tool should retry with backoff).

## Verification before declaring done
- `npm test` output shows `# pass N / # fail 0`.
- `git branch -vv` shows `[origin/main]`.
- Public API returns the repo with a populated tree.
- The live demo output was actually captured (real data, not hand-written).
