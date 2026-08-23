# Gate false-positives — when the verification lies by passing

Two distinct ways an automated post-render / content gate can green-light a
broken or wrong output. Both were found and fixed in the Automated-Video-
Generator project; both are generalizable to any media/content QA pipeline.

## Case A — dimension check too loose (X14, `src/agentic/gate.ts`)

**Broken logic:**
```ts
const portraitOk = dim.height >= dim.width;   // 9:16 / 1:1 / anything tall-ish
const landscapeOk = dim.width >= dim.height;  // 16:9 / 1:1 / anything wide-ish
const dimOk = dim.width > 0 && dim.height > 0 && (portraitOk || landscapeOk);
```
Every non-zero rectangle satisfies one of the two → `dimOk` is ALWAYS true.
A portrait request rendered as 720x1280 landscape PASSED "Output dimensions
valid". The gate claimed correctness while the aspect ratio was wrong.

**Fix:** compare against the REQUESTED size within tolerance.
```ts
const exp = opts?.expectedDimensions;
if (exp && exp.w > 0 && exp.h > 0) {
  const wOk = Math.abs(dim.width - exp.w) <= Math.max(2, exp.w * 0.02);
  const hOk = Math.abs(dim.height - exp.h) <= Math.max(2, exp.h * 0.02);
  dimOk = dim.width > 0 && dim.height > 0 && wOk && hOk;
  dimDetail = dimOk ? `${dim.width}x${dim.height} (expected ${exp.w}x${exp.h})`
                    : `${dim.width}x${dim.height} MISMATCH expected ${exp.w}x${exp.h}`;
} else { /* fall back to the loose check only when no expected size known */ }
```
Thread `expectedDimensions` from the render call sites (single render +
multi-aspect render). Regression test (mocked analyzer, no ffmpeg):
- wrong aspect → `X14.pass === false`
- matching aspect → `X14.pass === true`

**General rule:** any gate whose pass-condition can be satisfied by a
degenerate input (any non-zero value, `a || b` where one branch is usually
true, a regex matching too much) is a false-positive. Audit each check's
pass-condition, not just its failure path.

## Case B — content verifier silent-passes on unparseable AI reply
(`src/lib/media-verifier.ts`)

**Broken logic:** `parseVerificationResponse(text)` returned
`{ passes: true, confidence: 5, reason: 'Could not parse AI response' }` when
the model replied with non-JSON (a refusal, a "Sure! Here is my thoughts…"
string). So an unparseable / failed watermark+NSFW check SILENTLY PASSED —
defeating the strict verifier.

**Fix:** route unparseable output through the same `failClosed` path as a
missing backend:
```ts
function parseVerificationResponse(text: string, opts: VisionCheckOptions): VerificationResult {
  // ... extract {...} ...
  if (jsonStart === -1 || jsonEnd === -1)
    return unavailableResult('Could not parse AI response (no JSON found)', opts); // fail-closed
  try { /* parse */ } catch { return unavailableResult('Could not parse AI response', opts); }
}
```
Both `verifyWithOllama` and `verifyWithGemini` pass `opts` through.
Regression test: mock `ollama-client` `generateContentWithImage` to return a
non-JSON string; call `verifyMedia(img, ['test'], { failClosed: true })` and
assert `passes === false`.

**General rule:** any AI-backed check must fail-closed when the model output
cannot be parsed/trusted — never default to `passes:true` on a parse failure.

## The test-harness gotcha behind both regression tests
Under tsx (CJS transform) you cannot `await import()` at module top-level
("Top-level await is not supported with the cjs output format"). So:
1. Register `mock.module('./dep.js', {…})` at top-level (sync call, fine).
2. Do `const { sut } = await import('./sut.js')` INSIDE each `test()` — the
   mock is already registered, so the loader applies it.
3. If the SUT reads the dep via inline `require()` instead of top-level ESM
   `import`, promote it to `import * as dep from './dep.js'` first (otherwise
   the mock won't intercept).
4. A check that only runs when the file EXISTS needs a real dummy file written
   in the test (`writeFileSync(tmp, 'dummy')`) or the check is never pushed and
   `.find(...)` returns `undefined` → `Cannot read properties of undefined`.
See `node-test-mocking` SKILL.md for the full mock pattern.
