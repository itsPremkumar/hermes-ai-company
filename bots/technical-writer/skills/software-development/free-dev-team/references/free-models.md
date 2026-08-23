# Free models for the dev team

## OpenRouter free coder models (reuse the OpenClaw key)
The OpenClaw config at `~/.openclaw/openclaw.json` contains an OpenRouter key
(`sk-or-v1-...`). Reuse it — do NOT print it. Extract programmatically:
```python
import re, os
key = re.search(r"sk-or-v1-[A-Za-z0-9]+", open(os.path.expanduser("~/.openclaw/openclaw.json")).read()).group(0)
```
Free coder models (rotate; verify at https://openrouter.ai/models?filters=free):
- `qwen/qwen2.5-coder-32b-instruct:free`  (recommended)
- `mistralai/mistral-7b-instruct:free`
- `meta-llama/llama-3.1-8b-instruct:free`

Hermes itself runs on `tencent/hy3:free` (already wired in OpenClaw).

## OpenHands config.toml shape
```toml
[llm]
model = "qwen/qwen2.5-coder-32b-instruct:free"
base_url = "https://openrouter.ai/api/v1"
api_key = "<sk-or-...>"
temperature = 0.2
top_p = 0.95
[agent]
max_iterations = 30
max_budget_per_task = 0.05
[core]
workspace_base = "C:/Users/PREM KUMAR/openhands-workspace"
```

## Notes
- Free tiers are rate-limited and rotate models — pin a model but have a fallback.
- `max_budget_per_task` caps spend (free tier = ~$0, but keep the guard).
- Local Ollama (e.g. `qwen2.5-coder:7b`) is an alternative if Docker/SSH runtime is up
  and the box has ~4GB VRAM — but this 6GB-RAM box is too tight for local LLM + build.
