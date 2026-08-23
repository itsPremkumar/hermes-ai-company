# Pitfalls log — Hermes skill authoring (from the prompt-refine build session)

Concrete failure transcripts and the fixes. Each is a thing that broke during a
real build; encode the fix, not the failure-as-constraint.

## 1. `python3` missing
- Symptom: script uses `python3`, run fails or JSON build step produces nothing.
- Fix: `PYBIN="$(command -v python || command -v python3 || echo python)"` and use
  `$PYBIN` everywhere. On this box `python` = 3.11.15, `python3` absent.

## 2. MSYS `/tmp` path translation
- Symptom: background `python /tmp/mock_refine.py` →
  `can't open file 'C:\tmp\mock_refine.py': No such file or directory`.
- Fix: write temp/test scripts to a Windows-native path under the user home,
  e.g. `C:\Users\<user>\AppData\Local\Temp\hermes-verify-*.py`, referenced with
  forward slashes.

## 3. Dead Ollama endpoint hangs
- Symptom: `hermes chat -q` blocks when config provider is `ollama-launch` and
  Ollama isn't running (it tries to launch/connect and waits).
- Fix: don't call `hermes chat` for the refine step. Use a direct
  OpenAI-compatible `curl --max-time 5` against the configured base_url; on empty
  RESP exit 2 (unreachable) fast. Never loop waiting on a dead local server.

## 4. OpenRouter free-model slug rotation (404)
- Symptom: `meta-llama/llama-3.1-8b-instruct:free` →
  `{"error":{"message":"This model is unavailable for free...","code":404}}`.
- Fix: resolve a live free slug at runtime:
  `GET https://openrouter.ai/api/v1/models`, filter
  `pricing.prompt==0 and pricing.completion==0`, prefer small instruct/text models
  (llama/qwen/mistral/gemma/phi). Verified-live this session:
  `meta-llama/llama-3.2-3b-instruct:free`, `meta-llama/llama-3.3-70b-instruct:free`,
  `qwen/qwen3-next-80b-a3b-instruct:free`.
- Reminder: free slugs churn; never hardcode one as the only option.

## 5. 429 rate-limit is transient, not fatal
- Symptom: `{"error":{"code":429,"metadata":{"raw":"...temporarily
  rate-limited upstream..."}}}`.
- Fix: retry with `sleep 6` backoff AND fall back across several free slugs before
  giving up. Don't treat 429 as a hard failure.

## 6. Local skill folder NOT indexed by `hermes skills list`
- Symptom: folder at `~/.hermes/skills/prompt-refine/` with valid `SKILL.md`
  (name/version/description/triggers/allowed-tools) does NOT appear in
  `hermes skills list`; `hermes skills inspect prompt-refine` → "No exact match";
  `skill_view(name='prompt-refiner')` → "not found". `git init` in the folder did
  NOT help. `hermes skills install <local-path>` →
  "Could not fetch '<path>' from any source" (expects URL/hub id).
- Conclusion: in this install, only hub/registry-installed skills are indexed.
  Arbitrarily-dropped local folders are not discovered.
- Workarounds:
  - Agent-inline execution ALWAYS works: the agent reads `SKILL.md` and follows it.
  - To make it auto-discoverable/triggerable: publish to a git repo and run
    `hermes skills install <repo-url>` (local paths rejected).
- Don't burn time reverse-engineering discovery internals.
