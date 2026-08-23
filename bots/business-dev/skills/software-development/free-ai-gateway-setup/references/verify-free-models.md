# Verified: which no-key/no-signup free models ACTUALLY work (OmniRoute, v3.8.48)

Evidence from a real session: installed OmniRoute, connected no-auth providers via the
API, then fired real `POST /v1/chat/completions` and `POST /api/providers/<id>/test`
requests. These are ACTUAL HTTP codes + error strings, not README claims.

## The 7 "No Auth" providers OmniRoute exposes (Dashboard → Providers → "No Auth 0/7")
auggie, chipotle, duckduckgo-web, mimocode, opencode, theoldllm, veoaifree-web
(Pollinations is "Free Tier" type, not "No Auth" — connect it separately.)

## Connectivity + inference matrix (verified)

| Provider | Connect | `/test` (valid) | Real chat test | Verdict |
|---|---|---|---|---|
| **OpenCode Free** `oc/*` | API POST 201 | `valid:true` | HTTP 200, real text (deepseek-v4-flash-free) | **WORKING** reliable zero-key |
| **Pollinations** `pol/*` | API POST 201 | `valid:false` | via gateway timeout; direct `text.pollinations.ai` 200 | **Host-blocked** `gen.pollinations.ai` times out (HTTP 000) here; `text.pollinations.ai` works. Override base URL to fix. 50+ models (pol/openai, pol/claude, pol/deepseek, pol/grok, pol/gemini, pol/qwen-coder) |
| **MiMoCode** `mcode/*` | API POST 201 | - | "All accounts exhausted" | Free quota drained after 1 call |
| **Auggie** `aug/*` | API POST 201 | "Auggie CLI not found" | 502 `'auggie' is not recognized` | Needs local `auggie` CLI + `auggie login` |
| **DuckDuckGo** `ddgw/*` | API `Invalid provider` (web-cookie) | n/a | 418 "anti-abuse challenge ERR_CHALLENGE" | Anonymous session rejected; UI-connect only, still blocked |
| **TheOldLLM** `tllm/*` | API `Invalid provider` (web-cookie) | n/a | 403 Forbidden upstream | UI-connect only, upstream 403 |
| **Chipotle** `pepper/*` | API `Invalid provider` (web-cookie) | n/a | 502 fetch failed | UI-connect only |
| **Veo AI** `veoaifree-web` | API `Invalid provider` (web-cookie) | n/a | (video gen, not chat) | UI-connect only |
| `auto/best-coding` smart routing | - | - | tried 24 models, `max_attempts_exceeded` | Not usable from fresh no-key setup |

## Key findings / gotchas
1. "All free LLMs working" is FALSE on a fresh no-key setup. Only OpenCode Free returned
   real text reliably. Pollinations works once its blocked egress host is overridden.
   Everything else needs a free API key or a local CLI.
2. Web-cookie providers (duckduckgo-web, theoldllm, veoaifree-web, chipotle, + the 25
   Web-Cookie section) CANNOT be added via `POST /api/providers` — they return
   `{"error":"Invalid provider"}`. Use the Dashboard "Provider Onboarding Wizard".
3. Pollinations model IDs: use `pol/openai` etc., NOT `pol/gpt-5` (legacy API 404s
   "Model not found"; it expects `openai`/`claude`/`deepseek`/`gemini`/`grok`/`qwen-coder`).
4. Network egress block: `gen.pollinations.ai` -> HTTP 000 (timeout) here;
   `text.pollinations.ai` / `image.pollinations.ai` -> 200. Do not blame OmniRoute's logic.
5. Reliable $0 path that needs a FREE key (no card): NVIDIA NIM, Cerebras, Groq, GitHub
   Models, Together (signup credit). These are the dependable free tier.

## Reproduce the sweep
```bash
TOKEN=$(curl -s -D - -o /dev/null -X POST "http://localhost:20128/api/auth/login" \
  -H "Content-Type: application/json" -d "{\"password\":\"$INITIAL_PASSWORD\"}" \
  | grep -i set-cookie | sed 's/.*auth_token=/auth_token=/;s/;.*//')
curl -s "http://localhost:20128/api/providers" -H "Cookie: $TOKEN"
for id in <uuid1> <uuid2>; do
  curl -s -X POST "http://localhost:20128/api/providers/$id/test" -H "Cookie: $TOKEN"
done
curl -s -X POST "http://localhost:20128/v1/chat/completions" \
  -H "Content-Type: application/json" -H "Authorization: Bearer omniroute" \
  -d '{"model":"oc/deepseek-v4-flash-free","messages":[{"role":"user","content":"Say PONG"}],"max_tokens":10,"stream":false}'
```
Or run `scripts/verify_connected_providers.sh` (steps 1-3 automatically).
