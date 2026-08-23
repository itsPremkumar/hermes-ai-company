---
name: openclaw-setup
description: Install, configure, and run OpenClaw (openclaw/openclaw) — a self-hosted multi-channel AI assistant gateway — on a Windows dev box, wired to a FREE OpenRouter model (nvidia/nemotron-3-super-120b-a12b:free; tencent/hy3:free is DEAD since 2026-07). Covers the exact config schema (env.OPENROUTER_API_KEY + agents.defaults.model.primary), the reasoning-model token gotcha, where the existing OpenRouter key lives, and the low-RAM boot-failure debugging path (wmic vs /proc, timeout-bounded commands). Use when the user says "install openclaw", "set up the openclaw agent", "run openclaw with my openrouter key", or references openclaw.ai.
---

# OpenClaw setup (Windows, self-hosted, free OpenRouter model)

OpenClaw (`openclaw/openclaw`, npm package `openclaw`, MIT) is a personal AI
assistant gateway you run on your own machine. It speaks to channels
(Telegram/WhatsApp/Discord/Slack/…) and routes agent requests to an LLM. It is
OpenAI-compatible and has **OpenRouter built in**, so a free model
(`tencent/hy3:free`) works with zero paid keys.

This skill was written for a host that already had `openclaw@2026.6.11` installed
globally via npm. Adjust paths if your install differs.

## Environment facts (verified on the build host)

- Node **≥ 22.19 required**. The host had v22.23.1 — fine.
- Global install: `npm install -g openclaw@latest` (or pnpm/bun). Binary:
  `openclaw` → `openclaw.mjs`.
- Config lives at `C:\Users\PREM KUMAR\.openclaw\openclaw.json`
  (`$HOME/.openclaw/openclaw.json` in git-bash).
- Gateway default port **18789**, `bind: loopback`, `auth.mode: token`.
- Telegram channel may already be wired (`channels.telegram`, `dmPolicy: pairing`).
- The user's OpenRouter key is NOT in the shell env — it lives ONLY in
  `C:\Users\PREM KUMAR\.openclaw\openclaw.json` under `env.OPENROUTER_API_KEY`
  (verified 2026-07-31: the old `C:\one\omniroute\start-omniroute.bat` file and
  `~/.openrouter_key` no longer exist).

## Procedure (fresh install on this host)

1. **Install** (if missing):
   ```bash
   npm install -g openclaw@latest
   openclaw --version   # prints e.g. "OpenClaw 2026.6.11 (e085fa1)"
   ```
   Note: `openclaw --version` is light and always safe.
   `openclaw gateway --help` also runs cleanly on this box (verified:
   returns in <25s, EXIT=0) — it is NOT the "heavy/hangs" command
   the old note claimed; do use it to list flags. The real silent-stall
   symptom is the **startup-migration lease** (Pitfall 5), not --help.
   If the gateway won't bind, read its LOG FILE, not your stdout redirect —
   see Pitfall 8.

2. **Extract the OpenRouter key WITHOUT printing it** (see Pitfalls — never echo
   the secret):
   ```bash
   KEY=$(grep -oP 'OPENROUTER_API_KEY=\K\S+' /c/one/omniroute/start-omniroute.bat | head -1)
   printf '%s' "$KEY" > ~/.openrouter_key
   chmod 600 ~/.openrouter_key
   ```
   Then patch the config with `scripts/setup-openclaw.sh`
   (reads `~/.openrouter_key`, writes `env.OPENROUTER_API_KEY` + sets the primary
   model). Or hand-edit per the schema below.

3. **Config schema** — add/merge into `openclaw.json`:
   ```json5
   {
     "env": { "OPENROUTER_API_KEY": "sk-or-..." },
     "agents": {
       "defaults": {
         "model": { "primary": "openrouter/nvidia/nemotron-3-super-120b-a12b:free" },
         "models": { "openrouter/nvidia/nemotron-3-super-120b-a12b:free": {} }   // allowlist entry
       }
     }
     }
     ```
     - Model ref is `openrouter/<provider>/<model>` — e.g.
     `openrouter/nvidia/nemotron-3-super-120b-a12b:free`. Onboarding default is `openrouter/auto`.
     - ⚠️ 2026-07-31 verified: `tencent/hy3:free` is DEAD (OpenRouter returns 404 — free tier pulled);
     `gpt-oss-20b:free` answers chat but REJECTS OpenClaw's tool schema (HTTP 422);
     **`nemotron-3-super-120b-a12b:free` works with tools** — use it.
     - Switch later without editing JSON: `openclaw models set openrouter/nvidia/nemotron-3-super-120b-a12b:free`.
   - OpenRouter is OpenAI-compatible, so OpenClaw talks to it over the same
     `openai-completions`-style transport.

