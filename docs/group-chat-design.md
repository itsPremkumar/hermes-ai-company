# Hermes Group Chat — Complete Platform Design Specification

> Author: @cto. Authoritative design doc answering the CEO directive: "for our
> company we need an hermes group chat feature — if need means for what, are the
> agent we need group chat feature, how many group and group member list, i need
> full details and its main uses."
>
> This is the canonical specification handed to engineering (@fullstack-dev,
> @mcp-specialist) for implementation. It is NOT a project blueprint for any
> specific OSS flagship — it is the cross-agent collaboration substrate THEY
> all build on top of.
>
> Staged via the `company-arch` skill; live-deployed (git push) by @devops-engineer
> into `itsPremkumar/hermes-ai-company` `docs/group-chat-design.md`.

---

## 1. Group Definition & Purpose Analysis

### 1.1 What triggers the group chat need?

A group chat is created when a unit of work requires more than one avatar to
coordinate within a bounded time window and cannot be expressed as a single
linear handoff (track transfer §3 of team-architecture.md). The need is
triggered by one of these patterns:

**Pattern A — Parallel specialization within one layer.**
A single concern requires expertise the owning avatar does not alone possess.
Example: an MCP server (@mcp-specialist) needs a schema agreed with an agent
architecture (@agent-builder) before either can write code — neither owns the
other, but both must be present, in real time, to converge.

**Pattern B — Phase boundary with no single successor.**
Work moves from one phase to the next, but the handoff is not a baton pass to
one avatar — it fans out to a responsibility set. Example: the TaskForge
engineering track (t_b259c545) lands on `main`; at that moment the work is NOT
transferred to a single QA avatar — it is published into the QA pipeline GROUP
where @qa-lead (test lead), @agent-builder (agent harness), and
@fullstack-dev (repo owner) must all react to the same artifact.

**Pattern C — Real-time incident response.**
A track has stalled, crashed, or is producing contradictory state (cf. the
@fullstack-dev crash, team-architecture.md §2.1.1). The affected avatar +
@qa-lead + @cto + (optionally) @ceo must be simultaneously addressable so the
incident is declared, root-caused, and resolved in one conversational context.

**Pattern D — Governance / review boards.**
Certain decisions require a quorum of roles by policy, not by convenience.
Security sign-off, release gates, budget approvals — these are group chats by
design because the rule mandates which avatars must be present.

**Pattern E — Crisis management (claimerman pattern).**
When any avatar crashes mid-track, @claimerman fires and all *surviving*
members of that avatar's active groups are auto-invited into a fresh incident
group. The crash is never retried blind; the group coordinates the retry, the
re-dispatch, and the artifact salvage. This is the group chat acting as a
crash-recovery coordinator.

### 1.2 Group chat vs. 1:1 DM

| Decision factor | Use 1:1 DM (@cto → @devops-engineer) | Use group chat |
|---|---|---|
| Number of decision-makers | exactly 2 | ≥ 2 *and* the third matters |
| Artifact ownership | linear handoff | shared/parallel ownership |
| Time window | asynchronous is acceptable | synchronization needed now |
| Failure mode | single successor | broadcast needed (Pattern C/E) |
| Precedent | team-architecture.md §2.2 transfer | this doc §2 groups |

A 1:1 DM is always *contained within* a group chat (group → individual DM
escalation, §5.3). A group chat is never spawned for a purely linear transfer.

### 1.3 Which avatars benefit?

All of them. The roster (canonical, from team-architecture.md §1 + live
roster):

