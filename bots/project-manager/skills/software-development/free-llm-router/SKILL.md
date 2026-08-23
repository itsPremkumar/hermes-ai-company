---
name: free-llm-router
description: Build and run a ZERO-COST, no-signup, OpenAI-compatible LLM router/proxy with automatic fallback across free providers, 24/7 supervision, and Windows startup autostart. Use when the user wants a local proxy that aggregates completely-free LLM endpoints (Pollinations, OpenCode, DuckDuckGo, MiMo, Kilo, etc.) so any OpenAI-compatible client (Hermes, etc.) can list and select them from its model picker.
triggers:
  - "free LLM router"
  - "no-signup LLM proxy"
  - "zero-cost model provider"
  - "connect free aggregator models"
  - "make hermes use free models"
  - "free models not updating in hermes ui"
  - "list all the free model providers"
---

# Free LLM Router / Proxy (ZERO-COST, NO-SIGNUP)

Aggregates completely-free, anonymous LLM endpoints behind ONE local
OpenAI-compatible server (`/v1/chat/completions`, `/v1/models`, `/health`)
with automatic fallback. Built for the user's hard rule: **$0, no API keys,
no signup**. Canonical implementation lives at `C:\one\free-llm-router`
(stdlib + `aiohttp`; no other pip deps).

## When to use
- User wants to use free models (Pollinations/OpenCode/DDG/MiMo/Kilo) from
  any OpenAI-compatible client, especially the **Hermes model picker UI**.
- User says "connect all the completely free endpoint provider list" / "I
  should be able to select all these models and providers from the UI itself".
- User wants a 24/7 local proxy with proper error handling + fallback.

## Architecture (proven)
- **Package** `free_llm_router/`: `providers.py` (registry, `preference` order),
  `catalog.py` (`provider_id -> [free model ids]`), `router.py` (`chat()` with
  fallback chain + `check_providers()` / `check_models()` live probes),
  `backends.py` (openai-compatible caller + custom shims), `http.py` (resilient
  client, timeout+1 retry, maps errors to typed exceptions), `errors.py`
  (`RouterError` -> `ProviderAuthError`/`ProviderUnreachableError`/
  `ProviderBadResponseError`/`NoHealthyProviderError`), `server.py` (aiohttp).
- **`/v1/models` advertises every catalog model as id `provider:model`**
  (e.g. `pollinations_text:openai-fast`) PLUS a catch-all `free` model that
  auto-picks a healthy provider. This is what makes Hermes's UI list them all.
- **`chat()` fallback**: tries `provider` if given (no fallback unless
  `fallback=True`), else tries providers in `preference` order until one
  returns text. 401/403/429/timeout/empty -> next. All fail -> raise
  `NoHealthyProviderError` (never hang, never return garbage).
- **24/7**: `run_server.py` supervisor = auto-restart on crash, single-instance
  PID guard, rotating logs (`logs/server.log`, `logs/supervisor.log`).
- **Windows autostart**: `autostart.bat` + a `.vbs` that drops a
  `free-llm-router.lnk` into the Startup folder (see `references/windows-ops.md`).

## Build order
1. `providers.py` + `catalog.py` (seed from public `noAuth`/`anonymousFallback`
   free-provider lists — but VERIFY LIVE; see pitfall below).
2. `errors.py`, `http.py`, `backends.py`, `router.py` (fallback + probes).
3. `server.py` (aiohttp, advertise `provider:model` ids).
4. `run_server.py` supervisor + `autostart.bat` + startup `.vbs`.
5. `tests/test_router.py` (offline registry checks + live probe, skippable via
   `SKIP_LIVE=1`).
6. Wire client (Hermes `config.yaml`) to `http://127.0.0.1:<port>/v1`.

## CRITICAL pitfalls (this session cost many turns — do NOT repeat)
### P1 — `patch` tool can corrupt a function signature
Editing a module with `patch` while anchoring near a `def` line can silently
DROP lines. In this session two corruptions happened:
- Removed `from .backends import complete` -> every call failed with
  `name 'complete' is not defined`.
