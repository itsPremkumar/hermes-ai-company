# Agent Marketplace Research (2026-07-13)

Discovered during the 31-ClawHub-skills publishing campaign. Direct research via
GitHub topic pages, browser inspection, and official website analysis.

## HYRVE AI — The First AI Agent Marketplace

**URL**: https://hyrveai.com  
**GitHub**: https://github.com/ertugrulakben/HYRVE-AI (20★, MIT)  
**Community**: 5,750+ agents and clients  
**Commission**: You keep 85%, HYRVE takes 15%

### Key features
- **Dual Payment**: Stripe (USD/EUR), USDT (TRC-20, ERC-20), stablecoin via MPP
- **48-hour Escrow**: Client reviews work before payment is released
- **Self-Registration**: Agent reads `hyrveai.com/skill.md` and registers in 30s
- **A2A Trading**: Agents hire other agents autonomously
- **Reputation System**: Verified customer ratings and agent profiles
- **Machine Payments (MPP)**: Stablecoin payments at 1.5% fees

### How it works
1. Deploy your agent (register via API or skill.md)
2. Agent gets hired (browses job listings, bids on tasks)
3. Agent earns (85% commission, paid via Stripe/USDT)

### Sample jobs live on platform
- "Translate 500 Product Descriptions" — $75
- "Code Review for React Project" — $0.05/file

### Powered by CashClaw
MIT licensed v1.7.0 middleware. One command: `npx cashclaw init`
Gives agent 13 skills, connects to Stripe, earns on HYRVE.
Guard runtime: hard cost cap, recursion kill, tool firewall.

### Relevance to our 31 ClawHub skills
Our skills map directly to HYRVE service offerings:
- `doc-extractor` → document processing service
- `secret-scanner` → security audit service
- `codebase-inspection` → code review service
- `json-tools` → data processing service
- `youtube-content` → content repurposing service
- `web-research` → research agent service
- `maps-cli` → geocoding/mapping service

---

## The Colony — AI Agent Forums + Marketplace

**URL**: https://thecolony.cc  
**GitHub (skill)**: https://github.com/TheColonyCC/colony-skill (5★, Shell)  
**GitHub (agent template)**: https://github.com/TheColonyCC/colony-agent-template

### What it offers
- Topic-based forums (colonies) with threaded discussion
- Direct messages between agents and humans
- **Marketplace**: paid tasks and document sales
- Upvote/downvote, reputation system
- 20+ colonies covering general, findings, meta, analysis, etc.

### Agent registration
- Agents self-register via the agent flow on the site
- OpenClaw skill exists for direct integration

---

## AgenC — Agent Hiring Protocol (Solana)

**URL**: https://github.com/tetsuo-ai/AgenC (190★, 1,460+ commits)  
**Model**: Free protocol + marketplace where AI agents get hired/paid on Solana

### Architecture
- Zero-knowledge proofs for work verification
- Solana mainnet for settlement
- Developer docs workspace at agenc.io
- Very active (merged 1,570+ PRs)

---

## Agoragentic — Cross-Framework Agent Commerce

**URL**: https://github.com/rhein1/agoragentic-integrations (23★)  
**Model**: Adapters for 50+ agent frameworks → USDC settlement on Base

### Supported frameworks
LangChain, CrewAI, AutoGen, OpenAI Agents, MCP, A2A, x402, smolagents
Monorepo + npm packages for MCP, Micro ECF, and local readiness tooling.
Route a task with `execute()`, get a receipt, settle in USDC.

---

## ai-sns — OpenClaw Hermes AI Agent Social Network

**URL**: https://github.com/ai-sns/ai-sns (319★, JavaScript)  
**Model**: 3D Google Maps-based agent social network using A2A protocol
Connects OpenClaw and Hermes agents worldwide.

---

## AladdinChat — Agent DM Network

**URL**: https://github.com/OpenCloserOrg/AladdinChat (6★, JavaScript)  
**Model**: Agents DMing each other with human-in-the-loop
For OpenClaw agents to connect with various agents.

---

## GitHub topic pages used in research

- https://github.com/topics/agent-marketplace — 70 repos
- https://github.com/topics/ai-agent-marketplace — 40 repos
- https://github.com/topics/agent-social-network — 24 repos
