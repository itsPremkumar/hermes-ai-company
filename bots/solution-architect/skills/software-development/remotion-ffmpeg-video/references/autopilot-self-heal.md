# Autopilot Self-Heal Pattern (Remotion/ffmpeg video pipelines)

Companion to SKILL.md P14. How to make a "fully automated" video pipeline that
survives known failure classes without a human in the loop.

## The shape

A single controller wraps `runPipeline + render + verify`:

```
autoRunVideo(req, opts) -> AutoRunReport
  loop (maxAttempts):
    run pipeline (+ render)
    if postRender.pass: return SUCCESS
    diagnose(events) -> fixes[]   # maps log signature -> side-effect fix
    if fixes == []: break          # unknown failure -> stop, report
    apply fixes; record fixesApplied; retry
  return FAILURE report
```

`AutoRunReport = { topic, success, outputPath, attempts, fixesApplied[], postRender }`.

## diagnose() — known failure signatures -> fixes

Keep it PURE and deterministic (no ffmpeg/network). Each fix is a side-effect on
the ENVIRONMENT only (clear a cache file, flip an env var) — never mutate source.

| Log signature (regex on joined event text)        | Fix                                  |
|----------------------------------------------------|---------------------------------------|
| `Found video on` / `flickr` / `placeholder`        | `rm .video-cache.json`                |
| `502` / `503` / `504` / `ETIMEDOUT` / `ECONNRESET` / `fetchVisual failed` | `rm .video-cache.json` + retry |
| `ffmpeg failed` / `X7` / `X8` / `X9` / `Invalid argument` / `No option name` | `AGENTIC_RENDER_SOFTEN=1` (renderer: kinetic OFF, shorter xfade, force ffmpeg) |

Unknown signature -> returns `[]` -> controller breaks and reports failure (no blind retry).

## PostRenderCheck shape (read this right)

`verifyRenderedVideo()` returns:
```
{ path, pass: boolean, checks: [{id,label,pass,detail}], probed? }
```
It does NOT have `.x7/.x8/.x9/.detail`. Reading `post.x7 && post.x8 && post.x9`
is ALWAYS false -> controller reports success as failure. Use `post.pass` and
`post.checks[i].pass`.

## Offline test of the self-heal loop (no network / no ffmpeg)

Inject a `runner` so you can force a fail-then-succeed sequence deterministically:

```ts
function check(pass: boolean, ids: string[]) {
  return { path: 'x.mp4', pass,
    checks: ids.map((id) => ({ id, label: id, pass, detail: id })) };
}

let calls = 0;
const report = await autoRunVideo(
  { topic: 't', title: 'x', backend: 'agent' },
  { maxAttempts: 3,
    runner: async () => {
      calls++;
      if (calls === 1) return { out: 'bad.mp4', post: check(false, ['X7']), gatePass: true };
      return { out: 'good.mp4', post: check(true, ['X7','X8','X9']), gatePass: true };
    } });
// expect: report.success === true, attempts === 2, fixesApplied.includes('render-soften')
```

For "no known fix -> stop at 1 attempt": `runner: async () => { throw new Error('unrelated purple elephant error'); }`
-> expect attempts === 1, fixesApplied.length === 0. NOTE the test-isolation trap
below — reset `AGENTIC_RENDER_SOFTEN` per case or it leaks from a prior case.

## Test-isolation gotcha (node:test)

Env vars set inside one test case persist into later cases in the same process.
`AGENTIC_RENDER_SOFTEN=1` set by a render-soften fix in case A spills into case B's
`autoRunVideo`, making a "should break at 1" case loop to maxAttempts. Fix: reset the
env var at the start of each case (`delete process.env.AGENTIC_RENDER_SOFTEN`), or read
it fresh inside the injected runner rather than once per module.