- Deleted the `prompt` param from `chat()` -> `chat() got multiple values for
  argument 'provider'`.
**Fix/workflow**: after any edit to a server module, (a) re-read the function
to confirm the signature is intact, (b) run `python -c "import free_llm_router"`
to catch import/syntax errors, (c) **kill the running server AND its supervisor
before relaunching** (P2) or you will test STALE bytecode and chase ghosts.

### P2 — Zombie supervisor serves stale code
A supervisor respawns its child on exit. `taskkill` on the child PID just lets
it respawn with OLD code. Symptom: you "fixed" `chat()` but `/v1/chat/completions`
still returns the old error.
**Fix**: kill by the listening port, confirm free, relaunch:
```
for p in $(netstat -ano 2>/dev/null | grep ':17498' | grep LISTENING | awk '{print $5}'); do taskkill /PID "$p" /F; done
sleep 2; netstat -ano | grep ':17498' | grep LISTENING || echo "FREE"
```
If a supervisor keeps respawning, kill the supervisor too:
`wmic process where "CommandLine like '%run_server%'" get ProcessId` then kill.

### P3 — MSYS mangles `taskkill //PID`
In git-bash, `taskkill //PID 13976 //F` errors ("Invalid argument"). Use SINGLE
slash: `taskkill /PID 13976 /F`. Or `cmd //c "taskkill /PID 13976 /F"`.

### P4 — VBS startup shortcut: `link.Path` is READ-ONLY
`WScript.Echo link.Path` throws "Object doesn't support this property or
method: 'path'". The `.lnk` IS still created. Use `link.FullName` if you must
print, or just don't echo. (See `references/windows-ops.md`.)

### P5 — "no-auth" provider lists lie (geo/region)
Public aggregator lists flag many providers `noAuth:true`, but from this host (India IP) most
are 401/403/geo-blocked. **Never trust the flag — live-probe.** Build the router
to use only what actually answers anonymously *from where it runs*. As of
2026-07-20 from India, `pollinations_text` (`text.pollinations.ai`) AND
`opencode` (zen, using the real `-free` model ids — see P7) both worked; several
others were blocked. **A provider looking "blocked" may just have wrong model
ids (P7) — always live-probe its `/models` + a real chat before writing it off.**
Re-verify with `references/provider-probe.md` script — status changes by
region/IP. (See `references/provider-probe.md`.)

### P7 — A provider's "401 / not working" is often WRONG MODEL NAMES, not a blocked endpoint
A free provider can return `401`/error not because the endpoint needs a key or is
geo-blocked, but because you called a **model id that isn't in its free tier**.
In this session OpenCode Zen (`https://opencode.ai/zen/v1/chat/completions`) was
marked "401s from this host / needs key regionally" — WRONG. The endpoint is
keyless (HTTP 200, `cost:"0"`); the catalog just had made-up model ids
(`kimi-k2.6`, `gpt-5`, `claude-opus-4-6`) that don't exist in the free plan.
**Before concluding a provider is dead, always GET its `/models` endpoint and use
the real ids.** For OpenCode Zen the free-tier models all end in `-free` (plus a
stealth one), verified working keyless 2026-07-20:
```
curl -s https://opencode.ai/zen/v1/models | python -c "import sys,json;[print(m['id']) for m in json.load(sys.stdin)['data']]"
# free-tier: deepseek-v4-flash-free, hy3-free, mimo-v2.5-free,
#            nemotron-3-ultra-free, north-mini-code-free, big-pickle (stealth)
```
Test a real chat before trusting the catalog:
```
curl -s https://opencode.ai/zen/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash-free","messages":[{"role":"user","content":"Say PONG"}],"max_tokens":10}'
```
Corrects P5: from India, BOTH `pollinations_text` AND `opencode` (zen, `-free`
ids) answer anonymously — not just Pollinations. If a user shows a screenshot of
the models they actually have in a provider's UI, match your catalog ids to that
screenshot, then confirm against the live `/models` list.