| Handle | Role | Benefits from groups |
|---|---|---|
| `@ceo` | CEO / priority | Leadership council, crisis escalation (Pattern C/E) |
| `@cto` | Vision / standards | Leadership council, architecture review board, crisis escalation |
| `@devops-engineer` | Infra + git push | CI/CD pipeline, repo liveness monitoring, crisis coordination |
| `@fullstack-dev` | Repo + feature work | Engineering team, QA handoff, crisis (its own crash recovery) |
| `@agent-builder` | Pipelines / agents | Engineering team, QA pipeline, incident response |
| `@agent-architect` | Agent schema / design | Research team, architecture review board |
| `@mcp-specialist` | MCP servers / tools | Engineering team, integration group, security review board |
| `@qa-lead` | Test + monitoring | QA pipeline, monitoring board, incident response |
| `@security-engineer` | Hardening / posture | Security review board, release approval |
| `@research-analyst` | Market / intel | Research team, leadership council (strategy input) |
| `@product-manager` | Priority / roadmap | Leadership council, research team |
| `@vp-sales` | Sales / GTM | Leadership council, product council |
| `@claimerman` | Crash recovery | Auto-invoked in ALL incident groups (Pattern E) |

---

## 2. Number of Groups

There are **8 permanent groups** + a **dynamic group class** for incidents.
Each group is a persistent channel with a stable membership, a defined
purpose, and a single owning avatar (the "chair") who controls membership
and lifecycle.

### 2.1 Group roster

| # | Group name | Chair | Members | Purpose |
|---|---|---|---|---|
| G1 | `eng-core` | `@fullstack-dev` | fullstack-dev, agent-builder, mcp-specialist, qa-lead, agent-architect | Core engineering: feature build, code review, CI/CD pipeline |
| G2 | `research-lab` | `@research-analyst` | research-analyst, agent-architect, product-manager, cto | Early-stage research, feasibility, schema design before eng handoff |
| G3 | `leadership-council` | `@ceo` | ceo, cto, vp-sales, product-manager, devops-engineer | Company strategy, priority, resource allocation, OKR alignment |
| G4 | `qa-pipeline` | `@qa-lead` | qa-lead, agent-builder, fullstack-dev, mcp-specialist | Test execution, harness design, PR verification, trace validation |
| G5 | `security-review-board` | `@security-engineer` | security-engineer, mcp-specialist, cto, devops-engineer | Security gates, hardening reviews, MCP server vetting, release sign-off |
| G6 | `infra-operations` | `@devops-engineer` | devops-engineer, fullstack-dev, qa-lead, mcp-specialist | Repo liveness, dispatch health, monitoring config, green-hold enforcement |
| G7 | `architecture-council` | `@cto` | cto, agent-architect, fullstack-dev, security-engineer | Cross-project architecture standards, dependency resolution, schema |
| G8 | `monitoring-ops` | `@qa-lead` | qa-lead, devops-engineer, cto | monitconfig.json maintenance, alert tuning, escalation trigger integrity |
| — | `incident-*` (dynamic) | `@claimerman` | auto-invites all members of the crashed avatar's groups + claimerman | Crash recovery (Pattern E), real-time incident (Pattern C) |

### 2.2 Membership rationale

- **eng-core (G1):** This is the default build room. @fullstack-dev chairs
  because the engineer who writes the most code owns the build surface.
  @qa-lead sits in eng-core (not just qa-pipeline) so test feedback is
  synchronous during the build, not post-hoc.
- **research-lab (G2):** @research-analyst chairs because market intel drives
  feasibility. @agent-architect is present so research findings map to schema
  before eng. @product-manager represents roadmap priority.
- **leadership-council (G3):** @ceo chairs. All C-suite + product + devops so
  strategy has the operational constraint set in the room.
- **qa-pipeline (G4):** @qa-lead chairs; this is the *output* gate. Eng
  members present here because their code is being tested, not to direct it.
- **security-review-board (G5):** @security-engineer chairs; MCP servers
  (@mcp-specialist) are the primary surface, so they are always present.
  @cto attends for architecture sign-off on new integrations.
- **infra-operations (G6):** @devops-engineer chairs; this is the operational
  backbone. @qa-lead and @fullstack-dev attend because infra health directly
  gates their tracks (cf. the max_runtime=0s green-hold).
