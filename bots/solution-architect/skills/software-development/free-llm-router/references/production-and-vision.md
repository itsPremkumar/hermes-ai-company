# Production-hardening + multimodal (vision) pass-through

Two reusable passes on top of the working router (2026-07-24, v1.0.0 → v1.1.0).
Both are ADDITIVE and backward-compatible — the user's rule is: never delete/modify
old code, add standalone + shim; commit locally, push only after explicit "push".

## A. Make it production-ready (audit → harden)

The code was already good (clean src-layout, structured errors, 10 passing tests).
"Production-ready" for a shippable OSS repo means adding the layer AROUND the code
without touching logic. Deliver ALL of:

- **Packaging**: `pyproject.toml` (setuptools, `package-dir={"":"src"}`,
  `[tool.ruff.lint] select=["E","F","W","I","UP","B"]`, `[tool.pytest.ini_options]
  pythonpath=["src"]`, console-script), `requirements.txt` (runtime =
  `aiohttp>=3.9` only; core is stdlib), `requirements-dev.txt` (pytest/ruff/mypy).
- **12-factor config**: env-var defaults in `server.main()` via an `_env_default()`
  helper (`FREE_LLM_ROUTER_HOST/PORT/TIMEOUT/DEBUG`). **CLI flags still win** —
  argparse `default=_env_default(...)`. Backward compatible.
- **Docker**: `Dockerfile` (non-root user, layer-cached deps, `HEALTHCHECK`
  hitting `/health`, `CMD ["python","main.py","serve"]`, `HOST=0.0.0.0` inside
  container), `docker-compose.yml` (restart:unless-stopped, log volume,
  healthcheck), `.dockerignore`, `.env.example`.
- **Tests 10→30**: deterministic OFFLINE suites with `unittest.mock` so CI never
  depends on flaky free providers: mock `httpclient.post_json` / `router.complete`.
  `conftest.py` puts `src/` on path. Server handlers tested with aiohttp's
  `AioHTTPTestCase` (drop the deprecated `@unittest_run_loop` on aiohttp 3.8+).
- **CI**: `.github/workflows/ci.yml` matrix py3.10/3.11/3.12 running
  `ruff check .`, `mypy src` (continue-on-error ok), `SKIP_LIVE=1 pytest`, plus a
  `docker build` job.
- **Legal/docs**: `LICENSE` (MIT), `SECURITY.md`, `CONTRIBUTING.md`,
  `CHANGELOG.md` (Keep-a-Changelog), README badges + Docker + config table.

### Gotchas hit this pass
- **`src/__init__.py` breaks the flat src-layout.** Modules are imported flat
  (`import errors`, not `src.errors`). Adding `src/__init__.py` makes mypy fail
  with "Source file found twice under different module names". Do NOT add it — put
  `__version__` in `pyproject.toml` (and README), not a package `__init__`.
- **ruff `--fix` can strip "unused" imports that are only used in annotations**
  under `from __future__ import annotations` (it removed `Optional` and `time`
  from `router.py`). Re-add them and re-run; don't blindly trust auto-fix.
- **B904** (raise-from inside except): this codebase chains via a custom
  `RouterError(cause=e)` that sets `__cause__`, so B904 is noise here — add it to
  `[tool.ruff.lint] ignore`.
- **mypy `to_thread(chat, ...)`**: `chat()` returns `str | FallbackResult`, so
  `asyncio.to_thread(chat, ...)` trips arg-type. The result is narrowed at runtime
  (`text if isinstance(text,str) else text.text`); put
  `# type: ignore[arg-type]` on the line with the callable (`chat,`), not the
  closing paren.
- **Docker build can't be verified locally if Docker Desktop's daemon is down**
  (`open //./pipe/dockerDesktopLinuxEngine: file not found`). Say so honestly and
  let CI's docker job prove it — do NOT claim a build you didn't run.

## B. Multimodal (vision) image pass-through — free keyless providers

Goal: accept OpenAI vision format (`content` as a list with an `image_url` part)
and route to a vision-capable FREE provider. Verified live: a base64 blue PNG →
Pollinations `openai` model replied "Blue"; text path still returned "PONG".

