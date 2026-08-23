# AVS render.ts — regex lint fixes & verify-after-edit pitfalls

Condensed from the 2026-08-01 production-readiness pass on `src/agentic/orchestrator/render.ts`.

## 1. Multilingual caption font regex → `no-misleading-character-class` ESLint error

`render.ts` has two font-detection regexes (`CJK_RE`, `INDIC_ARABIC_RE`) used by
`pickFontArg()` to fall back to a CJK / Indic-Arabic capable font (Noto / Nirmala)
so captions don't render as tofu boxes.

**Pitfall:** Writing the character class with literal Unicode script ranges
(e.g. `஀-௿`, `ഀ-ി`, `ก-๛`) triggers ESLint `no-misleading-character-class`
because some of those ranges contain combining marks that behave unexpectedly
inside a class. This is a hard **error** (not a warning) — it fails `npm run lint --quiet`.

**Fix (verified working):** use `\uXXXX` escapes only + the `u` flag (code-point mode).
```ts
const CJK_RE        = /[\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u2F00-\u2FDF\u3000-\u303F\uFF00-\uFFEF]/u;
const INDIC_ARABIC_RE = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\u0900-\u097F\u0980-\u09FF\u0A00-\u0A7F\u0A80-\u0AFF\u0B00-\u0B7F\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F\u0E00-\u0E7F\u0E80-\u0EFF\u1000-\u109F]/u;
```
If you must keep a literal-range version for readability, add an inline disable
directly above it AND keep the `u` flag:
`// eslint-disable-next-line no-misleading-character-class -- Unicode code-point ranges; tested and working`

## 2. `punchInByScene` typo → `Cannot find name 'z'` (TS2304, build-breaking)

In the per-scene advanced-FX block, the punch-in (zoom) push used to reference an
undefined symbol `z`:
```ts
// BROKEN (failed `npm run typecheck`):
segAdv.push(`scale=${Math.round(W * z)}:${Math.round(H * z)}:force_original_aspect_ratio=increase,...`);
```
`z` was never declared — the intended value is the in-scope `punch` variable
(`const punch = opts.punchInByScene?.[si]`). Fix: substitute `z` → `punch`.
The comment above it ("Starts zoomed (scale=z)…") must be updated to "(scale=punch)".
This is a silent compile error only caught by `tsc` — `eslint` does not flag it.
**Always re-run `npm run typecheck` after editing ffmpeg filter-string templates.**

## 3. Verify-after-edit on the shared low-RAM dev box (6GB)

- Do NOT launch a heavy `npm install` of many packages in parallel with an
  in-flight one — on this box it gets **OOM-killed (exit 137)** and can leave
  `package.json` bumped but `node_modules` mid-sync. Check `ps` for a running
  `npm`/`tsx`/`tsc` first; if a sibling install is active, wait, then verify with
  `npm ls <pkg>` that node_modules matches `package.json`.
- A parallel subagent may be editing the same files (observed subagent id
  `20260801_115710_89d71a` touching 21 files at once). Re-read the file immediately
  before `patch` if more than a few minutes passed since last read; the tool warns
  on sibling modification. Always re-run `typecheck` + `lint --quiet` after your edit
  to confirm you didn't regress the shared state.
- Cheap safety gate (no RAM risk): `npm run typecheck` and `npx eslint src/ remotion/ --quiet`
  both exit 0 when clean. `npm run test:unit` is RAM-heavy — avoid running it
  casually on this box; rely on typecheck+lint as the primary gate.