4. **Boot the gateway** (see Pitfalls for the low-RAM trap):
   ```bash
   openclaw gateway --port 18789
   ```
   Onboarding (`openclaw onboard --install-daemon`) installs a launchd/systemd
   user service so it stays running — preferred if you want 24/7.

5. **Verify the model is reachable** (lightweight, no gateway needed):
   ```bash
   curl -sS -X POST "https://openrouter.ai/api/v1/chat/completions" \
     -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
     -d '{"model":"tencent/hy3:free","messages":[{"role":"user","content":"Reply with exactly: OK"}],"max_tokens":200}' \
     | python -c "import sys,json;print(json.load(sys.stdin)['choices'][0]['message']['content'])"
   ```
   Expect `OK`. This call also confirms the key is valid independent of OpenClaw.

## ⚠️ Reasoning-model gotcha (important)

`tencent/hy3:free` (the original free pick — **dead since 2026-07-31, OpenRouter
returns 404**) was a **reasoning model**. The lesson generalizes: at low
`max_tokens` (e.g. 20) reasoning models spend all tokens on internal "thinking"
(`reasoning` field) and return **empty `content`** (`finish_reason: length`).
Give any reasoning model `max_tokens: ~200` so it actually emits a reply. The
OpenRouter API resolves the alias to `tencent/hy3-20260706:free`
(provider: Novita). Within OpenClaw this matters for agent tasks: very short
tool-call expectations may come back empty.

## Pitfalls

### 1. NEVER echo the OpenRouter key
The key is a 73-char `sk-or-...` secret. Extract it to a file with `grep -oP`,
store in `~/.openrouter_key`, and pass it to curl via `$(cat ~/.openrouter_key)`.
Verify success by printing only `len` + 4-char prefix, never the full value.

### 2. Low-RAM boot failure (this host is the poster child)
The box had **~70–150 MB free RAM of 6 GB** with 565 processes (a Paperclip/
Omniroute cluster eats ~100 MB each). Symptoms:
- `openclaw gateway` node.exe **is alive** (via `wmic`) but never binds the port —
  stuck loading plugins.
- `openclaw --help` times out (60s).
- Shell gets `fork: Resource temporarily unavailable` (EAGAIN).

**Debugging path that works on Windows git-bash:**
- Confirm the process is real with **`wmic.exe process where "name='node.exe'"
  get ProcessId,CommandLine`** — `/proc/<pid>/cmdline` does NOT see Windows-native
  node.exe from git-bash, and `tasklist | grep node` is unreliable for cmdlines.
- Check RAM: `grep MemFree /proc/meminfo`. < 200 MB free ⇒ expect hangs.
- **Bound every command with `timeout`** (e.g. `timeout 8 curl ...`) so a hung
  call fails fast instead of eating the 60s tool budget.
- **Avoid deep recursive greps** (`grep -r` over `$HOME`) — they trigger the
  EAGAIN fork failures. Target specific files/dirs instead.
- **Free RAM first**: kill stale `openclaw gateway` procs (`taskkill /PID <n> /F`)
  and any unneeded Paperclip/Omniroute node processes before restarting.
- After freeing RAM, a fresh `openclaw gateway` boots and binds within ~30s.

### 3. Port already in use by a stale gateway
If `netstat -ano | grep :18789` shows LISTENING but it's an OLD config (wrong
model), kill that PID and relaunch — the new process can't bind a taken port and
will silently hang.

### 4. Config not re-read until restart
OpenClaw loads `openclaw.json` at gateway startup. Editing the file does nothing
until you restart the gateway.