Key insight: `backends._openai_complete` ALREADY forwards the full `messages`
array untouched — so multimodal content already reaches the provider at the
backend layer. The ONLY blockers were (1) `server._extract()` flattening content
to a string (and crashing on lists), and (2) no vision-provider routing.

Implementation (all additive):
1. `providers.py`: add `vision: bool=False` + `vision_model: str=""` to the
   `Provider` dataclass; mark Pollinations `vision=True, vision_model="openai"`
   (its keyless multimodal model); add `vision_providers()` (preference-ordered,
   vision-only).
2. `router.py`: add `_messages_have_image(messages)` + `chat_messages(messages,
   ...)` — a fallback loop that takes a FULL messages array (not a prompt string),
   tries `vision_providers()` first when an image is present (using each
   provider's `vision_model`), else normal order. `chat()` stays untouched.
3. `server.py`: add `_payload_has_image()`; in `handle_chat`, branch to
   `chat_messages` when an image is present, else the existing `chat` path.

### THE bug this class of change hits (must-fix)
`server._extract()` runs BEFORE the image branch and did
`" ".join(p for p in user_parts)` where `p` is now a LIST →
`TypeError: sequence item 0: expected str instance, list found` → HTTP 500.
Fix: add a `_content_to_text(content)` helper that returns str as-is, flattens a
parts-list to its `text` parts (ignoring `image_url`), else "". Route ALL
`content` reads in `_extract()` through it. Also relax the empty-prompt guard to
`if not prompt and not has_image`.

### Limits (tell the user honestly)
Images (vision) work on free keyless providers (Pollinations). Audio / PDF /
docs do NOT — no free no-signup provider accepts them; pre-process to text
(OCR / Whisper transcription) BEFORE the LLM.

### Live vision proof recipe (stdlib, no deps)
Generate a tiny solid-color PNG with `struct`+`zlib` (no Pillow needed), base64
it into an `image_url` data URI, POST to `/v1/chat/completions`, assert the
reply names the color. Write it to a FILE and run it — building the nested
dict/list payload inline in a bash heredoc trips Python bracket-matching.

## C. Coding-capability benchmark (grade by EXECUTION, run sequentially)

When the user asks "can these free providers actually do complex coding?", do NOT
eyeball the output — RUN it. Harness pattern (stdlib only, write to a file):
- Define 5 real tasks: algorithm (binary search), data-structure class (LRU
  cache), recursion/parsing (balanced parens), debug-a-bug (fix factorial base
  case), multi-step (word-frequency). Each prompt ends "Output ONLY runnable code
  in a ```python block", temperature 0.
- For each: `ask()` → `extract_code()` (regex the ```python block) →
  `run_python()` (write temp .py, `subprocess.run([sys.executable, path])`,
  timeout 30) → assert on `stdout.splitlines()`.
- Print `[PASS]/[FAIL] name (Ns) -> detail` and a final `SCORE: n/5`.

**Run it SEQUENTIALLY, one request at a time.** Pollinations enforces 1
concurrent request per IP (`HTTP 429 "Queue full for IP: ... (max: 1)"`), so a
parallel harness — or a benchmark colliding with the `/health` scan or another
curl — measures the throttle, not the model. If you must run it in the
background, don't fire other router calls at the same time.

Observed result (Pollinations `openai-fast`, temp 0, sequential, 2026-07-24):
**4/5 passed**; binary-search / LRU / balanced-parens / word-freq all correct,
one FAIL was a transient `504 Gateway Timeout` (not a wrong answer). Latency
12–65s/task. Conclusion to give the user: free models handle moderate coding
genuinely, but expect occasional 504/429 — a 429/504 retry-with-backoff +
provider-rotation layer (and/or a local Ollama provider) is what makes them
usable for real agent workloads. Delete the throwaway `_coding_benchmark.py`
after — never commit it.

## D. Ollama last-resort fallback + retry/backoff + vision DELEGATION (v1.2.0)

Three additive features from 2026-07-24 (see SKILL.md P16). All degrade to no-op
when Ollama is absent. Verified LIVE and fully OFFLINE.

### D1. Ollama dynamic discovery (`src/ollama.py`)
- `GET {OLLAMA_HOST}/api/tags` → list installed model names. NEVER hardcode.
  Fail SOFT on every path: no daemon / timeout / connrefused → return `[]`, so
  callers treat "no daemon" and "no models" identically. Stdlib `urllib` only.
