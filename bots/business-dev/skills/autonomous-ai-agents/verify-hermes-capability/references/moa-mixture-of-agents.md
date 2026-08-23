# Hermes Mixture of Agents (MoA) — verified 2026-07-25 on this install

## The user's request that maps to this
"I want one input → asked to multiple different LLM models → ONE model combines every
model's best output into a single output." This is exactly MoA. Do NOT propose a custom
"LLM council" skill/CLI when `/moa` already ships — confirm via source first.

## What MoA is (from reading the source, not docs)
- One prompt is sent to **N reference models** run **in parallel** (`ThreadPoolExecutor`).
- Their outputs are gathered and passed to an **aggregator model** that **merges the best
  of each** into a single final answer.
- Supports **multiple iterations** (references → aggregator → references again → final
  aggregator), so the council refines rather than concatenates.
- Built-in PII/secret redaction on reference outputs (`agent/redact.redact_sensitive_text`
  + email/phone patterns) — safe to use on real conversations.

## Source of truth (file:line evidence)
- `hermes_cli/main.py:14941` — `moa_parser = subparsers.add_parser("moa", ...)`
  subcommands: `list|ls`, `configure|config [name]`, `delete|rm <name>`.
- `agent/moa_loop.py` (2,126 lines) — runtime; `ThreadPoolExecutor` gather
  (line 15 import, line 781 `results = [None]*len(reference_models)`), aggregator prompt,
  privacy filter, iteration handling.
- `hermes_cli/moa_cmd.py` — CLI picker (`_pick_slot`, `_model_options`, `_print_config`).
- `hermes_cli/moa_config.py` — `DEFAULT_MOA_PRESET_NAME`, `normalize_moa_config`,
  `coerce_privacy_filter` (modes: '' | 'display' | 'full').

## How to use
```
# In chat — prefix the question:
/moa Explain quantum entanglement simply

# Configure which models sit in the council:
hermes moa configure     # interactively pick reference models + aggregator
hermes moa list          # show current presets / active
hermes moa delete <name> # remove a preset
```
Reference models + aggregator are resolved from your **configured providers**, so the
**free-llm-router** models (`opencode:deepseek-v4-flash-free`, `hy3-free`,
`nemotron-3-ultra-free`, `kilocode:*` — see `config.yaml` `free-llm-router.models`)
and Ollama models plug straight in. **Zero cost.**

## Caveat (environment, not a code bug)
MoA needs the reference/aggregator endpoints reachable. On this box the local free-llm-router
at `http://127.0.0.1:17498/v1` was NOT listening (connection refused) during discovery, so a
live council couldn't dispatch until the router is up. The MoA machinery is fine; the upstream
free models just must be live. Verify with a quick `terminal` probe:
`curl -s http://127.0.0.1:17498/v1/models` (expect a JSON `data[]` list, not connection-refused).

## Other installed multi-model surfaces (for completeness)
- `delegate_task` subagents — can pin `delegation.provider`/`delegation.model` per subagent
  (parallel different models), but they don't auto-merge; you'd synthesize manually.
- `config.yaml` `fallback_model:` block — automatic failover on 429/503/timeout, NOT a council.
- MoA is the only built-in that does the "ask all, combine" pattern natively.
