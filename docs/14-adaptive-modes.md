# 14 — Adaptive Goal/Loop Modes

The company now **configures its own execution mode per task** based on requirements.

## The decision engine — `scripts/adaptive_mode.py`

```
analyze "<task text>"   → prints recommended mode + reasoning
create <assignee> -- "<task text>"  → creates the card with correct flags
```

**Decision matrix (signal-based classification):**

| Signals in task text | Mode | Why |
|---|---|---|
| build / implement / migrate / end-to-end / full / complete / fix-failing / refactor (≥2 hits, or long spec) | **GOAL** (`--goal --goal-max-turns 120-200`) | Complex work must self-iterate: a judge model decides done vs continue each turn instead of one-pass-and-stop |
| rename / typo / update-docs / status-check (≥1 hit, no goal signals) | **PLAIN** | Mechanical tasks don't need judge overhead |
| ambiguous | **GOAL** (safe default) | Better to iterate than half-finish |

## Intake automation — `scripts/adaptive_intake.py`

Drop `%LOCALAPPDATA%\hermes\pending-task.txt`:
```
fullstack-dev
Build: price-patrol. Complete monitoring agent with tests and CLI
```
The next dispatcher tick automatically: classifies → creates card with correct mode → renames file `.done`. Verified end-to-end (goal card created via the hourly line).

## Quality gates (deterministic done)

Goal cards for builder bots get a suggested gate:
```
/goal gate add python %HERMES_HOME%/scripts/qa_harness.py <worktree>
```
Gates run BEFORE the judge — a red harness makes "done" impossible, regardless of LLM judgment.

## Loops (/loop) vs cron in this company

`/loop` is session-scoped monitoring; our equivalent lives in **cron routines**
(watchdog 30m, production line 60m) because those survive restarts. Use `/loop`
interactively inside a bot chat when you want live polling ("poll CI every 2m until green").

## Verified
- `analyze` correctly classified complex build → GOAL (budget 120) and typo-fix → PLAIN
- Full pipeline: pending-task.txt → dispatcher tick → goal_mode=1 card created → test card cleaned
