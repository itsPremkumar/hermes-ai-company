# Model Specialization Map (role → model class)

Framework for matching each agent role to the model strongest at its workload.
RE-VERIFY the concrete IDs against `references/live-model-check.md` before assigning —
this snapshot is DATED (2026-08-18) and the live catalog drifts.

## Role → model-class reasoning
| Workload | Best model class | Why |
|---|---|---|
| Strategy / planning / CEO / CTO | reasoning-class (e.g. nemotron-nano-reasoning, Hy3) | long-horizon reasoning, trade-off analysis |
| Heavy coding / agentic builds | coding-class (DeepSeek V4 Pro, Qwen3.8, Laguna, north-mini-code) | SWE-bench / agentic coding strength |
| Long-context analysis / architecture | long-ctx (Kimi K3, Longcat, Qwen3.8 1M) | large repo / doc ingestion |
| Security review / secure coding | strongest code model + content-safety model | NO dedicated "cybersecurity LLM" exists free; use code model for find-and-fix + `nemotron-3.5-content-safety` for safety analysis |
| Fast / cheap / support / HR | small/fast free (nemotron-3.5-lightning, gemma-4) | high volume, low complexity |
| Docs / writing | strong general (Longcat, GLM) | language quality |

## DATED live-free snapshot (2026-08-18, OpenRouter)
```
nvidia/nemotron-3-ultra-550b-a55b:free      (strongest general — may be retired)
nvidia/nemotron-3-super-120b-a12b:free      (strong general + coding)
nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free  (reasoning)
nvidia/nemotron-3.5-lightning:free          (fast/cheap)
nvidia/nemotron-3.5-content-safety:free     (security/safe-code)
cohere/north-mini-code:free                 (coding)
poolside/laguna-s-2.1:free                  (coding)
poolside/laguna-xs-2.1:free                 (small coding)
google/gemma-4-31b-it:free                  (general)
openai/gpt-oss-20b:free                      (general)
```

## Example assignment (verify IDs live first!)
- CEO/CTO/Product/VP-Delivery → reasoning free model
- Tech Lead / Senior FE+BE / Fullstack / DevOps / Data → coding free model
- QA Lead / QA Engineer → content-safety free model
- Junior / HR / IT Support → fast/cheap free model
- UI-UX / Technical Writer / Business Dev → long-context general free model

## Honest caveat
There is no free "cybersecurity-specific" LLM. Security work = strongest coding model
for find/fix + the closest content-safety model for analysis. Don't claim a dedicated
sec model exists.