### 5. ⚠️ Orphaned `startup-migrations` lease — THE most common stuck-start cause on upgrade
OpenClaw 2026.7.x writes a lease row into its state SQLite DB
(`$HOME/.openclaw/state/openclaw.sqlite`, table `state_leases`,
`scope='startup-migrations'`) at gateway boot and clears it on clean exit.
**If you `taskkill` the gateway (or it crashes mid-boot) the row is NOT removed**,
so every later launch fails instantly with:
```
OpenClaw startup migrations are already running for this state directory;
retry after the other gateway finishes or after <UTC timestamp>
```
or, once past that, with:
```
OpenClaw startup migrations did not complete cleanly; refusing to report the gateway ready.
- Failed to install missing configured plugin "codex" from @openclaw/codex: ...
```
This is a **DB-level lock, not a process lock** — waiting does NOT help unless the
owning process is alive AND renewing it (it isn't, it's dead). The lease also has a
time-based expiry (~10 min ahead). Naive "wait it out" loops keep failing because a
competing launch re-writes a fresh timestamp each time.

**Fix — delete the orphaned row directly (safe ONLY when no gateway is running):**
```bash
# 1. kill EVERY gateway node process first (see Pitfall 6 for the respawn trap)
for p in $(wmic.exe process where "name='node.exe'" get ProcessId,CommandLine 2>/dev/null \
            | tr -d '\r' | grep -i gateway | grep -oE ' [0-9]+ *$'); do
  taskkill /PID $(echo $p | tr -d ' ') /F; done
# 2. clear the lease row
cd "$HOME" && python - <<'PYEOF'
import sqlite3, os
p = os.path.expanduser(r"~/.openclaw/state/openclaw.sqlite")
c = sqlite3.connect(p); cur = c.cursor()
cur.execute("DELETE FROM state_leases WHERE scope='startup-migrations'")
c.commit()
cur.execute("SELECT count(*) FROM state_leases"); print("leases left:", cur.fetchone()[0])
c.close()
PYEOF
# 3. launch exactly ONE gateway (no competing launches), then poll port 18789
```
A ready-to-run version lives in `scripts/clear-startup-lease.py`. After clearing,
launch the gateway by hand (see Pitfall 6) and verify the port.

### 6. ⚠️ Windows scheduled task silently respawns the gateway
`openclaw gateway install` creates a Windows task **"OpenClaw Gateway"** (and
"OpenClaw Companion") that may auto-restart the gateway. If you `taskkill` the
gateway but the task is enabled, it respawns a NEW gateway that re-acquires the
migration lease — your kills appear to "not work" and the lease clock keeps
resetting. **Disable both tasks before any lease surgery or clean relaunch:**
```bash
schtasks /change /tn "OpenClaw Gateway" /disable
schtasks /change /tn "OpenClaw Companion" /disable
```
After the gateway is confirmed running and healthy, re-enable the Gateway task
with `schtasks /change /tn "OpenClaw Gateway" /enable` if you want 24/7 boot.
Until then launch directly: `openclaw gateway --port 18789` (background, long-lived).

### 7. `codex` plugin install fails with an integrity mismatch
On this host `openclaw update repair` / `doctor --fix` fail to install the
configured `@openclaw/codex` plugin:
```
Failed to install missing configured plugin "codex" from @openclaw/codex:
npm install resolved @openclaw/codex with integrity unknown, expected
sha512-OCEVg4R3yb5vXZiwchJp02o+XmWklnF9EdcXgQUGfvVELwIwJvvvQYJ0tp0M2zJLuA4zDSYPtFVDGviKRrKd2w==
```
This is an **upstream npm registry / checksum drift**, not a local config error,
and it blocks the startup migration from completing cleanly. The gateway does NOT
need `codex` (we route via OpenRouter `nvidia/nemotron-3-super-120b-a12b:free` +
Telegram). Fix:
```bash
# in openclaw.json, set the entry to disabled (or remove it from plugins.entries)
"codex": { "enabled": false }
```
Then relaunch. If the migration still chokes, fully delete the `codex` block from
`plugins.entries`. `doctor --fix` will also report it disabled and "continue
without it" — that is the expected good outcome.

