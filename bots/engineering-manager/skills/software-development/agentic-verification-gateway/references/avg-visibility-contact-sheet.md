# AVG visibility layer — see every asset the agent approved

## Why it exists
The user's explicit correction (this session): *"no — in all the image and the video is
completely approved by you, the Hermes AI agent?"* → meaning: the **agent auto-approves
every image/video** (no human gate), BUT the user wants to **see every image and every
decision**. So the agentic pipeline must (a) approve all assets autonomously and (b) emit
a visible audit artefact. Visibility ≠ a human approval gate.

## What it produces (additive, in `src/agentic/orchestrate.ts`)
- `makeContactSheet(res)` — tiles EVERY non-music approved asset into ONE image:
  `agentic-pipeline/workspaces/<job>/contact-sheet.png`. Images added directly; for videos,
  one middle frame is pulled with `ffmpeg -ss 00:00:01 -vframes 1`. So a human/agent can
  SEE every downloaded visual in a single grid.
- `writeDecisionsReport(res)` — `decisions-report.txt`, stamped
  `decider: HERMES AI AGENT (autonomous, no external model)`, one line per asset with
  `[✅ APPROVED]` / `[❌ REJECTED]` / `[🔁 REPLACED]`, the `decidedBy`, and rationale.
- Wired into `runAgenticPipeline` after gate pass; CLI prints both paths; REST exposes
  `GET /api/agentic/jobs/:id/contact-sheet` + `/decisions`.

## The reliable ffmpeg contact-sheet recipe (and the traps)
Reliable:
```
ffmpeg -y -i img0 -i img1 -i img2 \
  -filter_complex "[0:v]scale=360:640[s0];[1:v]scale=360:640[s1];[2:v]scale=360:640[s2];[s0][s1][s2]vstack=inputs=3" \
  -frames:v 1 contact-sheet.png
```
Traps (each cost a real iteration this session):
1. **`xstack` + multiple `-i` + `-frames:v 1` → "Failed to inject frame into filter network:
   Invalid argument".** The inputs have different frame counts/durations and xstack can't
   align them. Use **`vstack`** (or `hstack`) instead — it just stacks same-width inputs.
2. **Do NOT prepend `nullsrc` as a base canvas.** `nullsrc=s=WxH:d=1[base];[base][s0]...xstack`
   → "Error linking filters" (nullsrc has no real frames to inject). `vstack` makes its own
   canvas — just stack the scaled inputs, no base.
3. **Label collision.** Naming scaled outputs `[v0],[v1],...` while ALSO using `[v0]` elsewhere
   (e.g. a nullsrc base) makes ffmpeg silently pick the wrong node. Use distinct labels
   `[s0],[s1],...`.
4. **Scale to FIXED size, not `360:-1`.** `xstack`/`vstack` require equal-size inputs; `-1`
   yields varying heights by aspect ratio → "Failed to inject frame". Use `scale=360:640`.
5. **Wrap the exec in try/catch returning `null`** — if ffmpeg fails, the pipeline must still
   render the video; the contact sheet is a nice-to-have, never a blocker.

## Test (`src/agentic/contact-sheet.test.ts`)
Build a synthetic `PipelineResult` with real placeholder PNGs; assert:
- contact sheet is a valid PNG (`slice(0,8).toString('hex') === '89504e470d0a1a0a'`).
- report contains `HERMES AI AGENT` and exactly 3 `✅ APPROVED` lines.
- **Pitfall:** count the stamped `[✅ APPROVED]` lines, NOT the bare word `APPROVED` — the
  report header also says "APPROVED by the agent", so a `/APPROVED/g` regex over-counts (4≠3).
