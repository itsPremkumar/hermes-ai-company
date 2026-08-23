# Placeholder-as-Unset Pattern — Graceful Opt-Out for Disposable Config

A common anti-pattern in repos with `.env.example` or `.env` files: a
placeholder string like `<your-api-key-here>` is committed alongside a
runtime check `if (process.env.VOICEBOX_PROFILE_ID)`. Since dotenv re-injects
the placeholder at process start, the check passes and the code tries to use
the value — then blocks for retries before eventually falling back.

## The pattern: check for the placeholder string

Apply a **content check** alongside the existence check:

```ts
const raw = process.env.VOICEBOX_PROFILE_ID;
if (!raw || raw.includes('your-voicebox-profile-id')) {
    // Not a real profile — skip the entire service path
    return false;
}
```

## Two-layer defense

| Layer | Location | What it prevents |
|---|---|---|
| **Service gateway** | `ensureBackend()` (voicebox-lifecycle.ts) | Prevents spawning the Python backend process (40s+ overhead) |
| **Consumer** | `speakVoicebox()` (api-tts-provider.ts) | Prevents HTTP calls to the backend (30s×3 retry) |

Both layers should use the same check so that even if an earlier path creates
a side effect, the later path still bails out fast.

## Why not just check `process.env` alone?

Because `.env` files committed to the repo ship placeholder values that are
picked up by `dotenv.config()`. A shell-level `env -u VAR_NAME` is overridden
by dotenv. The placeholder string is the only reliable signal that "this value
was never really set."

## Related

- `repo-hardening/SKILL.md` §9 "Placeholder-as-unset — graceful opt-out for disposable config values"
- `src/lib/voicebox-lifecycle.ts` `ensureBackend()`
- `src/lib/api-tts-provider.ts` `speakVoicebox()`
