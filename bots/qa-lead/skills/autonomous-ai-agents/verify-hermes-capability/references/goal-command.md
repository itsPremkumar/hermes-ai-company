# Worked example: `/goal` is a built-in default command

Verified 2026-07-14 on this Windows install
(`C:\Users\PREM KUMAR\AppData\Local\hermes\hermes-agent`).

## Question
User: "is `/goal` a default command available in Hermes?" (asked after a clarification
that they were NOT asking about a cron job — the phrase "goal command" was ambiguous).

## Confirmation via source (3 independent hits)
1. `apps/desktop/src/lib/desktop-slash-commands.ts:153`
   `{ name: '/goal', description: 'Manage the standing goal for this session', surface: exec() }`
   → it is in the desktop slash palette (so typing `/goal` in the chat box works).
2. `hermes_cli/commands.py:114`
   `CommandDef("goal", "Set a standing goal Hermes works on across turns until achieved", "Session", args_hint="[text | draft <text> | show | pause | resume | clear | status | wait <pid> | unwait]")`
3. `cli.py:8867`
   `elif canonical == "goal": self._handle_goal_command(cmd_original)` → handler wired up.
Companion: `commands.py:118` defines `/subgoal "<text> | remove N | clear"`.

## Live proof
```
hermes chat -q "/goal show"
```
Returned real agent output (full usage/contract docs) and exited 0:
`Session: 20260714_075223_c26f40  Duration: 1m 13s  Messages: 18  EXIT=0`

## What `/goal` does
A *standing goal*: Hermes keeps working toward it across turns until achieved.
Setting one auto-starts the loop (queues the goal text as the next turn).
Ctrl+C during a goal turn pauses it (resumable via `/goal resume`); a real user
message preempts the goal.

Subcommands (from `args_hint`):
- `/goal <text>`        set a standing goal
- `/goal draft <text>`  draft without committing
- `/goal show`          show current goal
- `/goal status`        progress/status
- `/goal pause`         pause the loop
- `/goal resume`        resume a paused goal
- `/goal clear`         clear it
- `/goal wait <pid>`    pause until a process finishes
- `/goal unwait`        resume after wait
- `/subgoal <text>`     add acceptance criterion (no interrupt)
- `/subgoal remove N`   remove one

Inline "contract" syntax (alternative to `/goal draft`):
```
/goal Build the login page
verify: npm test auth
constraints: must use existing Button component
stop when: all tests pass and PR opened
```

## Tooling note for this session
`search_files` failed on the spaced path with `os error 3`; switched to
`terminal` with quoted cd + grep, which worked. (See SKILL.md pitfalls.)
