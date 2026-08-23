---
name: verify-hermes-capability
description: Verify whether a Hermes Agent feature, slash command, or subcommand exists by default — by reading the LOCAL install source (not guessing, not trusting lagging docs) and exercising it live. Use when a user asks "is /X available by default?", "does Hermes have a built-in for Y?", "what are the subcommands of /Z?", or challenges a capability claim.
---

# Verify a Hermes Capability (built-in command / feature)

Never guess whether a Hermes feature or slash command exists. The install ships its
own source locally, so you can confirm authoritatively against code, then PROVE it works
by running it. Asserting "no, Hermes doesn't have that" from memory — or from a doc page
that 404s — is how you give wrong answers.

## When to use
- "Is `/goal` (or any `/command`) available by default?"
- "Does Hermes have a built-in for X?"
- "What are the subcommands of /Y?"
- User disputes a capability you stated.

## Authoritative source files (local install)
Install lives at `%LOCALAPPDATA%/hermes/hermes-agent/`
(e.g. `C:\Users\PREM KUMAR\AppData\Local\hermes\hermes-agent\`). Confirm a command/feature
exists by reading these — in order of usefulness:

1. **Desktop slash palette = single source of truth for slash commands:**
   `apps/desktop/src/lib/desktop-slash-commands.ts`
   → the `DESKTOP_COMMAND_SPECS` table. Each row: `name`, `description`, `aliases`,
   `surface` (`action` | `picker` | `exec` | `unavailable`). If it's in this table, it's
   a real, shippable command.
2. **Backend command definitions (subcommands live here):**
   `hermes_cli/commands.py` → the `CommandDef("goal", "...", ..., args_hint="...")` list.
   The `args_hint` is where a command's subcommands are declared.
3. **CLI subcommand dispatcher:** `cli.py` → grep `canonical == "<cmd>"` to see the handler branch.
4. **Top-level `hermes` subcommands:** run `hermes --help` (positional subcommands like
   `cron`, `chat`, `status`, `memory`, `config`, ...).
5. **`hermes_cli/main.py` — the giant subcommand table (NON-obvious).** Several `hermes <noun>`
   commands (`moa`, `fallback`, `secrets`, `mcp`, `migrate`, `egress`, …) are NOT in
   `commands.py` — they're wired in `main.py` via `subparsers.add_parser("<noun>", ...)`, with
   handlers in `hermes_cli/<noun>_cmd.py`. When a command is absent from `commands.py`, run
   `cd "/c/Users/PREM KUMAR/AppData/Local/hermes/hermes-agent" && grep -n 'add_parser("<noun>"' main.py`.
   The runtime for complex features often lives in `agent/<noun>_loop.py` +
   `hermes_cli/<noun>_config.py`. **Mixture of Agents (`/moa`) lives here** — see
   `references/moa-mixture-of-agents.md`. This is the right answer to "ask one question to
   many LLMs and combine their best output into one" — do NOT propose a custom council skill
   when `/moa` already ships.

Confirm the definition (commands.py / desktop-slash-commands.ts) AND, ideally, exercise it
live before telling the user "yes, it exists."

## Prove it works (live check)
Run the command in a real session and capture output:
```bash
hermes chat -q "/goal show"
```
Clean exit (EXIT=0) with real agent output = verified. Quote the actual output in your
reply; do not merely assert "it exists." Slash commands also work typed directly in the
Desktop chat box or inside `hermes chat`.

## Pitfalls
- **`search_files` / `rg` FAILS on Windows paths containing spaces**
  (e.g. `/c/Users/PREM KUMAR/...`) with
  `rg: ... The system cannot find the path specified. (os error 3)`.
  This is NOT a missing-path error — it is the space in the path. **Fix:** use the
  `terminal` tool with a quoted `cd` then `grep -r`, e.g.
  `cd "/c/Users/PREM KUMAR/AppData/Local/hermes/hermes-agent" && grep -rn "goal" --include=*.py .`
  Never conclude "command not found" from a search_files failure on a spaced path.
- **Don't rely on the docs site alone.** Docs lag the shipped build, and GitHub Pages
  sidebar slugs can 404 (e.g. `/docs/using-hermes/tui` returned a 404 while the page
  existed under a different slug). The local source is always authoritative for *this* install.
- **Companion commands & structured syntax exist.** Some commands have siblings
  (e.g. `/goal` has `/subgoal` for acceptance criteria, plus a `verify:` / `constraints:` /
  `stop when:` "contract" syntax). When the user asks about one, surface the family.

## Deliverable shape
Reply with: (1) a yes/no confirmed against source, (2) the command + its subcommands,
(3) a live-run proof snippet. See `references/goal-command.md` for a worked example
(`/goal`, verified 2026-07-14 on this install).
