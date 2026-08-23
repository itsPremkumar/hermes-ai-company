# Durable standing-goal keeper (cron pattern)

Use when the user wants a persistent "/goal" that survives chat sessions.

## Why /goal alone isn't durable
`/goal` drives a loop ONLY while the `hermes chat` session that issued it stays
alive. Close the chat (or run `hermes chat -q "/goal ..."`, which executes ONE
turn then exits) and the loop dies. There is no background `goal` service and no
agent-side `goal` tool.

## The durable form: a goal-keeper cron
Encode the goal as a self-verifying cron whose PROMPT *is* the contract:

1. Write `GOAL_ACTIVE.md` in the project root:
   - **Objective** — what "done" means.
   - **Standing invariants** — commands that MUST keep passing every tick
     (e.g. `python run_all.py self-test` → `self-test: OK — 15 pipelines, 62
     packages, all priced`). If an invariant breaks, STOP and report — do NOT
     silently lower the bar.
   - **Per-tick acceptance checks** that require REAL command output, not claims.
   - **Repair rules** — bounded, within `agent.goal_max_turns` (set to 120 once
     via `hermes config set agent.goal_max_turns 120`).
   - **Human gates** — steps the agent must PAUSE at and print a checklist for
     (e.g. create marketplace accounts, link payment, publish first gig).
   - **Stop condition** — when the goal is actually achieved.
2. `cronjob action=create` with:
   - `workdir` = the project repo
   - `enabled_toolsets` = ["terminal","file","web"]
   - `schedule` = e.g. `0 */6 * * *` (6h; bounded cost)
   - `prompt` = "Read GOAL_ACTIVE.md; each run execute the loop and VERIFY every
     claim with real command output; repair within budget; PAUSE and print a
     3-action checklist at human gates; report <200 words."
3. Run once immediately (`cronjob action=run`) and read
   `$LOCALAPPDATA/hermes/cron/output/<job_id>/<timestamp>.md` to confirm it
   self-verified (don't just trust `last_status: ok`).

## How to confirm a Hermes slash command exists (don't guess)
Grep the installed source, then live-run it to prove it:
- `apps/desktop/src/lib/desktop-slash-commands.ts` — the desktop slash palette
  (e.g. `{ name: '/goal', ... }`).
- `hermes_cli/commands.py` — backend registration (`CommandDef("goal", ...)`).
- `cli.py` — the dispatcher (`elif canonical == "goal":`).
Then `hermes chat -q "/goal show"` to prove it works. `/goal` IS a default
built-in (no plugin/install needed).

## Cron fleet diagnostic: gateway-down
- **Symptom:** crons don't fire at all, or a batch flips to `error` with
  `APIConnectionError` and no single job is misconfigured.
- **Cause:** the Hermes **gateway process is not running** → no job auto-fires.
- **Fix:** `hermes gateway install` (brings the gateway up, prints a PID). Then
  transient `APIConnectionError` crons self-heal on their next tick; only
  config-drift crons (see CRON MODEL-CONFIG-DRIFT GUARD in SKILL.md) need
  explicit `cronjob action=update ... provider=... model=...` pinning. Do NOT
  edit jobs that merely hit a connection blip — that is not a code fault.
