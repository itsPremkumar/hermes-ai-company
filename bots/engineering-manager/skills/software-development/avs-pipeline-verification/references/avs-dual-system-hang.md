# AVS dual music-system trap + timeout-that-doesnt-fire (G10/G11)

## Symptom this campaign hit
A variety render (wave1 jobs) froze for 9+ minutes at the log line:
```
[FREE-MUSIC]   ♪ Auto-selected free music: Be The Change (ccmixter)
```
No `Output:` ever appeared. `tasklist` showed node procs alive but **no `ffmpeg.exe`** running. That = hung in a JS await, NOT rendering.

## Root cause #1 — you patched the WRONG module
AVS has TWO music systems:
- `src/music-system/engine.ts` — the NEW architecture (what you naturally grep for).
- `src/lib/free-music.ts` — the LEGACY `FREE-MUSIC` engine, which emits the `♪ Auto-selected free music` line. **The agentic batch runner actually calls this one.**

The first fix hardened `withSignal` in `music-system/engine.ts` + wrapped ITS download in try/catch — but the live path was `free-music.ts:284` doing a bare `axios.get(url, { responseType:'arraybuffer', timeout:15000 })` with no AbortSignal. `axios` `timeout` only covers the **connect phase**, so a stalled ccmixter **body** stream never rejects → await hangs forever.

## Root cause #2 — `spawnSync` timeout on a wedged Windows child is unreliable
`voice-generator.ts` → `runPowerShellEncoded(..., { timeout: 120000 })` → `voice-engine.ts:50` uses `spawnSync('powershell.exe', ..., { timeout })`. When the PowerShell child spawns a grandchild (`.NET SpeechSynthesizer`) that wedges, the grandchild outlives the parent and `spawnSync`'s `timeout` is silently not firing — same class as above.

## The ONLY pattern that ALWAYS works
Race the op against a **hard `Promise` whose own `setTimeout(...reject)` fires independently** of whether the inner promise ever settles:

```ts
// src/music-system/providers/base.ts (already committed, reusable)
export async function withSignal<T>(
  factory: (signal: AbortSignal) => Promise<T>,
  timeoutMs: number,
  label: string,
): Promise<T> {
  const controller = new AbortController();
  let timer: NodeJS.Timeout | undefined;
  const hardTimer = new Promise<T>((_, reject) => {
    timer = setTimeout(() => {
      controller.abort();
      reject(new Error(`${label} timed out after ${timeoutMs}ms`));
    }, timeoutMs);
  });
  try {
    return await Promise.race([factory(controller.signal), hardTimer]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}
```

Then wrap the **call site** in try/catch so a rejection **falls through to the next provider / procedural ambient fallback** instead of throwing and killing the whole pipeline. An abort that throws but isn't caught still hangs the parent.

Unit-test `withSignal` with a promise that NEVER resolves — assert it rejects at `~timeoutMs`. If that test hangs, the guard is wrong.

## How to tell a hang from a slow render (don't "fix" prematurely)
A normal landscape 3-scene encode on the ~800MB-RAM box takes 90–120s. Do NOT conclude "hang" at 60s.
- **Hang (JS await stuck):** node procs alive, **NO `ffmpeg.exe`** in `tasklist`, log frozen at a non-render line (`Auto-selected free music` / `Falling back to Windows offline speech`) for 5–9+ min, no `Output:` line.
- **Slow render (healthy):** `tasklist` shows `ffmpeg.exe` running; an `Output:` line appears within ~3 min.

## Procedure when a "fixed" bug doesn't take effect on a live run
1. `grep -rn "EXACT log string" src/` — find the module that ACTUALLY emits it. That is the live path.
2. Trace the import chain from the CLI entry (`bin/variety-run.ts`, `src/adapters/cli/agentic-batch.ts`) down to the function. Confirm your edit sits on that chain.
3. If two modules implement the same thing, fix BOTH, but verify the runner uses the one you prioritized by checking `import` statements at the call site.
4. Only declare fixed after a LIVE run (not just typecheck) shows the symptom gone.

## Status at end of this campaign
- `music-system/engine.ts` hardened (`withSignal` + try/catch) — committed `5abe058`.
- `music-system/providers/base.ts` `withSignal` hardened — committed `5abe058`.
- `free-music.ts:284` routed through `withSignal` — committed `b3a783c`.
- **Voiceover SAPI hang (G11) was DIAGNOSED but NOT YET PATCHED** — the open blocker. Apply the `withSignal`-style hard race + silent/empty-audio fallback to `voice-generator.ts` `generateSceneVoiceoverWithWindowsSapi` before the next full variety sweep.