- **architecture-council (G7):** @cto chairs the standards body. Members are
  the avatars who own surfaces that standards touch — repo owner, schema owner,
  and security. This is the escalation path for §3 dependency disputes.
- **monitoring-ops (G8):** @qa-lead chairs; this is the monitoring protocol
  control room. @devops-engineer attends because checks emit to the infra
  repo; @cto attends because monitoring is the company's liveness signal.

### 2.3 Dynamic incident groups

When @claimerman fires (any avatar crash, Pattern E), a new group
`incident-<task-id>-<timestamp>` is auto-created with:
- members = union of all groups the crashed avatar belonged to, PLUS
  @claimerman and @ceo (escalation).
- chair = @claimerman (recovery protocol).
- purpose = coordinate the crash retry, salvage artifacts, and confirm root
  cause before re-dispatching the stalled track.
- lifecycle = auto-archived (read-only) once the recovered track either
  completes or is re-queued with a new owner.

This is the group-chat realization of team-architecture.md §2.1.1's crash
recovery: the chat IS the recovery coordination surface.

---

## 3. Full Group Member Lists (Roster + Handles)

### G1 — `eng-core`
- `@fullstack-dev` (chair) — Repo + feature work; owns the build surface
- `@agent-builder` — Pipelines/agents; builds the agent harness the repo runs
- `@mcp-specialist` — MCP servers/tools; integrates tools the build depends on
- `@qa-lead` — Test/monitoring; synchronous test feedback during build
- `@agent-architect` — Agent schema/design; validates architectural fit

### G2 — `research-lab`
- `@research-analyst` (chair) — Market/intel; drives feasibility + priority
- `@agent-architect` — Schema design; turns research into implementable spec
- `@product-manager` — Roadmap; aligns research with priority lane
- `@cto` — Vision; ensures research maps to company direction

### G3 — `leadership-council`
- `@ceo` (chair) — Strategy, priority, resource, OKR alignment
- `@cto` — Tech vision, architecture gates, scaling posture
- `@vp-sales` — GTM, market fit, revenue implications
- `@product-manager` — Product priority, roadmap
- `@devops-engineer` — Operational capacity, infra constraints

### G4 — `qa-pipeline`
- `@qa-lead` (chair) — Test lead; owns the gate
- `@agent-builder` — Agent harness tests; verifies agent-level behavior
- `@fullstack-dev` — Repo owner; must react to failing tests on their code
- `@mcp-specialist` — Tool integration tests; verifies MCP surfaces

### G5 — `security-review-board`
- `@security-engineer` (chair) — Hardening/posture; owns sign-off
- `@mcp-specialist` — Primary MCP surface; must defend/vouch for servers
- `@cto` — Architecture security sign-off on new integrations
- `@devops-engineer` — Infra posture; container/network/runtime hardening

### G6 — `infra-operations`
- `@devops-engineer` (chair) — Infra + git push; owns liveness
- `@fullstack-dev` — Repo; depends on infra health for builds
- `@qa-lead` — Monitoring config; checks emit to infra repo
- `@mcp-specialist` — Integration tooling; depends on infra for MCP routing

### G7 — `architecture-council`
- `@cto` (chair) — Vision/standards; owns cross-project architecture
- `@agent-architect` — Schema; owns the agent contract standard
- `@fullstack-dev` — Repo; owns the implementation fidelity surface
- `@security-engineer` — Posture; owns security non-functional requirements

### G8 — `monitoring-ops`
- `@qa-lead` (chair) — Test/monitoring; owns the protocol
- `@devops-engineer` — Infra; owns check emission + repo liveness
- `@cto` — Standards; owns escalation trigger integrity

### Dynamic — `incident-*`
- `@claimerman` (chair) — Crash recovery protocol
- `@ceo` — Escalation; notified on all incidents
- +(union of all groups the crashed avatar belonged to)

---

## 4. Main Uses

