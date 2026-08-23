# Agentic-Payment Gateway Comparison (verified 2026-07-20)

"Agentic payments" = an AI agent that can actually INITIATE / CAPTURE money movement
via tools (not just read history). Verified live from GitHub + Hermes MCP docs.

## Verdict at a glance

| Provider | First-party agent toolkit? | Can agent MOVE money? | Transport / setup | Maintenance signal (live) |
|---|---|---|---|---|
| **Stripe** | YES `stripe/ai` + hosted `mcp.stripe.com` | YES (create intent, capture, refund — all filterable) | **Hosted remote OAuth MCP** (zero infra) | Strong — 1.7k star, synced 2 days ago |
| **PayPal** | YES `paypal/agent-toolkit` (188 star, Apache-2.0) | YES (`pay_order`, `create_refund`, invoices, subs) | Self-hosted MCP / framework SDK (TS + Py) | Weaker — MCP server MOVED OUT to a separate repo 8 months ago (#76); README describes tools but no in-repo MCP server |
| **Square** | NO first-party toolkit | WARN Only by hand-wiring their REST API | You build it | No agent tooling — only `goose-vscode` (Block Goose editor ext., 34 star) under the org |
| **Adyen** | NO confirmed first-party agent/MCP toolkit | WARN REST API only, agent must be hand-built | Manual | No agent tooling found |

## Detail

### Stripe — most mature, only true drop-in
- Repo `stripe/ai`: "one-stop shop for building AI-powered products on Stripe." 1.7k star, 310 forks, MIT license, last commit **2 days ago** at time of check.
- Hosted remote MCP server at `https://mcp.stripe.com` — OAuth 2.1, no server to host. Docs: "You can also build autonomous agents with MCP as well."
- SDKs: `@stripe/ai-sdk` (Vercel AI SDK), `@stripe/token-meter` (native OpenAI/Anthropic/Gemini billing).
- First-party plugins: Claude Code (`claude plugin install stripe@claude-plugins-official`), Codex (`codex plugin add stripe@openai-curated`), Cursor (`/add-plugin stripe`), Grok Build (`grok plugin install stripe --trust`).
- Agent skills collection (best-practice instructions).
- MCP toolset includes WRITE/money-movement tools — that's exactly why per-server `exclude: [refund_payment, delete_customer]` is the documented safety mechanism.

### PayPal — real but self-hosted, less maintained
- Repo `paypal/agent-toolkit`: 188 star, Apache-2.0, 105 forks. Latest commit **8 months ago** MOVED the MCP server code to a separate repo (#76) — so this repo now holds SDKs, not an in-repo MCP server.
- Frameworks: OpenAI Agent SDK, LangChain, Vercel AI SDK, MCP. TypeScript + Python.
- Tools exposed: invoices (create/list/get/send/remind/cancel/qr), payments (`create_order`, `get_order`, `pay_order`, `create_refund`, `get_refund`), disputes, shipment tracking, catalog, subscriptions, reporting/insights (`list_transactions`, `get_merchant_insights`).
- Broader business-object coverage than Stripe's MCP, but maturity gap (stale, MCP split out).

### Square — no agent-native path
- No `square/agent-toolkit`. Org `square` repos matching "agent" = only `goose-vscode` (a Block Goose editor extension, 34 star).
- To make Square agentic you must hand-wrap its REST API in your own MCP server. Doable, not out-of-box.

### Adyen — no agent-native path
- No first-party agent toolkit / MCP server found. REST API only; agent must be hand-built.

## How to verify a provider's agent support (recipe)
```bash
# stars + last push (proves it's alive)
timeout 20 curl -s 'https://api.github.com/repos/<owner>/<repo>' | \
  python -c 'import sys,json;d=json.load(sys.stdin);print(d.get("stargazers_count"),d.get("pushed_at"))'
# does an MCP server actually live IN the repo, or was it moved out?
# browse repo root + recent commits for "mcp" / "moved to separate repo"
```
Watch for the trap that bit PayPal: a toolkit repo that *used* to contain an MCP server but had it split out — the README still describes MCP tools while the server lives elsewhere or is unmaintained.

## Bottom line for a secure Hermes setup
- **Read-only, zero-infra:** Stripe hosted OAuth MCP + `include:` whitelist is the cleanest, best-maintained option and the ONLY drop-in (others need a self-hosted MCP server).
- **Agentic (agent can collect payments) but least-privilege:** Stripe again strongest; PayPal a secondary self-hosted option. Square/Adyen require custom MCP wrapping of their REST APIs.
- In ALL cases, explicit per-server tool filtering (`include`/`exclude`) is the cross-cutting safety layer — a remote MCP exposing `refund_payment` is dangerous until you filter it away.
