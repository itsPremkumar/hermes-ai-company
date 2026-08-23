# Gap-Validation Before Build — prove a product gap is REAL, not already solved

Use this when the user says "find the best problem to build", "is this gap already taken",
"should we build X as open source". The goal: avoid rebuilding an existing mature project.
Born from a 2026-07-18 session where the agent proposed "SAMM — shared agent memory mesh"
and the user correctly demanded proof the gap wasn't already filled.

## The 4-step validation recipe
1. **Topic-count scan (proxy for "how crowded is this space")**
   Navigate `https://github.com/topics/<topic>` and read the "Here are N public repositories"
   line + the top 3 repos' stars. Low count + tiny top-repo stars = nascent/unsolved.
   - `ai-agents` = 55,523 repos (SATURATED)
   - `agent-memory` = 1,992 (crowded but per-agent silos)
   - `mcp` = 52,242 (tool protocol, SOLVED)
   - `agent-to-agent` = 272 (nascent — messaging, not shared state)
   - `memory-server` = 24 (the REAL candidate space — small!)
   - `shared-memory` = 793 BUT FALSE FRIEND (OS IPC: iceoryx, cpp-ipc, ucx)
2. **False-friend detection** — a topic name that SOUNDS like your gap may be a different
   domain. Always open the top repos and read their descriptions. `shared-memory` is the
   classic trap (process IPC, not agent memory). `knowledge-graph` = code-to-graph
   visualizers (graphify 90k★, Understand-Anything 75k★), NOT memory substrates.
3. **Competitor-maturity check** — for the nearest 2-3 candidates, inspect: stars, last
   commit date, issue/PR count, license (MIT vs open-core), and whether it is
   SINGLE-AGENT / SINGLE-USER vs truly MULTI-AGENT SHARED.
   - mcp-knowledge-graph (877★): Claude-only, single agent.
   - Dakera-AI (16★, open-core): self-hosted agent memory server w/ namespaces+vectors+KG,
     but EMBRYONIC (4 issues, 1 PR, features stalled 2-4 mo). Closest to the gap; NOT mature.
   - sqlite-memory-mcp (12★): single user.
4. **Decision rule**: if no candidate is (a) adopted (>>1k★ or real usage), (b) truly
   multi-agent/shared, (c) MIT/Apache (not open-core), then the gap is OPEN. Build — but
   DIFFERENTIATE (state your wedge: e.g. conflict detection, fully-local embeddings, MIT).

## GitHub search note
`github.com/search?q=...` HTML often returns "Too many requests" (rate limit) from this host.
Prefer the Topics browse path above, or the API with `User-Agent` + sleeps (see parent
skill PITFALL). Browser-navigate Topics pages work reliably here.

## Wedge template (when you DO build)
State explicitly what you do that existing attempts don't:
1. Truly multi-agent shared (namespace + agent_id + shared RW) — not single-user.
2. Cross-agent conflict detection — nobody does this.
3. Fully local, zero-cost embeddings (no paid API) — vs mem0's API default.
4. MIT, not open-core.
5. Adopted by YOUR stack first (MCP clients).

## Evidence captured 2026-07-18 (verified live)
- Gap "shared persistent agent memory" = REAL, largely UNSOLVED at maturity.
- Nearest competitor Dakera-AI is open-core + stalled; mem0/cognee/supermemory are per-agent.
- Conclusion: valid to build a zero-cost, MIT, conflict-aware, multi-agent memory mesh.
