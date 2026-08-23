---
name: hermes-remote-mcp
description: "Configure a REMOTE HTTP + OAuth 2.1 MCP server in Hermes (Stripe is the canonical case, but the pattern covers Linear/Sentry/Asana/Figma/Atlassian etc.) with least-privilege per-server tool filtering. Covers the VERIFIED config schema (auth oauth vs static bearer, server-level include/exclude, include-wins precedence, correct nesting), the headless-OAuth loopback trap, and a reusable verified agentic-payment provider comparison. Use when the user wants Hermes to talk to a hosted MCP server, asks about Stripe or agentic payments in Hermes, or wants read-only or least-privilege agent access to a SaaS."
tags: [hermes, mcp, oauth, remote-mcp, stripe, agentic-payments, least-privilege, tool-filtering]
---

# Hermes Remote / OAuth MCP Server Config (+ least-privilege filtering)

## When to use
- User wants Hermes to connect to a **hosted MCP server** (Stripe `https://mcp.stripe.com`, Linear, Sentry, Asana, Figma, Atlassian, etc.) — not a local stdio server.
- User asks about **agentic payments** — "can Hermes pay / charge / refund via Stripe / PayPal / Square / Adyen".
- User wants **read-only or least-privilege** agent access to a SaaS (see payments but never refund/delete/transfer).
- User pastes an MCP `mcp_servers:` YAML block — VERIFY the schema against this skill before trusting it (AI-pasted configs routinely nest keys wrongly; see Pitfalls).

NOTE: for **local stdio** MCP servers (your own Python/Node server, OpenSpace, Ruflo), use `hermes-mcp-registration` instead. This skill is for **remote HTTP** servers.

## Verified config schema (from Hermes MCP docs, cross-checked 2026-07-20)

Remote servers go under `mcp_servers:` in `~/.hermes/config.yaml`. The shape:

```yaml
mcp_servers:
  stripe:
    url: "https://mcp.stripe.com"
    auth: oauth          # hosted servers like Stripe need OAuth 2.1, NOT a static bearer
    # Per-server tool filtering — include/exclude are DIRECT keys under the server entry:
    include: [list_payments, list_customers, list_invoices]   # whitelist form
    # OR
    exclude: [delete_customer, refund_payment, create_transfer] # blacklist form
    resources: false     # optionally disable MCP resource/prompt utility wrappers
    prompts: false
```

### Critical schema facts (verified)
1. **`include` / `exclude` are DIRECT keys under the server entry** — NOT nested under `tools:`. AI-pasted configs that write `tools: exclude: [delete_customer]` are WRONG and likely won't match the schema. `tools:` in the real docs is reserved for `resources:` / `prompts:` toggles only.
2. **`auth: oauth` for hosted servers.** Stripe/Linear/Sentry/Asana/Figma/Atlassian are OAuth-2.1-only per the docs. A static `headers: Authorization: "Bearer ***"` is the generic fallback shown in a mixed example; for Stripe use `auth: oauth`.
3. **Precedence: `include` wins.** If a server has both `include: [create_issue]` and `exclude: [create_issue, delete_issue]`, the `include` list wins — `create_issue` stays enabled, `delete_issue` is excluded. So if you want a strict whitelist, use ONLY `include` (cleaner + safer).
4. **Filtered-out entirely → no empty toolset.** If your config excludes/omits all callable tools AND disables resources/prompts, Hermes just won't register that server (clean). No crash.
5. **Tool NAMES are discovered at install, not hardcoded.** `hermes mcp configure <name>` probes the server and shows a checklist of the REAL tool names. Don't invent names like `create_transfer` — let the probe enumerate them, then pick.

### OAuth flow reality
- On first connect Hermes prints an authorize URL, opens a browser if possible, and waits for the OAuth callback on a local loopback port.
- Tokens cached at `~/.hermes/mcp-tokens/<server>.json` (perms `0o600`); reused silently until refresh fails.
- **Headless / remote-host trap:** if Hermes runs on a different machine than your browser, the loopback callback can't reach your laptop. Two fixes: (a) do the first OAuth from a machine with a browser, or (b) supply your own OAuth client (`auth: oauth` + `client_id`/`client_secret` from the provider console) + a reachable `redirect_uri`.