### P6 — `/health` live-probes ALL providers -> slow
`GET /health` calls `healthy_providers()` which probes every provider (~30s).
Don't give curl a 10s timeout on `/health`; use 60-70s. The chat endpoint itself
is fine (~5-40s per call).

### P8 — SEQUENTIAL health probe starves slow-but-alive providers (make it concurrent)
A sequential `healthy_providers()` loop with an overall deadline probes providers
in `preference` order and lets early/dead ones burn the time budget — so a
genuinely working provider later in the list (e.g. `opencode`, which answers in
~2-7s) is never reached before the deadline and is falsely reported DOWN.
Symptom: `/health` shows only `pollinations_text` even though a direct chat to
`opencode:hy3-free` returns 200. **Fix: probe ALL providers concurrently** with a
`ThreadPoolExecutor` (one worker per candidate), each capped at `timeout`, the
whole scan bounded by `overall` via `as_completed(futs, timeout=overall)`, then
re-sort results back into `preference` order. Also pick a FAST probe model as the
provider's `default_model` (e.g. `hy3-free`, ~7s) — a slow *reasoning* model like
`deepseek-v4-flash-free` can exceed an 8s probe cap AND return its answer in
`reasoning_content` with empty `message.content` at low `max_tokens`, both of
which make a live provider look dead. Bump probe `timeout` to ~20s and `overall`
to ~60-75s. Health can still flap on network jitter; the source of truth is a
real chat round-trip, so verify routing with an actual `/v1/chat/completions`
call, not `/health` alone.

### P15 — Free providers throttle HARD on concurrency; grade coding capability by EXECUTING output
Two durable facts about the free tier that shape how you test and use the router:
- **Pollinations rate-limits to 1 concurrent request per IP.** A second in-flight
  request returns `HTTP 429 {"error":"Queue full for IP: <ip>: 1 requests already
  queued (max: 1)..."}`. This bites the instant you run a parallel probe/benchmark
  WHILE another call is live (e.g. the health scan, or two curls at once). It also
  means the router is fine for one interactive client but NOT for parallel coding
  agents hammering it. Mitigations to offer the user: add a local **Ollama**
  provider (unthrottled backend), and/or **429 retry-with-backoff + provider
  rotation** in `httpclient`/`router` so a 429 rolls to the next healthy provider
  instead of failing. Run any multi-request benchmark SEQUENTIALLY, one call at a
  time, or you measure the throttle, not the model.
- **Grade coding capability by running the generated code, never by eyeballing it.**
  The honest test harness: send real coding tasks (algorithm, data-structure class,
  recursion/parsing, debug-a-bug, multi-step), extract the ```python block, write
  to a temp file, `subprocess.run` it, and assert on stdout. Observed result from
  the free tier (Pollinations `openai-fast`, temp 0, sequential): **4/5 real
  coding tasks passed** — binary search, LRU cache, balanced-parens, word-freq all
  correct; one FAIL was a transient `504 Gateway Timeout`, not a wrong answer.
  Latency 12–65s/task. Takeaway: free models genuinely handle moderate coding, but
  expect occasional 504/429 — the retry/fallback layer is what makes them usable.
See `references/production-and-vision.md` for the benchmark harness pattern.

### P16 — Ollama last-resort fallback + vision DELEGATION (offline resilience)
This session added three durable, verified capabilities. Build them ADDITIVELY
(new `chat_messages()`, leave `chat()` untouched); all degrade gracefully when
Ollama is absent.
- **Ollama = last-resort fallback, dynamically discovered.** New `src/ollama.py`
  fetches installed models from the LIVE daemon (`GET /api/tags`) — never
  hardcode model names; `ollama pull X` and it appears. Classify each by NAME:
  vision hints (`llava`, `moondream`, `llama3.2-vision`, `qwen2-vl`, `minicpm-v`,
  `gemma3`, `pixtral`), coding hints (`coder`, `deepseek-coder`, `codellama`,
  `codegemma`, `starcoder`, `codestral`). Register ollama providers with a large
  NEGATIVE preference (e.g. -100) so `ordered_by_preference()` always tries them
  LAST — only when every remote free provider fails / network is down. Ollama's
  OpenAI-compatible endpoint is `http://127.0.0.1:11434/v1/chat/completions`
  (override daemon via `OLLAMA_HOST`); it's `openai_compatible` so the existing
  backend handles it, including base64 `image_url` for vision models. Cache
  discovery with a short TTL (30s) so you don't hit `/api/tags` per request.