### 7b. ⚠️ ROOT CAUSE (verified 2026-07-31): openai provider refs force the codex runtime
The REAL trigger that keeps the startup migration stuck on codex is **any
`openai` provider/model reference in openclaw.json**. In
`dist/harness-runtimes-*.js`, `openAIProviderUsesCodexRuntimeByDefault()` returns
true when the provider is `openai` AND it has no custom base URL — so the agent
harness runtime defaults to `codex`, and startup migration insists on installing
`@openclaw/codex` (which fails npm integrity on this box). Symptoms persist even
after: uninstalling codex (`openclaw plugins uninstall codex --force`), deleting
stale `openclaw-generation` project dirs under `~/.openclaw/npm/projects/` that
depend on `@openclaw/codex`, rebuilding the registry
(`openclaw plugins registry --refresh`), and clearing the startup-migrations
lease. **FIX (verified working — gateway binds in ~30s):** remove ALL openai refs
from config — `models.providers.openai` block and any `openai/gpt-*` entries in
`agents.defaults.models`. Keep only openrouter refs. Also drop `gpt-*-codex`
model names from the models list. Then: kill gateway node procs, clear lease,
launch ONE gateway detached (see Pitfall 5/6), poll port 18789.
```bash
# verify the trigger is gone BEFORE relaunching:
grep -c '"openai"' "$HOME/.openclaw/openclaw.json"   # expect 0 (or only plugin allowlist)
```

### 8. ⚠️ Background launches write to a TEMP LOG, not your stdout redirect
When you run `openclaw gateway ... > /tmp/oc.log 2>&1` in the
background, the gateway process **does NOT log to that file** — it
stays empty while the process is alive. OpenClaw writes its real log to:
```
C:\Users\<user>\AppData\Local\Temp\openclaw\openclaw-YYYY-MM-DD.log
```
(git-bash path: `/c/Users/<user>/AppData/Local/Temp/openclaw/...`).
When debugging a non-binding gateway, tail THAT file, not your redirect:
```bash
sed 's/[[:cntrl:]]/ /g' "/c/Users/PREM KUMAR/AppData/Local/Temp/openclaw/openclaw-2026-07-14.log" | tail -20
```
The file is JSON-lines; strip control chars before grepping. The gateway
also responds to `openclaw gateway --verbose` in the FOREGROUND (bounded
with `timeout 90 ...`) — that IS captured to stdout and shows the
`[gateway] ready` / `http server listening` line that proves a clean boot.

### 9. ⚠️ Delegating a task to the agent — and its no-file-write limitation
`openclaw agent` runs a turn through OpenClaw's own agent (model per
`agents.defaults.model.primary`). Useful for offloading a reasoning/draft task
or proving the channel bridge works. Gotchas discovered (verified 2026-07-14):
- **Must select a target.** `openclaw agent --message-file X` FAILS with
  `No target session selected. Use --agent <id>, --session-key <key>,
  --session-id <id>, or --to <E.164>`. Pick an existing agent via
  `openclaw agents list` (e.g. `main`) and pass `--agent main`.
- **`--message-file` path is Node-resolved to Windows.** A `/tmp/oc_task.txt`
  becomes `C:\tmp\oc_task.txt` (ENOENT) on this box. Write the task file to a
  plain Windows path (e.g. `C:\one\oc_task.txt`) and pass THAT.
