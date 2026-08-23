# Stack architecture & control model (verified, adopted 2026-07-15)

The founder adopted this chain-of-command after comparing Hermes vs Paperclip vs
OpenClaw. It is the canonical operating model for the company — keep it in sync
with `CONSTITUTION.md` (the OS-spec table points here).

## The model: Hermes is 1st boss, Paperclip is 2nd boss, OpenClaw is a channel

```
YOU  (principal — only you cross the 3 revenue gates: marketplace acct,
      payment link, first-publish click)
        │
  HERMES  = 1st BOSS   (self-improving: persistent memory + skills, learns
                        from mistakes; commands Paperclip + OpenClaw)
          ├─ PAPERCLIP = 2nd BOSS  (operations manager: company, budgets, 8
          │       agents, heartbeat dispatch). It has NO execution tools of
          │       its own — it delegates to hired agents (Hermes/Claude).
          └─ OPENCLAW = CHANNEL   (phone/Telegram front-door; draft-only,
                  refuses to write files — Hermes must persist artifacts)
```

## Why this (the reasoning the founder accepted)

- **Hermes self-improves; Paperclip and OpenClaw do not.** A boss that gets
  smarter every session (memory + skills) beats a frozen org tool. So Hermes
  belongs at the TOP, not underneath.
- **Paperclip alone is useless** (no execution ability); **Hermes alone works**
  (30+ tools, can even command Paperclip via REST). So Hermes-as-boss is the
  most capable solo AND the best supervisor of the org.
- **OpenClaw is never boss material** — its agent is reasoning/draft-only and
  refuses file writes; it's an interface, not a worker.

## Operating mode (recommended)

- Hermes = **strategist + supervisor**: sets company direction, monitors health,
  fixes problems (e.g. reset 4 stuck `error` agents today), improves skills.
- Paperclip = **autonomous operator**: keep heartbeat ON so it self-dispatches
  work to agents without Hermes babysitting each task.
- Hermes steps in only when needed (monitor via API, reset stuck agents, assign
  blocked issues). Don't micro-manage — that wastes the self-improving boss.

## Verified: Hermes CAN control both (proven this session)

- Hermes hit Paperclip REST API: listed 8 agents, read their runtime-state,
  reset 4 stuck `error` agents (HTTP 200 on every reset).
- Hermes can start/stop the OpenClaw gateway: `openclaw gateway --port 18789`
  (currently DOWN; config present at `C:\Users\PREM KUMAR\.openclaw\openclaw.json`).

## Command map (Hermes → controls the stack)

### Paperclip (REST, :3100) — from `paperclip-company-ops`
| Action | Endpoint |
|---|---|
| Health | `GET /api/health` |
| Companies | `GET /api/companies` |
| Issues | `GET /api/companies/{id}/issues` |
| Create issue | `POST /api/companies/{id}/issues` |
| Assign agent | `PATCH /api/issues/{id}` (body `assigneeAgentId`, `status`) |
| Trigger work | `POST /api/agents/{id}/heartbeat/invoke` |
| Kill stuck run | `POST /api/heartbeat-runs/{id}/cancel` |
| Agent state | `GET /api/agents/{id}/runtime-state` |

Auth: session cookie as `Cookie:` header (curl `-b` FAILS on MSYS paths) +
`Origin: http://localhost:3100` for ALL mutations. GETs need only the cookie.
Cookie extract: `TOKEN=$(grep 'paperclip-default.session_token' cj.txt | awk '{print $NF}')`.

### OpenClaw (gateway :18789) — from `devops/openclaw-setup`
- Start: `openclaw gateway --port 18789`
- Health: `curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:18789/`
- Channels: `openclaw channels status --probe`
- Capability catalog: `openclaw capability list`
- Pitfall: `openclaw agent` is draft-only; it refuses to write files — Hermes
  must persist the returned artifact with `write_file`.

## Money boundary (non-negotiable, Charter §0)
Neither Hermes, Paperclip, nor OpenClaw can earn a rupee without the founder.
The 3 human gates: (1) marketplace account (Fiverr/Upwork/Gumroad KYC),
(2) payment link (PayPal/bank/UPI `premkumar016555@oksbi`), (3) first-publish
click. Live 2026-07-15: revenue $0, blocked on PRE-52/54/57/58.

## Verified facts bank (GitHub API 2026-07-15) — for any "comparison" doc
- `NousResearch/hermes-agent`: 214,936★ / 39,999 forks / created 2025-07-22 /
  latest v0.18.2 (tag v2026.7.7.2, 2026-07-08) / MIT.
- `paperclipai/paperclip`: 73,676★ / 13,726 forks / created 2026-03-02 /
  latest v2026.707.0 (2026-07-07) / owner `paperclipai` org.
- `openclaw/openclaw`: license NOASSERTION (NOT MIT).
- AI-generated "comparison" docs fabricate star/version/date stats — verify
  against the API before trusting. See `research/verify-ai-claims`.

## Where each agent wins (verified, not editorial)
- Hermes: coding, research, persistent memory, continuous learning, GitHub
  workflows, desktop UI + computer-use.
- Paperclip: multi-agent org, budgets, governance, executive dashboard, KPI
  tracking, department separation.
- OpenClaw: Telegram/phone delivery + remote control only (cannot build/earn).
