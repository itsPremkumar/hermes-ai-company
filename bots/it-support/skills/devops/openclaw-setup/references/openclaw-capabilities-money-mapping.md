# OpenClaw capabilities & money-earning mapping (verified 2026-07-14)

Condensed from live inspection of `OpenClaw 2026.7.1` on this host. Companion
to the Pitfall 9–11 section in SKILL.md.

## Verified capability catalog (`openclaw capability list`)
| Capability id | Transports | Internet? | Notes |
|---|---|---|---|
| `web.search` | local | **Yes** | Real provider-backed web search |
| `web.fetch` | local | **Yes** | Fetch URL content |
| `model.run` | local, gateway | via OpenRouter | `tencent/hy3:free` (reasoning model) |
| `image.generate` / `edit` / `describe` | local | needs key | Needs an image provider configured |
| `video.generate` / `describe` | local | needs key | Needs a video provider configured |
| `tts.*` (convert/voices/providers/enable/…) | local, gateway | — | Text-to-speech surface |
| `audio.transcribe` | local | — | Speech-to-text |
| `embedding.create` | local | — | Embeddings |
| `model.list` / `model.inspect` / `model.providers` | local | — | Catalog introspection |

**Takeaway:** OpenClaw has genuine internet (search/fetch), media generation,
and a working Telegram bot. Its agent, however, **cannot write files** (no
file/exec tool).

## Live channel health (verified)
```
openclaw channels status --probe
→ Telegram default: enabled, configured, running, connected,
  transport: polling, bot:@prem123aibot, token:config, works
```
Telegram is the one LIVE, connected channel. Everything else (WhatsApp/Discord/
Slack/…) requires its own pairing/creds before it works.

## Delegating a task to the agent (proven walkthrough)
1. `openclaw agents list` → note agent id (e.g. `main`).
2. Write the task to a **Windows path**, e.g. `C:\one\oc_task.txt`
   (do NOT use `/tmp/...` — Node resolves it to `C:\tmp\...` → ENOENT).
3. Run:
   ```bash
   openclaw agent --agent main \
     --message-file "C:\one\oc_task.txt" --json --timeout 200
   ```
4. Read `finalAssistantVisibleText` from the JSON. The agent returns the
   generated artifact but **will not write it**. Persist with Hermes
   `write_file`, then verify with `ls`.

## Mapping into the money-earning stack (vs `money-engine`)
`money-engine` already generates content via Hermes crons (18 pipelines:
affiliate, Gumroad, Fiverr, POD, SEO Q&A, tools hub, newsletter, research
scanner). Its honesty rule: ~90% autonomous, never "guaranteed income", agent
DRAFTS but cannot auto-post — the user does the posting.

**Where OpenClaw genuinely helps:**
- **Telegram delivery layer** — push `_promo-drafts.md` / `_newsletter.md`
  drafts to you/a channel so you only approve+forward. Closes the
  "can't auto-post" gap without violating the honesty rule.
- **Phone-controlled front-door** — enable `@openclaw/admin-http-rpc` and wire
  its webhooks/cron to trigger Hermes crons; you command the system from your
  phone. Actual build/publish stays with Hermes.

**Where OpenClaw is redundant or cannot act:**
- Research / generation / file writes / `git push` → better done by Hermes
  (faster, reliable, and it can actually write to disk). OpenClaw's
  `web.search`/media gen duplicate what Hermes already covers.
- **Cannot:** persist files (agent has no file/exec), touch `config.json`
  affiliate IDs, open paid store accounts, do KYC/GST/tax, or run
  crypto/arbitrage/"automatic money" bots (money-engine explicitly rejects
  these — do NOT build them on OpenClaw either).
- **Low-RAM caution:** this ~6 GB box runs hot; running the gateway + Hermes +
  18 money crons together can starve RAM and wedge things. Budget processes.
