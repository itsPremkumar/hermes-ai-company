# 13 — Feature Activations (2026-08-22)

## Plugins enabled (verified via `hermes plugins list`)
| Plugin | Purpose for the company |
|---|---|
| telegram-platform | Phone escalation channel: watchdog alarms + needs-you reach the owner's phone |
| web-ddgs | DuckDuckGo keyless search — research redundancy lane 2 |
| web-brave-free | Brave free search — research redundancy lane 3 |
| disk-cleanup | Automated disk/RAM hygiene on this resource-starved box |
| security-guidance | Security guidance injected into agent context |

## MCP servers enabled
| Server | Use |
|---|---|
| vercel | site deploys (pre-existing) |
| hugging_face | models/datasets/Spaces access (OAuth on first use) |

## Gateway event hook
`hooks/build-qa-auto/` (also in `scripts/hooks/`) — logs every agent:end to
`ops-qa-log.txt`; foundation for auto-QA triggering on build completion.

## Notes
- All plugins activate on session start; gateway restarted to load them.
- Telegram needs bot-token setup with @BotFather to go live [HUMAN STEP].
- hugging_face OAuth fires in browser on first tool use.