- **The agent has NO file/exec capability.** It will generate code/text and
  reply, but REFUSES to write to disk ("I can't write files in this session —
  no file/exec tool — so I won't fake a confirmation"). So OpenClaw's agent is
  **reasoning/draft-only**: Hermes must do the actual persistence. Proven
  pattern: delegate generation to `openclaw agent`, then write the returned
  artifact with Hermes's `write_file` and verify with `ls`.
- **Media generation is unavailable without a provider key — it says so
  honestly (verified 2026-07-31).** Asked to "generate a sample video" the
  agent replied verbatim: `VIDEO_GEN_UNAVAILABLE — No video generation skill
  or tool is configured in the current environment.` `capability list` shows
  `video.generate` but with NO configured video provider key behind it (the
  config only has openrouter + telegram). Don't fight this: Hermes + the AVS
  pipeline does real video on this box (see avs-ffmpeg-pipeline local-assets
  pattern for a network-free render).

### 10. Verifying capabilities & live channel health
- **Capability catalog (what it can REALLY do):** `openclaw capability list`
  returns canonical ids — `web.search`, `web.fetch` (REAL internet access),
  `image.generate/edit/describe`, `video.generate/describe`, `tts.*`,
  `audio.transcribe`, `embedding.create`, `model.run`. Media gen needs a
  provider key; web + model + tts work with the base config.
- **Live channel health:** `openclaw channels status --probe` reports each
  channel's connected/running state. Verified on this host:
  `Telegram default: enabled, configured, running, connected, transport: polling,
  bot:@prem123aibot, ... works`.
- **Gateway HTTP health probe:** extract `token` from `~/.openclaw/openclaw.json`
  and `curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:18789/` →
  `HTTP 200`. (Background logs go to `%LocalAppData%\Temp\openclaw\...`, see
  Pitfall 8 — NOT your stdout redirect.)

### 13. ⚠️ Gateway dies with the Hermes session — relaunch DETACHED (verified 2026-07-31)
A gateway launched from a Hermes terminal session gets killed when that session
is torn down (orphan recovery kills the process tree), leaving a dead gateway and
an orphaned `startup-migrations` lease. The gateway MUST be launched fully
detached so it outlives the shell:
```bash
powershell -NoProfile -Command "Start-Process -FilePath 'C:\nvm4w\nodejs\node.exe' \
  -ArgumentList 'C:\nvm4w\nodejs\node_modules\openclaw\openclaw.mjs','gateway','--port','18789' \
  -WindowStyle Hidden -WorkingDirectory 'C:\Users\PREM KUMAR'"
# then poll (boot takes ~30-40s after a clean state):
for i in $(seq 1 30); do netstat -ano 2>/dev/null | grep -q ":18789.*LISTENING" && echo UP && break; sleep 10; done
```
Path note: `openclaw` resolves to `C:\nvm4w\nodejs\node_modules\openclaw\openclaw.mjs`
on this host (nvm4w layout, NOT the Roaming npm path).

**Full control battery** — how to PROVE end-to-end control in one pass (all
verified 2026-07-31 on 2026.7.1-2):
1. `openclaw --version` — CLI alive.
2. `openclaw agents list` — agent `main` + model visible.
3. `openclaw capability list` — real capability catalog (`model.run`,
   `image.generate/edit/describe`, `audio.transcribe`, `tts.*`, `web.*`).
4. Gateway HTTP: `TOKEN=$(python -c "import json;print(json.load(open(r'C:\Users\PREM KUMAR\.openclaw\openclaw.json',encoding='utf-8-sig'))['gateway']['auth']['token'])")` then
   `curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" http://127.0.0.1:18789/` → `200`.
5. `openclaw plugins list` — clean plugin set (no codex).
6. `openclaw channels status` — "Gateway reachable" + Telegram running/connected.
7. **Decisive end-to-end test**: write an exact-reply instruction to a
   Windows-path file (e.g. `C:/one/oc_gw_test.txt`) and run
   `openclaw agent --agent main --message-file "C:/one/oc_gw_test.txt"`; grep for
   the verbatim reply. `--message-file` must be a Windows path (`C:/...`), NOT
   `/c/...` — MSYS mangles `/c/...` into `C:\c\...` (ENOENT).

### 12. Publishing an OpenClaw control/usage guide into the company repo
The verified control guide produced this session lives at
`infra/openclaw-control-guide.md` inside `Hermes-Full-Autonomous-Company`
(the "single source of truth" repo; OpenClaw is already listed in its Stack).
Reuse this pattern when documenting OpenClaw setup for the company:
- **Home:** `infra/` (the company README defines it as "deployment, security,
  monitoring notes" — the right place for a control/ops guide).
- **Public-repo sanitization is MANDATORY** (the company repo is public): before
  commit, replace every real identifier with a placeholder — `@<your-bot-handle>`
  (NOT `@prem123aibot`), `/c/Users/<WINDOWS_USER>/...` (NOT the real path),
  generic `<PID>`/`<PEER_PORT>` in the verified-output block, and any real
  task-file path (`C:\path\to\oc_task.txt`). Then run
  `grep -nE "prem123aibot|PREM KUMAR|nvm4w|49464|8780" <file>` and confirm CLEAN.
- **Wire it in:** update the README `infra/` row AND the Stack bullet to point at
  `openclaw-control-guide.md` (two edits, one commit).
- **Push:** the repo uses cached GCM (`git config credential.helper manager`);
  a plain `git push origin master` works with no token echo. Verify on GitHub via
  the API (`contents/infra/openclaw-control-guide.md`) — confirm size + that
  README mentions the guide — before declaring done.
- **Standalone copy:** also push a standalone public repo
  (`itsPremkumar/openclaw-control-guide`) if you want it independently linkable.

### 11. OpenClaw in the money-earning stack (honest mapping)
Mapped against the `money-engine` autonomous-income system. OpenClaw is NOT a
replacement for Hermes (Hermes writes files, runs generators, `git push`es;
OpenClaw's agent cannot persist — see Pitfall 9). Its real, defensible value
is two roles:
1. **Telegram delivery layer** — the connected bot (`@prem123aibot`) can push
   generated promo/newsletter drafts (`content/_promo-drafts.md`,
   `content/_newsletter.md`) to you/a channel so you only approve+forward. This
   fills money-engine's "agent drafts but cannot auto-post" gap honestly.
2. **Phone-controlled front-door** — enable `@openclaw/admin-http-rpc` so a
   Telegram message can trigger Hermes crons; you command the system from your
   phone. The actual build/publish stays with Hermes crons (the 18 pipelines).
**It cannot:** persist files (Pitfall 9), touch `config.json` affiliate IDs,
open paid accounts, do KYC/GST/tax, or run crypto/arbitrage bots (money-engine
rejects these — do NOT build them on OpenClaw either). Full mapping + verified
capability catalog: `references/openclaw-capabilities-money-mapping.md`.

## References / templates / scripts

- `references/openrouter-config.md` — full OpenRouter schema, model-ref rules,
  and the key-extraction + config-patch recipe.
- `references/release-channels-and-video-limits.md` — npm dist-tags per channel
  (latest vs extended-stable, when to switch), and the verified truth that
  OpenClaw cannot generate video without a provider key (use Hermes/ffmpeg).
- `references/windows-low-ram-debugging.md` — the EAGAIN / wmic / timeout
  debugging path in detail, for any heavy Node CLI on this box.
- `references/openclaw-stuck-startup.md` — full anatomy of the stuck-startup
  failures (orphaned lease, scheduled-task respawn, codex integrity), with exact
  commands and the `state_leases` SQLite schema.
- `references/openclaw-log-location.md` — WHERE OpenClaw actually writes its
  log when launched in the background (it is NOT your stdout redirect; it is
  `%LocalAppData%\Temp\openclaw\openclaw-YYYY-MM-DD.log`).
- `scripts/setup-openclaw.sh` — extracts the key (no echo), patches
  `openclaw.json` (env key + primary model + allowlist), verifies without
  printing the secret.
- `scripts/verify-openrouter.sh` — lightweight probe: confirms the key works and
  `tencent/hy3:free` returns non-empty content at max_tokens=200.
- `scripts/clear-startup-lease.py` — deletes the orphaned `startup-migrations`
  lease row; run ONLY when no gateway node.exe is alive.
- `templates/openclaw.openrouter.json` — known-good config fragment to merge into
  `openclaw.json`.
- `references/openclaw-capabilities-money-mapping.md` — verified capability
  catalog (`openclaw capability list`), live channel-health probe recipe, the
  `openclaw agent` delegation walkthrough, and the honest mapping of OpenClaw
  into the money-earning stack (delivery layer + control front-door, what it
  cannot do).
- `references/openclaw-vs-hermes-verified.md` — VERIFIED July 2026 numbers
  (live GitHub stars/licenses/issues for both repos, capability catalog,
  Telegram status) AND the recurring trap that AI-generated comparison docs
  hallucinate Hermes star counts (30k→30k→66k; real 214,750) and OpenClaw's
  license (it's NOASSERTION, NOT MIT). Reuse before trusting any pasted
  "OpenClaw vs Hermes" doc. Pair with the `verify-ai-claims` skill.