### Use 1: Real-time incident response
**Scenario:** `@fullstack-dev` crashes mid-track (cf. the PTY crash,
team-architecture.md §2.1.1). @claimerman auto-fires and creates
`incident-t_b259c545-<ts>` with all of eng-core + qa-pipeline + infra-ops
members. The group declares root cause ("3 concurrent in-process shells on one
PTY session"), confirms the @agent-builder commit 2823c48 is the post-fix
engine, and coordinates the retry — all in one channel. The green-hold
(team-architecture.md §2.1) is released only when the group chairs sign off.

### Use 2: Cross-phase handoffs
**Scenario:** TaskForge flagship spec lands on `main` (Track 1 → Track 2).
This is NOT a 1:1 transfer to @fullstack-dev — it is a fan-out into the
`qa-pipeline` group, where @qa-lead publishes the test plan, @agent-builder
wires the agent harness, and @fullstack-dev confirms the repo is visible.
The GROUP is the handoff context; each member acknowledges their slice.
This is the group realization of team-architecture.md §3 dependency gating.

### Use 3: Multi-agent code review
**Scenario:** @mcp-specialist submits an MCP server for `@agent-architect` +
`@security-engineer` + `@fullstack-dev`. Because the review spans schema
(architect), hardening (security), and repo integration (fullstack-dev), it
spawns in the `security-review-board` group (G5) — the policy-required quorum.
A single approval does not ship; the group must reach consensus, and the
decision is recorded as a group-signed artifact linked back to the PR.

### Use 4: CI/CD pipeline coordination
**Scenario:** A `main` commit triggers the deploy gate. The `infra-operations`
group (G6) receives the notification: @devops-engineer confirms the git tree
is interactive, @qa-lead confirms the monitoring trace is green, @mcp-specialist
confirms the MCP routing is stable, and @fullstack-dev confirms the repo
matches. The deploy proceeds only when all four chairs sign the group thread.
This is the group-chat enforcement of the green-hold gate.

### Use 5: Crisis management (claimerman)
**Scenario:** ANY avatar crashes. @claimerman fires, auto-creates an
`incident-*` group, and the group performs the recovery protocol:
(a) declare the failure (artifact + error), (b) identify survivors,
(c) confirm the post-fix engine commit, (d) re-queue the track with explicit
ownership, (e) close the incident and archive read-only. This replaces the
current ad-hoc recovery with a structured, auditable protocol. It is the
group-chat instantiation of team-architecture.md §2.2 (track ownership
transfer) — the group IS the transfer surface.

### Use 6: Architecture standards consensus
**Scenario:** @mcp-specialist proposes a new MCP server schema that touches
agent contracts (@agent-architect), repo structure (@fullstack-dev), and
security posture (@security-engineer). Because no single avatar owns the full
surface, this is discussed in the `architecture-council` group (G7) — the
standards body. The decision is recorded as a signed group artifact and
becomes the new cross-project standard (team-architecture.md §3).

---

## 5. Architecture Requirements

### 5.1 Message routing between avatars in a group
- Group chats are backed by a durable **pub/sub channel** per group. Each avatar
  subscribes to the groups it belongs to.
- A message sent to group G is delivered to all current members of G and
  persisted to G's thread store.
- Members can leave/join a group; join grants catch-up replay from the point of
  joining (not full history by default, to avoid noise — full history is
  available on demand).

### 5.2 Thread preservation across multi-agent conversations
- Every group message has a stable **thread ID**. Replies nest under the
  thread, preserving the conversational context across avatar turns.
- A thread is auto-created per track mention: when a task ID is named in a
  group (e.g. `@qa-lead see t_b259c545`), a thread is created linking the
  group conversation to the kanban task. This satisfies team-architecture.md
  §3.1 (traceable edges) — the group thread IS the dependency trace.

### 5.3 Escalation paths (group → individual DM)
- Any avatar can "escalate" a group thread to a 1:1 DM with any other member,
  pulling that sub-conversation out of the group context without losing the
  link (the DM thread references the originating group thread).
- The classic escalations (incident → @ceo, schema dispute → @cto, deploy gate
  → @devops-engineer) are all supported this way.

### 5.4 Persistent group history
- Group history is persisted to the infra repo under `groups/<group-name>/`
  as structured JSONL logs, committed by @devops-engineer.
- History is queryable by track ID, avatar handle, and date range.

### 5.5 Bot-to-bot @mention support
- All messaging supports `@handle` mentions. A mention triggers a notification
  to the mentioned avatar and (if the avatar is in goal_mode) can wake the
  avatar's goal loop.
- @claimerman auto-mentions all members of an incident group on creation.

### 5.6 Group creation / deletion lifecycle
- **Permanent groups** (G1–G8): created by @cto policy, membership managed by
  the chair. Lifecycle = company-wide; not deletable except by @ceo + @cto
  joint decision.
- **Dynamic groups** (incident-*): created by @claimerman on crash, archived
  (read-only) on incident close, never deleted (audit trail).
- **Ad-hoc groups**: any avatar can propose a group in the
  `leadership-council`; @ceo approves. Ad-hoc groups expire after 30 days of
  inactivity and auto-archive.

### 5.7 Integration with the kanban board
- Every group thread is linkable to a kanban task via `<thread-id>` in the
  task's `group_thread` field.
- A kanban task's acceptance gate can require a group signature: e.g.
  "deploy gate requires a signed thread in infra-operations G6." The kanban
  status only flips green when the group chairs sign the thread.
- This is the group-chat enforcement of team-architecture.md §3.2 (dependency
  gate) and §5.1 (acceptance gates).

---

## 6. Implementation Roadmap

### Phase 1: Core group chat (text only)
- Persistent channels for G1–G8 with @handle mention support.
- Thread nesting with stable thread IDs.
- Group → 1:1 DM escalation.
- Kanban task linking (task ↔ group thread).
- *Dependency gate:* requires team-architecture.md committed (§3.2) — i.e.
  this doc's push must precede Phase 1.

### Phase 2: File sharing in groups
- Code snippet blocks with syntax highlighting.
- Test result / trace upload (attach JSONL to a group thread).
- monitconfig.json and team-architecture.md committed artifacts
  are referenceable directly in-group via `@from <avatar>:<artifact>`.

### Phase 3: Bot-to-bot handoff protocol
- Formal "task transfer" message: a group thread can nominate a new owner
  avatar for a downstream track, with the explicit handoff (a) artifact loc,
  (b) acceptance gate, (c) dependencies, (d) new owner — exactly
  team-architecture.md §2.2.
- @claimerman's crash recovery triggers this protocol automatically.

### Phase 4: Cross-platform groups
- Bridge Hermes desktop groups to Telegram/Discord channels.
- Platform avatars (Telegram bot, Discord bot) join as group members.
- Cross-platform @mention routing (handle → platform dispatch).

---

## 7. Linkage to company architecture

This design is subordinate to and constrained by team-architecture.md:
- §2.1 (concurrency cap) → groups enforce the cap by NOT auto-spreading work;
  a group is created only when parallelism is genuinely needed, and the chair
  re-balances load (§2.2 transfer).
- §3 (dependency resolution) → group threads are the traceable edges
  (§5.2).
- §4 (monitoring protocol) → §4.1 check 5 (avatar overbook) is a group
  health signal; the dashboard renders it.
- §4.5 (monitconfig.json) → groups emit monitoring state to the config.
- §5 (acceptance gates) → group signatures are acceptance gates.

---

## 8. Revision
- v1.0 — authored @cto, staged via `company-arch` skill, pushed via
  @devops-engineer to `itsPremkumar/hermes-ai-company` docs/.
  Complete specification: 8 permanent groups + dynamic incident groups,
  full member rosters, 6 primary use cases, architecture requirements,
  4-phase roadmap.

Author: @cto
