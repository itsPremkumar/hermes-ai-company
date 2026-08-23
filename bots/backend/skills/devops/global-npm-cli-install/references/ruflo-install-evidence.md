# Ruflo install — session evidence (reproducible recipe)

**Repo:** https://github.com/ruvnet/ruflo  (agent meta-harness / "Ruflo" AI orchestration platform)
**Package on npm:** `ruflo`  (publishes bin `ruflo` -> `bin/ruflo.js`)
**Node:** v22.23.1 via nvm4w (engines: node >=20)

## Versions observed (2026-07-18)
- GitHub latest *release tag*: `v3.32.4`
- npm `ruflo@latest`: **3.32.7**  ← this is what `npm install -g ruflo@latest` gives you
- `package.json` in repo `main` said `3.32.2` (stale; ignore repo package.json for "latest")

## Exact command that worked
```bash
# 1. metadata (write to no-space dir — home has a space)
mkdir -p /c/tmp_ruflo && cd /c/tmp_ruflo
curl -sL https://registry.npmjs.org/ruflo/latest -o ruflo_npm.json
python -c "import json;d=json.load(open('ruflo_npm.json'));print(d['version'], d.get('bin'), d.get('engines'))"
# -> 3.32.7 {'ruflo': 'bin/ruflo.js'} {'node': '>=20.0.0'}

# 2. install in BACKGROUND (404 deps, would exceed 300s foreground timeout)
terminal(background=true, notify_on_complete=true,
  command="npm install -g ruflo@latest --no-audit --no-fund 2>&1; echo INSTALL_EXIT=$?")
# poll: process(wait, session_id=proc_..., timeout=60) until "added 404 packages" + "INSTALL_EXIT=0"

# 3. verify
/c/nvm4w/nodejs/ruflo.cmd --version     # -> ruflo v3.32.7
cmd /c "where ruflo && ruflo --version"  # resolves via /c/nvm4w/nodejs symlink
ruflo init --help                        # full subcommand tree
```

## Broken-install signature (first attempt, killed at 300s)
- Symptom: `/c/nvm4w/nodejs/ruflo` + `.cmd` existed, but
  `Error: Cannot find module 'C:\nvm4w\nodejs\node_modules\ruflo\bin\ruflo.js'`
- Cause: extraction interrupted; `node_modules/ruflo/` had only a nested `node_modules/`, no `package.json`, no `bin/`.
- Fix: `rm -rf /c/nvm4w/nodejs/node_modules/ruflo /c/nvm4w/nodejs/ruflo*` then reinstall in background.

## Notes
- nvm4w prefix symlink: `/c/nvm4w/nodejs` -> `C:\Users\PREM KUMAR\AppData\Local\nvm\v22.23.1` (this is where global bins land AND it is on PATH).
- `python3` is missing on this box; use `python` (3.11).
- README fetch: GitHub "contents" API returns base64 in `content`; decode with `base64.b64decode`.
- `ruflo init` subcommands: wizard, check, skills, hooks, upgrade.  Common flags: `--full`, `--no-signup`, `--start-all`, `--with-embeddings`.
