# OpenClaw stuck-startup — full anatomy

Symptoms observed on a Windows box after `npm install -g openclaw@latest`
(2026.6.11 → 2026.7.1). The gateway process stays alive but never binds
port 18789, and `--verbose` / log output shows one of:

```
[openclaw] Could not start the CLI.
[openclaw] Reason: OpenClaw startup migrations are already running for this
state directory; retry after the other gateway finishes or after <UTC ts>.
```
or, once past that timestamp:
```
[openclaw] Reason: OpenClaw startup migrations did not complete cleanly;
refusing to report the gateway ready.
- Failed to install missing configured plugin "codex" from @openclaw/codex:
npm install resolved @openclaw/codex with integrity unknown, expected
sha512-OCEVg4R3yb5vXZiwchJp02o+XmWklnF9EdcXgQUGfvVELwIwJvvvQYJ0tp0M2zJLuA4zDSYPtFVDGviKRrKd2w==
```

## Root causes (three distinct traps)

### A. Orphaned migration lease (state DB lock)
OpenClaw 2026.7.x writes a lease into `~/.openclaw/state/openclaw.sqlite`
table `state_leases`, `scope='startup-migrations'`. Cleared on clean exit;
left behind if the gateway is `taskkill`'d or crashes mid-boot.

Schema (verified):
```
state_leases(
  scope TEXT, lease_key TEXT, owner TEXT,
  expires_at INTEGER,        -- ms epoch; ~10 min ahead when written
  heartbeat_at INTEGER,
  payload_json TEXT,         -- e.g. {"version":"2026.7.1"}
  created_at INTEGER, updated_at INTEGER
)
```

The lease is **DB-level**, not process-level. A dead owner never releases it.
Waiting does NOT clear it — a competing `openclaw gateway` launch re-writes a
fresh `expires_at`, so naive wait-loops keep failing.

Fix: kill all gateway node procs, then `DELETE FROM state_leases WHERE
scope='startup-migrations'`. Script: `scripts/clear-startup-lease.py`.

### B. Windows scheduled task respawns the gateway
`openclaw gateway install` created task "OpenClaw Gateway" (+ "OpenClaw
Companion"). If enabled, it restarts the gateway after `taskkill`, spawning a
new process that re-acquires the lease → kills look like they "don't work" and
the clock keeps resetting.

Fix:
```
schtasks /change /tn "OpenClaw Gateway" /disable
schtasks /change /tn "OpenClaw Companion" /disable
```
Re-enable Gateway with `/enable` once the gateway is confirmed healthy, if
24/7 boot is wanted.

### C. `codex` plugin integrity mismatch (upstream)
`@openclaw/codex` fails npm install with `integrity unknown, expected
sha512-...` — an npm registry / checksum drift, NOT a local config bug. It
blocks the startup migration from completing cleanly. The gateway does not need
`codex` (routing is via OpenRouter `tencent/hy3:free` + Telegram).

Fix: in `openclaw.json`, set `"codex": { "enabled": false }` (or remove the
block from `plugins.entries`). `doctor --fix` / `update repair` will then
report codex disabled and "continue without it" — that is the good outcome.

## Verified sequence that worked

1. `schtasks /change /tn "OpenClaw Gateway" /disable` (and Companion)
2. Kill all `node ... gateway` procs (robust WMI loop, see SKILL.md Pitfall 6)
3. `cd "$HOME" && python scripts/clear-startup-lease.py`  → leases left: 0
4. Edit `openclaw.json`: `"codex": { "enabled": false }`
5. Launch once, directly: `openclaw gateway --port 18789` (background)
6. Poll `netstat -ano | grep :18789` for LISTENING; tail the launch log.

## Red herrings ruled out
- Low RAM was NOT the cause this time (RAM was 150–785 MB; process alive but
  not binding, and `--help` ran fine). The lease DB lock was the real blocker.
- Port-in-use by a stale gateway: ruled out — port was free; the process made
  NO outbound connections, so it was stalling internally, not on a network call.
- `openclaw doctor --fix` alone is insufficient — it surfaces the codex failure
  but does not clear the orphaned lease. Both steps are required.