- **Model-id parsing trap:** ollama ids contain TWO colons
  (`ollama:llama3.2:1b`). `server` splitting `provider:model` on the FIRST colon
  yields provider=`ollama` (unknown) → error. Special-case: if the requested
  model `startswith("ollama:")`, provider id = the whole string, model = the part
  after `ollama:`. Only fall back to `split(":", 1)` for non-ollama ids.
- **Vision DELEGATION** (the "coding model + images" ask): when the pinned/only
  usable model is NOT vision-capable, a vision provider analyzes the image into a
  detailed TEXT report (OCR + layout + colors + transcribed code), the image part
  is REPLACED by that report string, then the text model answers. Vision
  providers tried remote-first, local Ollama vision model last, so it works
  offline. Verified live end-to-end offline: image → non-vision `llama3.2:1b` →
  delegated to local `moondream` → report injected → correct answer.
- **Vision pitfall — solid/featureless images return EMPTY.** A vision model
  (moondream) returns `""` for a plain solid-color square (nothing to describe),
  which the router's empty-response guard then rejects as a failure. When
  live-testing vision, use an image with actual CONTENT (shapes/text/two-tone),
  not a solid fill, or you'll misdiagnose a working model as broken.
- **429/5xx retry with backoff** (`httpclient.post_json`): treat `429` (Pollinations
  "Queue full", see P15) AND `5xx` as TRANSIENT → retry with exponential backoff
  (1.5s→3s→6s, cap 30s), honor a `Retry-After` header; `401/403` still fail fast
  (no retry). Combined with provider rotation in the fallback chain, a
  rate-limited provider yields to the next instead of failing the request.
See `references/production-and-vision.md` for exact code patterns + the live
offline verification recipe.

## Verification (prove it works — user demands real output, not claims)
```
# server up?
netstat -ano | grep ':17498' | grep LISTENING
# live chat via catch-all (auto fallback)
curl -s --max-time 50 http://127.0.0.1:17498/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"free","messages":[{"role":"user","content":"Reply: PONG"}]}'
# targeted free model
curl -s ... -d '{"model":"pollinations_text:openai-fast",...}'
# list advertised models
curl -s http://127.0.0.1:17498/v1/models | python -c "import sys,json;print(len(json.load(sys.stdin)['data']))"
# CLI single-command status of every provider
python -m free_llm_router check --probe "hi"
python -m free_llm_router check --models --probe "hi"
python -m free_llm_router catalog
```
Green = a real assistant string returned (e.g. `"PONG"`), not just HTTP 200.

## Wiring into Hermes UI
Add to `config.yaml`:
```yaml
providers:
  free-llm-router:
    api: "http://127.0.0.1:17498/v1"
    default_model: "free"
    name: "Free LLM Router"
    models: ["free", "pollinations_text:openai-fast", ...]  # STATIC list, see P9
model:
  base_url: "http://127.0.0.1:17498/v1"
  provider: "free-llm-router"
  default: "free"
```
Then Hermes's model picker lists `free` + every `provider:model` entry. Back up
`config.yaml` before editing (`cp config.yaml config.yaml.bak`). **Restart
Hermes** (relaunch / gateway `/restart`) after editing — config is read once at
startup, NOT live.

### P9 — Hermes UI model list is a STATIC config.yaml list, NOT auto-refreshed from /v1/models
The Hermes desktop/CLI model picker reads `providers.free-llm-router.models` from
`config.yaml` verbatim. It does **not** poll the router's `/v1/models`. So the
router catalog and the config list are two separate lists that drift: you fix
`catalog.py`, the router serves the right models, but the UI still shows the old
hand-typed names (fake `opencode:kimi-k2.6`, dead `duckduckgo:*`, etc.). This is
the #1 \"the free models aren't updating in the UI\" complaint.
**Fix — single source of truth:** make `catalog.py` the ONE place to edit, and
GENERATE the config list from it. Pattern used here (all committed in the repo):
- `catalog.py` adds a `WORKING: set[str]` toggle (provider ids that actually
  answer anonymously) + `all_models(working_only=bool)` / `working_models()`.
