# Free AI Provider Catalog — extraction & publishing recipe

Companion to the `$0-inference` section in SKILL.md. Reproduce this when the user asks for the
"completely free AI models / free providers" list, or wants it documented for the $0 money machine
"with or without OmniRoute".

## 1. Get the authoritative model list (not the README)

For OmniRoute, the marketing README lies/rounds numbers. The real catalog is a TypeScript data file:

```
curl -sL https://raw.githubusercontent.com/diegosouzapw/OmniRoute/main/open-sse/config/freeModelCatalog.data.ts -o freeModelCatalog.data.ts
```

Each entry looks like:
```ts
{ provider: "pollinations", modelId: "openai", displayName: "OpenAI (Pollinations)",
  monthlyTokens: 0, creditTokens: 0, freeType: "keyless", poolKey: "pollinations", tos: "caution" }
```

Key fields:
- `freeType` — `"keyless"` (no API key) or `"recurring-uncapped"` (permanently free, rate-limited).
  Both = "no paid API key". NOTE `keyless` is NOT always "no sign-in" (see split below).
- `tos` — `"ok"` / `"caution"` / `"avoid"` / `"unknown"`. The `avoid` ones (Antigravity, Qwen-web,
  Meta Muse, DuckDuckGo, Blackbox, OpenCode) explicitly ban third-party/proxy use in their ToS.
- `modelId` — the real ID to hand to the API.

Human-readable methodology: `docs/reference/FREE_TIERS.md` in the same repo (snapshot 2026-06-17,
shipped v3.8.40+).

## 2. Split into Tier A (truly anonymous) vs Tier B (login-gated)

- **Tier A** = `recurring-uncapped` providers + the `keyless` ones that are genuinely anonymous
  (Pollinations, Puter). Real families: Pollinations (~24), Puter (33), Z.AI/GLM-CN (3, `tos: ok`),
  OpenCode Zen (6), Kilo-gateway free (7), SiliconFlow (10), Tencent Hunyuan (1), Baidu ERNIE (1),
  UncloseAI/Liquid/Reka/StepFun/SenseNova.
- **Tier B** = `keyless` providers that STILL need a host login/cookie (not "no sign-in"):
  `agy` (Antigravity, 16), `qwen-web` (3), `muse-spark-web` (Meta, 3), `duckduckgo-web` (6),
  `blackbox` (6), `opencode` (GitHub login, 7), `friendliai`, `iflytek`, `coze`, `nlpcloud`, etc.
  Flag these `avoid` and keep them OUT of the production money pipeline.

## 3. Document both usage paths

- **WITH OmniRoute** (recommended): single endpoint `http://localhost:20128/v1`, `model: auto`.
  Smart routing + RTK/Caveman compression (~15–95% token savings) stretches free quotas → $0.
- **WITHOUT OmniRoute** (direct per-provider): show each provider's free base URL (verify in latest
  docs, e.g. Pollinations `https://text.pollinations.ai/v1/chat/completions` is OpenAI-compatible and
  anonymous). Mark these as examples to re-verify, not guaranteed-current URLs.

Always include the **golden rule**: re-check the latest upstream catalog (`freeModelCatalog.data.ts`)
AND each provider's latest official docs before shipping — free tiers/ToS change constantly.

## 4. Publish (verified 2026-07-15)

(a) Standalone repo:
```bash
TOKEN=$(printf 'protocol=https\nhost=github.com\n' | git credential fill | awk -F'= ' '/^password=/{print $2}')
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
  -d '{"name":"omniroute-free-ai-providers","description":"...","public":true,"auto_init":false}' \
  https://api.github.com/user/repos
# then: git init, add README.md + LICENSE (MIT), commit, git remote add origin <url>, git push -u origin master
# set default_branch to whatever local branch you pushed (master here)
```
(b) ALSO add the same file into the company repo as `docs/free-ai-providers.md` via the GitHub
`PUT /contents` API (see github-api-windows-reliability.md — `PUT /contents` can silently fail on
this box; verify it landed with `GET /repos/itsPremkumar/Hermes-Full-Autonomous-Company/contents/docs/free-ai-providers.md`), and add a short pointer in `docs/model-registry.md`.

## 5. Gotchas
- `python3` is NOT on this Windows box; use `python` (3.11) or `curl | python`.
- `git credential fill` output must be re-read from a `C:/...` path (the MSYS→uv Python boundary
  drops `/tmp/_tok.txt`).
- `raw.githubusercontent.com` is CDN-stale for minutes — verify via the API tree, not raw.
- Label all model data a SNAPSHOT (OmniRoute refresh 2026-06-17) so readers don't treat it as live.
