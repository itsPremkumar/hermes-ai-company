# Autonomous full-build via `/goal` (Ralph loop)

Technique for running an entire money-system build with **zero per-step prompts**.
Verified against Hermes source `hermes_cli/goals.py` (the loop is real; it is NOT
named "loop" — the command is `/goal`).

## Why
The user micro-managed a long build with repeated "continue" prompts. `/goal` lets
Hermes self-continue across turns via a judge (DONE / CONTINUE / WAIT), so one
standing instruction replaces dozens of nudges.

## Hard facts (from goals.py)
- Judge returns 3 verdicts: `done` (stop), `continue` (auto-feed next step),
  `wait` (park on a PID/timer — no turn burned).
- Continuation is a normal user message — **prompt caching stays intact**, no
  system-prompt/toolset mutation.
- Judge failures are **fail-open** (→ continue); the **turn budget** is the backstop.
- A real user message **preempts** the loop and pauses it for that turn.
- Default `goal_max_turns = 20` — too low for a 12-pipeline build. **Raise it first.**

## Config prerequisite (one-time)
```
hermes config set agent.goal_max_turns 120
```
(If your build exposes a different key, check `hermes config | grep -i goal`.)

## Paste-ready activation
```
/goal draft <plain-language objective>
/goal <the returned 5-field completion contract>
```
The `draft` step turns your words into a **completion contract** (outcome /
verification / constraints / boundaries / stop_when). The judge then refuses
`DONE` unless the **verification** criterion is met with concrete evidence
(command output, file excerpt, test result) — not a vague "all done".

## The 3 human gates (must be in `stop_when`)
Only a human can do these; the loop pauses and prints a checklist at each:
1. **Account gate** — create marketplace accounts (Fiverr/Upwork ID verify).
2. **Payment gate** — link PayPal/Stripe (bank, tax).
3. **First-gig gate** — approve the first live gig.

After each, user types `/goal resume`.

## Example objective for the money/ pipelines
"Build the 7 remaining pipelines (#6–#12) from MONEY_AUTOMATION_IDEAS.md, wire
each into money/run_all.py, replace n8n stub manifests with working workflow JSON,
build infra/docker-compose.yml + SETUP.md, generate listings/ copy for every
package, schedule acquisition loop. STOP at the 3 human gates."

## CRITICAL agent-side constraint (learned 2026-07)
`/goal` is a **human-only slash command**. The agent has NO `goal` tool and cannot
invoke it. Concretely:
- There is no `goal` tool in the agent's toolset — it can only *write* the text.
- `hermes chat -q "/goal ..."` runs ONE turn then exits; the goal loop needs a
  **persistent session**, so this does NOT start the loop. Do not promise the agent
  "configured the goal for you" — only the user typing `/goal` in chat starts it.
- Legitimate agent hands-off equivalent: when the user pastes the goal text as a
  normal message, treat it as authorization and EXECUTE the build directly in-session
  (autonomous, no per-step prompts). Same outcome as the `/goal` loop, different
  mechanism. State this honestly instead of claiming the loop was started.
- If you prepared a plan file (e.g. AUTONOMOUS_GOAL_PLAN.md) but the user never pasted
  `/goal`, the goal is NOT active — say so plainly.