- `sync_hermes_models.py` (repo root, stdlib+PyYAML) reads the catalog and
  rewrites `providers.free-llm-router.models` in `config.yaml`. Flags:
  `--check` (report drift, exit 1 if drift, change nothing), `--all` (include the
  full catalog, not just WORKING). Resolves config path via `$HERMES_HOME` else
  `%LOCALAPPDATA%/hermes/config.yaml`. Preserves all other config sections
  (uses `yaml.safe_load` + `safe_dump(..., sort_keys=False)`).
- `run_server.py` supervisor calls the sync script on startup (wrapped in
  try/except so a sync failure NEVER stops the router serving). Net effect:
  **edit `catalog.py` -> restart router -> UI list auto-updates.**
See `references/single-source-sync.md` for the exact code + verification.

### P10 — Stacked/orphaned supervisors cause an endless restart-loop + port clash
Repeatedly launching `run_server.py` (across debugging sessions, or when an old
background instance outlived its Hermes session) leaves MULTIPLE supervisors
alive. Each owns a child; only one can bind the port, the rest log
`OSError 10048 ... bind ... 17498` + `child exited code=1` + `restarting in Ns`
forever. Symptom: chat works (one child holds the port) but the supervisor log is
a churn of relaunches, and `netstat` shows the LISTENING PID changing.
**Fix — reduce to exactly one:** kill every supervisor and every server, confirm
the port is free with NO respawn, THEN start one:
```
python run_server.py --stop 2>/dev/null; pkill -f run_server.py; pkill -f free_llm_router
sleep 2
for P in $(netstat -ano | grep ':17498' | grep LISTENING | awk '{print $NF}' | sort -u); do taskkill /PID "$P" /F; done
sleep 3; netstat -ano | grep -q ':17498 .*LISTENING' && echo "STILL HELD (zombie respawning)" || echo "free"
```
Also `process(action='kill', session_id=...)` any Hermes-tracked background
`run_server.py` sessions from earlier turns — they respawn children otherwise.
Confirm stability by checking the LISTENING PID is UNCHANGED across ~6s, not just
that a chat succeeds.

### P11 — Proxy MUST emit SSE when `stream:true`, or Hermes silently renders nothing
Hermes (and most OpenAI clients) stream by default: they POST `stream:true` and
parse `text/event-stream` — `data: {...}` chunks of `object:"chat.completion.chunk"`
with `choices[].delta`, terminated by `data: [DONE]`. If the proxy ignores the
flag and returns a single plain JSON `chat.completion` object, the client's SSE
parser gets one un-prefixed blob and shows **nothing / a silent failure**.
Classic trap: **`curl` (non-stream) works, so the router looks fine, but it's
broken inside Hermes.** Always test with `stream:true` explicitly, and if the
client complains, that's the first thing to check.
**Fix pattern (aiohttp):** read `stream = bool(payload.get("stream"))`; when true,
return a `web.StreamResponse` with `Content-Type: text/event-stream`,
`prepare()`, then write role delta -> content delta -> stop delta -> `data: [DONE]`.
The router produces the full text in one shot, so a 3-chunk single-delta stream
is fine. Errors must ALSO honor transport: a streaming client can't parse a JSON
error body, so send errors as an SSE chunk + `[DONE]` too (make the error helper
`async` and `prepare()`/`write()` it). Non-stream path stays a plain
`web.json_response`. Verify:
```
curl -sN http://127.0.0.1:17498/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"free","stream":true,"messages":[{"role":"user","content":"say X"}]}'
# expect: data: {...chunk...}  x3  then  data: [DONE]
```
Then prove it end-to-end through the REAL client, not just curl:
`hermes chat -q "Reply with exactly: HERMESLIVE" --model free --provider free-llm-router`
(a trailing `RuntimeError: Event loop is closed` from MCP cleanup on exit is
harmless noise; the assistant reply above it is the real result).

