# 17 — Work Flow: What Happens When You Say "Build X"

## The 30-second version

```
YOU: "Build a tool that does Y"
        │
        ▼
   ┌─────────┐   classifies task, picks the right bot,
   │   CEO   │──► creates goal-mode kanban card, parks it
   └────┬────┘   in blocked queue, replies with card ID
        │
        ▼
┌───────────────────┐   every hour (or on your "go now"):
│ PRODUCTION LINE   │   releases ONE card → spawns worker
│ kanban_dispatch   │   in isolated workspace/worktree
└────┬──────────────┘
     ▼
┌───────────────┐    self-iterates up to 150-200 turns:
│ WORKER BOT    │    writes code → runs tests → fixes errors
│ (goal loop)   │    judge model decides done vs continue
└────┬──────────┘    OUTPUT LAW: files must exist in workspace
     ▼
┌───────────────┐    qa_harness.py: compiles all files,
│ QA GATE       │    runs test suites, scans secrets,
│ (hard gate)   │    checks docs. Fail = card NOT done.
└────┬──────────┘
     ▼
┌───────────────┐    security review → git init/commit →
│ SHIP          │──► gh repo create <slug> --public
│               │    push master/main → verify HTTP 200
└────┬──────────┘
     ▼
┌───────────────┐    watchdog monitors everything;
│ YOU           │    drift issues auto-open on GitHub.
│ get notified  │    You just review the repo.
└───────────────┘
```

## Step-by-step with real commands

### 1. You give the work (3 ways)
| Way | Command / action |
|---|---|
| Through the CEO | `hermes -p ceo -z "Assign: build X"` |
| Direct to a bot | `hermes -p fullstack-dev -z "build X"` |
| Drop-file queue | write `pending-task.txt` → hourly tick picks it up |

### 2. CEO classifies & routes
Picks the specialist by task type (research→research-analyst, design→agent-
architect, implementation→fullstack-dev/backend, tools→mcp-specialist…),
creates the card with deliverables + OUTPUT LAW baked into the body.

### 3. Production line releases (RAM-safe)
`kanban_dispatch.py` fires hourly: if zero workers are running, it promotes
exactly ONE card and spawns its worker. Never two — this is the 6 GB RAM law.

### 4. Worker builds in a goal loop
The worker doesn't stop after one attempt. After each turn a judge model
checks progress and continues (up to 150-200 turns) until done. It works in
its own directory so parallel builds never collide.

### 5. QA gate before "done"
qa_harness.py compiles every file, runs the project's tests, scans for
secrets, verifies README/LICENSE exist. A red harness blocks completion —
the worker must fix and retry.

### 6. Ship to GitHub
git init → commit → `gh repo create <github-account>/<slug> --public` →
push → verify the repo returns HTTP 200 with real files (phantom-completion
check: empty workspace = failed build).

### 7. You stay informed
- Watchdog alerts land in this chat only when something breaks
- GitHub fleet-sync Action audits repo structure daily
- Ask anytime: board state, build logs (`hermes kanban tail <id>`), or
  verification of any shipped repo

## What you should NOT expect
- Instant results: one quality build takes ~1-3 hours of worker time
- Zero supervision: phantom completions happen; that's why independent
  verification exists (see docs/CHANGELOG.md incident log)
- The queue to jump: cards ship first-created-first-shipped unless you say
  "prioritize X"
