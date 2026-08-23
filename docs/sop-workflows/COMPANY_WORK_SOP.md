# IT Company — Work Assignment & Execution Protocol (SOP)

This document defines how work flows through the virtual IT services company so
every sub-agent does its own work, acknowledges assignments, follows up, and
submits finalized work with proper review. It is enforced via the shared kanban
board `it-company-ops` (`hermes kanban`, switched to this board).

## 1. Role of the Board
The kanban board is the SINGLE SOURCE OF TRUTH for who is doing what.
- One board per project/workstream: `hermes kanban boards create <slug> --switch`
- All assignment, acknowledgment, progress, review, and submission happen as
  board events — never only in chat.

## 2. Work Lifecycle (mandatory states)
```
ready → assigned → claimed → in_progress → (request-review ⇄ request-changes)*
       → approved → completed → archived
```

| State | Who | Action (kanban command) |
|---|---|---|
| ready | Chief of Staff | `kanban create` (title, desc, acceptance criteria) |
| assigned | Chief of Staff | `kanban assign <id> --to <profile>` (route by role) |
| claimed | Assignee | `kanban claim <id>` → prints workspace → starts work |
| in_progress | Assignee | `kanban comment <id> "ACK: accepted, ETA X"` (acknowledgment) |
| review | Assignee | `kanban request-review <id>` when done |
| changes | Reviewer | `kanban request-changes <id> "fix: ..."` (feedback loop) |
| approved | Reviewer | `kanban comment <id> "APPROVED"` after changes |
| completed | Assignee | `kanban complete <id>` (final submission) |
| archived | Chief of Staff | `kanban archive <id>` after sign-off |

## 3. Acknowledgment Rule (no silent acceptance)
An assignee MUST post an ACK comment within the task before doing work:
`ACK: accepted | scope: <what> | ETA: <when> | blockers: <none|...>`
If blocked, post `BLOCKED: <reason>` and the Chief of Staff reroutes.

## 4. Follow-Up Rule
- Progress comments at meaningful milestones (`PROGRESS: <x% / what done>`).
- On delay, post `DELAY: <new ETA> | reason`.
- Reviewer feedback is a two-way loop: `request-changes` → fix → `request-review` again.

## 5. Final Submission Rule
`complete` is ONLY allowed after:
1. Acceptance criteria met (self-checked by assignee),
2. At least one `request-review` cycle closed with approver comment `APPROVED`,
3. Evidence attached (`kanban attach <id> <file>`) — logs, outputs, test results.

## 6. Routing Map (who does what)
- Strategy / business case → CEO
- Tech architecture / stack → CTO
- Delivery / timelines → VP Delivery
- Feature definition → Product Manager / Product Owner
- Sprint/resource planning → Project Manager / Scrum Master
- System design → Solution Architect
- Code (front/back/full) → Tech Lead, Senior FE/BE, Full Stack, Junior, DevOps, Data
- Quality / tests → QA Lead, QA Engineer
- UI/UX → UI/UX Designer
- Docs → Technical Writer
- Hiring/identity → HR & Recruiter
- Client/sales → VP Sales, Business Dev
- Provisioning new agents → Chief of Staff
- Anything cross-team or ambiguous → Chief of Staff

## 7. Escalation
Assignee stuck > ETA with no BLOCKED post → Chief of Staff reclaims
(`kanban reclaim`) and reassigns.

## 8. Commands Quick Reference
```
hermes kanban boards switch it-company-ops
hermes kanban create "Task title" --desc "..." --acceptance "..."
hermes kanban assign <id> --to <profile>
hermes kanban claim <id>
hermes kanban comment <id> "ACK: ..."
hermes kanban request-review <id>
hermes kanban request-changes <id> "fix: ..."
hermes kanban attach <id> <file>
hermes kanban complete <id>
hermes kanban archive <id>
hermes kanban show <id>          # full audit trail
hermes kanban list                # board state
```
