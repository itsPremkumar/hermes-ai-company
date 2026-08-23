# 09 — SOPs & Standing Instructions (Company Constitution)

These are the operating procedures every bot session inherits. Sources:
bot SOULs (`souls/`), qa-lead's standing order, dispatcher laws (docs/03),
and the runbook (docs/08). This file is the single index of ALL rules.

## §1 Identity & Cost Laws
1. The company runs on **$0/month**. No paid API keys, no subscriptions.
   Approved inference: OpenRouter `:free` models + NVIDIA NIM fallback chain only.
2. **Pure Hermes only.** No third-party daemons (Paperclip/OpenClaw are banned
   for RAM reasons). Everything is profiles + gateway + cron + kanban.
3. GitHub = single source of truth. Work not committed/pushed did not happen.

## §2 Production Line SOP (kanban)
- Cards LIVE in `blocked`; only `scripts/kanban_dispatch.sh` releases ONE per tick,
  and only when zero workers are running.
- `dispatch_in_gateway: false` is PERMANENT. Never re-enable on this box.
- Builder bots run with max_turns=200 in their own worktree.
- After any manual kill: clear stale claim_locks before expecting dispatch to resume.

## §3 Quality Gate SOP (qa-lead)
1. Run the project's own suite first if present (ci/verify_product.py, pytest…).
2. ALWAYS also run: `python %HERMES_HOME%\hermes\scripts\qa_harness.py <dir>`
3. VERDICT PASS (exit 0) or the card goes back with request-changes.
4. A teammate's self-report is NEVER proof — reproduce independently.

## §4 Security SOP (security-engineer + all)
- No hardcoded secrets in any shipped file (qa_harness enforces).
- `.env` files never leave `%HERMES_HOME%\hermes\profiles\<bot>\` — never committed.
- Pushes to product repos go as `<github-account>`; admin ops as `<github-org>`.
- Community skills failing Hermes security scan stay uninstalled (already proven).

## §5 Escalation SOP
- Bots escalate judgment calls via @user → needs-you badge (group rooms) or watchdog
  alert (origin chat). Owner-only actions: hermes update, publish/spend, account work.

## §6 Communication SOP
- Direct orders → bot's canonical chat. Handoffs → message_agent with attribution.
- Deliberation → team room (≤6 members, ≤3 rounds). Watchdog silence = healthy.
