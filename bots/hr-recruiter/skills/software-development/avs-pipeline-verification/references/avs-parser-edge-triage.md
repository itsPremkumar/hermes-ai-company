# AVS script-parser edge-case triage (round 2, 2026-07-28)
Full report: `workspace/bug-hunt/findings_parser2.md`. Probes: `workspace/bug-hunt/parser_probe2.mts`.

## Import gotcha for `npx tsx -e` / .mts probes
Named import `import { parseScript } from '../../src/lib/script-parser'` FAILS
("does not provide an export named"). Use the default-shim pattern:
```ts
import sp from '../../src/lib/script-parser.ts';
const { parseScript } = (sp as any).parseScript ? sp as any : (sp as any).default ?? sp;
```

## Open bugs confirmed this pass
1. **P2-1 (HIGH) — `--no-acquire` missing `[Visual: file]` = silent success.**
   `agentic-modular.ts:247-249` warns + `continue`, exit 0; `:284` reports
   "manifest with 1 local asset(s)" where the 1 asset is the auto-selected MUSIC.
   Render then ships a video with zero user visuals. Expected: loud non-zero fail.
2. **P2-2 (HIGH) — CJK captions = tofu, emoji dropped.**
   `orchestrator/render.ts:363-375` font candidates start with arial.ttf (no CJK);
   seguiemj never selected; no msyh.ttc/Noto CJK in any candidate list
   (also `operations/captions.ts:26-30`, `media/export.ts:145`). Parser survives
   CJK/emoji fine — it's a render-path font issue. Vision grid proved white tofu blocks.
3. **P-4 confirmed end-to-end** — duplicate `[Visual: a.mp4] [Visual: b.mp4]` on a
   line WITH text: `script-parser.ts:322` takes `visualMatches[0]` only; b.mp4
   never appears on screen, zero warnings anywhere in plan/visuals/render.
4. **P-1 nuance** — parseScript gives duration=164s for 320-word line, plan stage
   clamps to 8s (`plan.ts:222`) — but 316 words ≈ 126s of TTS vs 8s planned scene:
   clamp without split is also wrong. Direct parseScript consumers
   (preview.ts, mcp tools, single-feature.ts) get the raw 164s.
5. **CJK keywords still garbage** — whole clause+emoji as one "keyword";
   full-width `。！？` not sentence boundaries.

## Verified OK
- Tag-only lines ([Transition:] alone, [Visual:] alone) — no phantom scenes, correct pendingVisualCue binding.
- 8-scene stress render — all frames correct, legible captions.
- Parser never crashes on CJK/emoji.

## Harness pitfalls (workspace/bug-hunt/harness.mjs)
- **Stale `.voice.lock`**: a killed harness leaves `workspace/bug-hunt/.voice.lock`
  → next run dies "could not acquire voice lock after 120s". `rm -f` it first.
- **Wrong-mp4 fallback**: harness.mjs:92 picks the LARGEST mp4 under output/ when
  the job-id dir match fails — short renders get an old demo's grid. Regenerate
  grids manually from `output/<jobId>/` when the render is small.
- Don't run harness.mjs via `terminal(background=true)` on this MSYS box —
  it exited immediately ("stdin is not a tty"); run foreground with timeout 600.