## Canonical worked example: Stripe in Hermes

Stripe is the **most mature agentic-payment MCP** (verified 2026-07-20):
- Hosted remote MCP at `https://mcp.stripe.com`, OAuth 2.1, zero infra.
- First-party `stripe/ai` repo (1.7k star, synced 2 days ago) ships SDKs (`@stripe/ai-sdk` Vercel AI SDK; `@stripe/token-meter` native OpenAI/Anthropic/Gemini billing) + plugins for Claude Code / Codex / Cursor / Grok Build + "agent skills".
- The MCP toolset INCLUDES money-movement tools (that's why `refund_payment`/`delete_customer` are real and filterable). So **tool filtering is your safety layer**.

### Read-only / least-privilege (your security model)
```yaml
mcp_servers:
  stripe:
    url: "https://mcp.stripe.com"
    auth: oauth
    include:          # strict whitelist — only these, nothing else
      - list_payments
      - list_customers
      - list_invoices
      - list_subscriptions
```
This gives: receive payment notifications, view payments/customers/invoices/subscriptions, build revenue reports — and CANNOT refund, transfer, delete, or spend.

### Agentic-but-least-privilege (agent can collect, but not destroy)
```yaml
mcp_servers:
  stripe:
    url: "https://mcp.stripe.com"
    auth: oauth
    exclude:          # allow everything EXCEPT the dangerous mutators
      - refund_payment
      - delete_customer
      - create_transfer
```
Prefer the strict `include` whitelist when you can enumerate the read tools; prefer `exclude` only when the tool list is large/volatile.

## Verification (prove it's wired)
- `hermes mcp configure stripe` → probes the server, lists real tools, interactive checklist. Only checked tools land in `tools.include`.
- `hermes mcp test` (or the equivalent per-server test) → "Connection succeeded" + tool count. Re-run after editing config.
- If the probe fails (server unreachable / OAuth not completed), install still succeeds using the manifest's `tools.default_enabled` or no filter; refine once reachable.
- Confirm in-session: ask Hermes to "list recent Stripe payments" — if it can and the excluded tools are absent from its tool list, the filter is live.

## Pitfalls
- **AI-pasted "official docs" are often wrong on schema.** A ChatGPT-generated Stripe MCP config (carried `utm_source=chatgpt.com` tracking) led with a static bearer token AND nested `tools: include:` under the wrong key. Real docs: Stripe = OAuth, filters are server-level keys. Always re-pull the live Hermes MCP page before acting.
- **Don't trust star/maturity claims from pasted comparisons.** Verify on GitHub: `curl -s 'https://api.github.com/repos/<owner>/<repo>' | python -c 'import sys,json;d=json.load(sys.stdin);print(d.get("stargazers_count"),d.get("pushed_at"))'`.
- **`search_files` chokes on spaces in Windows paths** (e.g. `C:\Users\PREM KUMAR\...`). Use `terminal` with `grep` (or `find` + forward-slash MSYS paths) instead when the path has spaces.
- **`python3` is missing on this box; use `python`** (hermes venv) — `python3` resolves to nothing. `curl` exists at `mingw64/bin/curl`.
- **Read-only ≠ safe by default.** A remote MCP that exposes `refund_payment` is dangerous unless you explicitly `exclude`/`include` it away. Least-privilege is a deliberate config step, not a default.

## Reusable knowledge bank
- `references/agentic-payment-providers.md` — verified comparison of Stripe / PayPal / Square / Adyen agentic-payment support (GitHub stars, last-commit, hosted-MCP vs self-hosted, can-the-agent-move-money), with the source signals that back each verdict. Use when the user asks "which payment gateway supports agentic payments" or "compare Stripe vs PayPal for agents".

## Related
- `hermes-mcp-registration` — registering a LOCAL stdio MCP server (different machine than this remote-OAuth skill).
- `mcp-client-build` / `mcp-server-build` / `mcp-server-verification` — building & verifying Python MCP clients/servers.
- `research/verify-ai-claims` — verify pasted "official docs" configs before trusting them (the Stripe chatgpt.com case lives there too).
