# 18 — High-Level Plan: Harness "Earned Completion" Integration

> Adapting the proven `hermes-harness-plugins` patterns into our company
> pipeline. Goal: **no card can ever be marked done without passing its proofs**,
> and stagnating builds self-heal instead of dying.

## Where work registers today (current state)

```
WORK REGISTERS (existing):
1. Kanban board  it-company-ops (SQLite)   ← the ONLY work ledger
2. Card body     tasks.body                ← prose spec + OUTPUT LAW
3. task_events   event log                 ← history, not enforcement
4. qa_harness.py post-hoc gate             ← runs only if worker chooses
5. Watchdog      infra health              ← no per-card quality signal

GAP: "done" is declared by the WORKER (self-report). Nothing VETOES it.
```

## The design principle we're adopting

From hermes-harness: **completion is EARNED via executable proofs**, and a
hook pipeline can VETO transitions (`pre_gate`, `on_completion`) before they land.

```
harness concept            →   our company equivalent
─────────────────────────      ─────────────────────────────
engine/run.py host         →   kanban worker lifecycle + dispatcher
pre_gate veto hooks        →   card-start validation (goal present)
on_completion veto         →   DONE-gate: checklist proofs must pass
goal-registry plugin       →   per-card goal.json in workspace
completion-checklist       →   per-card checklist.json in workspace
supervision plugin         →   failure-counter model rotation
progress-reporter          →   watchdog/dashboard gate events
lineage ledger             →   task_events + proof evidence hashes
scenario bundles           →   strict-ship vs fast-draft card modes
```

## Implementation plan (4 increments, each independently shippable)

### INC-1 · ProofChecklists (P0 — kills phantom completions)
**Where:** new script `%HERMES_HOME%/scripts/proof_checklist.py`
+ integration at ONE point: the dispatcher's done-transition check.
**Flow:**
1. Card created → CEO/adaptive_mode auto-writes `<workspace>/checklist.json`:
   ```json
   [{"id":"files-exist","item":"project files exist",
     "proof_cmd":"python -c \"import os;assert os.path.getsize('README.md')>0\"",
     "status":"FAIL"},
    {"id":"tests","item":"test suite green","proof_cmd":"python -m pytest -q"},
    {"id":"qa-harness","item":"qa_harness PASS","proof_cmd":"python %SCRIPTS%/qa_harness.py ."},
    {"id":"secrets","item":"no committed secrets","proof_cmd":"python scan_secrets.py ."},
    {"id":"pushed","item":"repo live","proof_cmd":"curl -sf https://api.github.com/repos/<acct>/<slug>}"]}
   ```
2. Worker may self-run proofs anytime (`proof_checklist.py run <card>`).
3. **Dispatcher veto:** when a card reports done, dispatcher executes every
   `proof_cmd`; any non-zero exit → card returns to `running` with veto reason
   logged to `task_events` (+ evidence hash). Worker sees remaining items.
**Effort:** ~2 hrs. **Risk:** low (pure addition; existing cards unaffected).

### INC-2 · GoalRegistry per card (P1 — stops scope drift)
**Where:** same script family; written at card creation by ceo/adaptive_mode.
**Flow:** `<workspace>/goal.json` = `{goal, criteria[], owner_prompt}` captured
from the card body at creation time. The goal-loop judge prompt includes the
registered criteria verbatim; INC-1 adds proof `goal-criteria-documented`.
**Effort:** ~1 hr.

### INC-3 · Supervision rotation (P2 — self-healing builds)
**Where:** dispatcher + watchdog.
**Flow:** on `consecutive_failures >= 2`, instead of parking blocked:
rotate `model_override` to the next fallback (NIM ↔ laguna), reset counter,
log `SUPERVISOR_REDIRECT` event. After 3 rotations → park blocked + alert.
**Effort:** ~1 hr.

### INC-4 · Gate events → dashboard (P3 — visibility)
**Where:** company_watchdog.py gains check #6 "proof-gate health":
last-N vetoes, pass rate, per-bot phantom score. Ops dashboard row added.
**Effort:** ~1 hr.

## Scenario bundles (later, optional)
Map harness scenarios to card priority classes:
- `strict-ship` (default for public repos): all plugins on
- `fast-draft`: skip push-proof, keep tests+secrets proofs
- `research-only`: citation proofs only

## What we deliberately DON'T adopt
- Harness's own engine/run loop — our kanban+dispatcher already is the host;
  double-hosting would fight the gateway.
- Domain evaluators (coding/docs-sync) — qa_harness covers this role today;
  revisit only if we need AST-level doc coverage.

## Rollout order & success criteria
| Inc | Ships | Success looks like |
|---|---|---|
| INC-1 | immediately | zero cards reach done with empty workspace |
| INC-2 | with INC-1 | every running card has goal.json |
| INC-3 | next | failures rotate models before parking |
| INC-4 | next | dashboard shows proof pass-rate ≥ 90% |

All code lives in `scripts/` (live) + mirrored to repo `scripts/` (versioned);
docs in `docs/18-*`. No engine forks, no third-party daemons, $0 cost.