### P12 — Scrubbing a term from the code must ALSO purge git history
When the user says "don't use word X anywhere in this project" (here: the
upstream project name that seeded the provider lists), fixing the source files
is only half the job — the word still lives in every past commit's diff/message.
Two-part fix:
1. Replace all source occurrences with generic wording (grep first to find them:
   `grep -rin "X" --include="*.py" --include="*.md" . | grep -v "/.git/"`), then
   re-grep to confirm NONE remain. Re-run tests + `python -c "import <pkg>"`.
2. Purge history. If there is NO remote yet (check `git remote -v`), the clean
   path is a fresh single commit: `rm -rf .git && git init -q && git add -A &&
   git commit -m "Initial commit: ..."`. Verify the term is gone from history:
   `git log -p | grep -i "X" && echo FOUND || echo clean`. (If a remote already
   exists, this needs a force-push / `git filter-repo` — confirm with the user
   before rewriting published history.)
Ask a one-line `clarify` when the term to remove has ambiguous spelling/variants,
or whether to delete vs. replace — cheap insurance before an irreversible history
rewrite touching many files.

### P13 — Multimodal/vision: `_extract()` crashes on list content; route images to vision providers
Adding OpenAI vision support (`content` as a list with an `image_url` part) has one
mandatory fix and one routing step:
- **Crash to fix first:** `server._extract()` does `" ".join(...)` over message
  `content`; with multimodal content that item is a LIST → `TypeError: sequence
  item 0: expected str instance, list found` → HTTP 500. Add a
  `_content_to_text()` helper (str→as-is, list→join `text` parts ignoring
  `image_url`, else "") and route all content reads through it. Relax the guard to
  `if not prompt and not has_image`.
- **Routing:** `backends._openai_complete` already forwards the full `messages`
  array untouched, so the image already reaches the provider — you only need to
  (a) keep the array intact (don't collapse to a prompt string) and (b) pick a
  vision-capable provider. Add `Provider.vision`/`vision_model`, a
  `vision_providers()` helper, and a `router.chat_messages(messages, ...)` that
  tries vision providers first when an image is present. Keep `chat()` untouched.
- **Free vision provider:** Pollinations `openai` model accepts `image_url`
  parts, keyless — verified live (blue PNG → "Blue"). Audio/PDF/docs are NOT
  supported by any free no-signup provider; pre-process to text first.
See `references/production-and-vision.md`.

### P14 — Production-hardening pass: don't add `src/__init__.py`; watch ruff/mypy traps
Making the repo shippable (packaging, Docker, CI, tests 10→30, legal/docs) is a
standard ADDITIVE pass — see `references/production-and-vision.md` for the full
checklist. Key traps: (1) do NOT add `src/__init__.py` — it breaks the flat
src-layout and makes mypy fail "found twice under different module names"; put
`__version__` in `pyproject.toml`. (2) `ruff --fix` can strip imports only used in
annotations under `from __future__ import annotations` (re-add `Optional`/`time`).
(3) `B904` is noise when errors chain via a custom `RouterError(cause=...)` — add
to ruff ignore. (4) drop the deprecated `@unittest_run_loop` on aiohttp 3.8+.
(5) if Docker Desktop's daemon is down you can't build locally — say so, let CI's
docker job prove it, never claim an unrun build.

## References
- `references/production-and-vision.md` — production-hardening checklist (P14) + multimodal/vision pass-through (P13).
- `references/provider-probe.md` — live probe results (time/region-sensitive) + how to re-run.
- `references/windows-ops.md` — taskkill/MSYS, zombie supervisor, autostart `.vbs` recipe.
- `references/single-source-sync.md` — make `catalog.py` the ONE source; auto-sync the Hermes UI model list (P9).
- `scripts/probe_providers.py` — standalone stdlib re-runnable probe of free endpoints.