- `_classify(name)` → `(vision, coding)` by lowercased substring hints
  (vision: llava, moondream, vision, -vl, vl-, bakllava, minicpm-v,
  llama3.2-vision, qwen2-vl/2.5-vl, gemma3, pixtral; coding: coder, code,
  deepseek-coder, qwen2.5-coder, codellama, codegemma, starcoder, codestral,
  granite-code).
- Cache with module-level typed globals + TTL (`OLLAMA_CACHE_TTL`, default 30s),
  NOT a `dict[str,object]` (that trips mypy on `list(...)`). Expose
  `best_coding_model()` (coder if any else first), `best_vision_model()` (vision
  or None), `clear_cache()` (tests + after `ollama pull`).
- `providers._ollama_providers()` builds `Provider(id=f"ollama:{name}",
  kind="openai_compatible", base_url=OLLAMA_OPENAI_URL, preference=-100(+5 if
  coding), vision=..., vision_model=name if vision)`. `ordered_by_preference()`
  and `vision_providers()` append them (sorted LAST). `get_provider()` resolves
  `ollama:*` ids by scanning `_ollama_providers()`.
- `server.handle_models` appends live ollama models to `/v1/models` (wrapped in
  try/except — Ollama optional, must never break the endpoint).

### D2. Model-id parsing (TWO colons)
`ollama:llama3.2:1b` — split-on-first-colon gives provider=`ollama` (unknown).
In `server.handle_chat`: `if requested_model.startswith("ollama:")` →
`provider_arg=requested_model`, `model_arg=requested_model[len("ollama:"):]`;
`elif ":" in requested_model` → normal `split(":",1)`.

### D3. Retry/backoff on 429+5xx (`httpclient.post_json`)
`for attempt in range(retries+1)`: on `HTTPError` if `code in (401,403)` raise
`ProviderAuthError` immediately (no retry); if `code==429 or 500<=code<600` set
`last_err=ProviderUnreachableError`, honor `Retry-After` (seconds form), `continue`
with exp backoff `min(1.5*2**(attempt-1), 30)`; other 4xx → `ProviderBadResponseError`
(no retry). Default `retries=2`. Test by monkeypatching `urllib.request.urlopen`
to raise `HTTPError` N times then succeed, and patch `time.sleep` to no-op.

### D4. Vision DELEGATION (`router.chat_messages`)
When an image is present, routing branches:
1. No image → normal preference-ordered chain.
2. Pinned provider is NON-vision (`get_provider(provider).vision is False`) →
   DELEGATE: `analyze_images(image_parts, question=user_text)` asks a vision
   provider for an exhaustive text report (OCR/layout/colors/code), then
   `_inject_report()` REPLACES the image parts with a string
   `"[Image analysis provided by a vision model]:\n" + report` and the text model
   answers on that.
3. No pin → try real `vision_providers()` directly (they see the image); if all
   fail, fall back to delegation.
Helpers: `_split_text_and_images(content)`, `_all_image_parts`, `_all_user_text`,
`_inject_report`, `_run_chain(order, messages, vision=bool)`. `analyze_images`
tries vision providers remote-first, Ollama vision last; raises
`NoHealthyProviderError` if none.

**Vision test trap:** a solid-color square makes moondream return `""` (nothing to
describe) → router's empty-guard rejects it as failure. Use a two-tone image with
a real shape (e.g. white bg + centered black square via raw PNG) when live-testing.

### D5. Live offline verification recipe (proven)
Start the daemon: `ollama serve &` (Windows: run the Ollama binary under
AppData\Local\Programs\Ollama). Confirm models via `GET /api/tags`. Then:
- Text: POST `{"model":"ollama:llama3.2:1b","messages":[...]}` → assert reply.
- Delegation: POST an `image_url` message pinned to a NON-vision model
  (`ollama:llama3.2:1b`); it must route through a local vision model (moondream)
  and the text model answers using the injected report. Bump server
  `FREE_LLM_ROUTER_TIMEOUT=300` — two sequential cold Ollama model loads are slow.
Result this session: 53 tests pass (was 34), ruff+mypy clean; text + delegation
both verified offline. Delete throwaway probe scripts (`_moon.py`, `_deleg_probe.py`)
after — never commit them.
