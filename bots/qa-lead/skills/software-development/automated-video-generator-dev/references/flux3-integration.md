# FLUX 3 optional backend — integration knowledge bank

Session 2026-08-01: built, verified, and shipped the opt-in FLUX 3 video backend
for AVS (`git 474b4f2 feat(agentic): optional FLUX 3 video backend via flux3-bridge`).
All facts below are empirically verified on this machine.

## Job contract (user-facing)

```json
{
  "id": "my-video",
  "orientation": "portrait",          // landscape|portrait|square
  "flux3": "auto",                    // off (default/absent) | auto | on
  "flux3Prompts": ["...", "..."],     // optional per-scene overrides, index = sceneNumber-1
  "script": "..."
}
```

- `off`/absent → pipeline byte-for-byte stock (zero behavior change).
- `auto` → FLUX 3 when the bridge reports available; ANY failure (gate, quota, job
  error) falls back gracefully PER SCENE and the run completes. Proven live: at the
  10th generation of the day the submission was rejected and scene 2 fell back —
  pipeline exited 0, video still rendered.
- `on` → requires FLUX 3, fails loud with the reason.
- `flux3Prompts[i]` overrides the default prompt derivation
  (voiceoverText → searchKeywords → title). Empty-string override is ignored.

## Code layout

- `scripts/flux3-bridge.py` — bridge run under the Hermes Agent venv
  (`C:\Users\PREM KUMAR\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`,
  override with env `HERMES_PYTHON`). Reuses Hermes' own Nous Portal auth +
  managed BFL gateway transport so availability matches the tool gate EXACTLY.
  Entry points: `available` → `{"available": bool, "reason": str}`; `generate
  --prompt ... --aspect W:H --duration N --out path` → one JSON line
  `{"job_id", "status", "saved_path"}`.
- `src/adapters/cli/flux3-option.ts` — pure helpers: `flux3Mode`, `flux3Aspect`,
  `flux3PromptForScene`, `flux3Duration`. Keep logic here; it's unit-tested
  (`flux3-option.test.ts`, 5/5).
- `src/adapters/cli/agentic-modular.ts` — Stage 2.5 `runFlux3` between plan and
  visuals; `flux3` subcommand; pipeline case calls runPlan → runFlux3 →
  runVisuals → runVoice → runRender. Writes `workspace/jobs/<id>/flux3/scene_N.mp4`,
  patches `plan.json` scene.localAsset (absolute path), writes `flux3.json`
  report with `fellBackScenes` count.

## CRITICAL pitfall: raw gateway payload shape

`_save_if_ready` in the Hermes tool (`tools/flux3_video_tool.py`) returns the
saved path at **`details.saved_path`** — NOT top-level. The tool WRAPPER
(bfl_flux3_get_result result object) flattens it to top-level `saved_path`, which
is why interactive tool calls look different from the raw payload a bridge sees.

Misreading this caused a real bug: the bridge polled `payload.get("saved_path")`
(top-level) → always undefined → every Ready response was missed → it re-called
`_handle_get_result` repeatedly, each call re-downloading the finished clip to a
new numeric-suffix file (`flux3_bridge_test-6.mp4` … `-51.mp4`, all same size).
Fixed by reading `(payload.get("details") or {}).get("saved_path")` with a
top-level fallback. Symptom signature: multiple same-size MP4s with `-N` suffixes
in the out dir = this bug.

## Poll/backstop timing (bridge must match)

`_POLL_BUDGET_SECONDS=180`, `_CALL_BACKSTOP_SECONDS=240`, `_POLL_GAP_SECONDS=5`.
One `_handle_get_result` call gives up after ~240s returning a "still generating"
payload; generation itself takes ~2-4 min per clip. Bridge loops: call → parse
Ready+`details.saved_path` → return; else sleep 5 and re-call.

## Orientation mapping + render compatibility

`portrait→9:16`, `landscape→16:9`, `square→1:1`. FLUX 3 output: h264+aac,
1280×704 (16:9) / 720×1280 (9:16) / 720×720 (1:1), 5-6s, ~2-5 MB. Render-safe:
compose.ts loops/holds short clips to scene duration (line ~728 `-loop 1 -t hold`),
so a 5s FLUX clip in a longer scene is fine.

## Mixed job files (FLUX + stock in one file)

Works per-job since the per-job no-acquire change: inside runVisuals, a job with
`flux3Mode(job) !== 'off'` always takes the no-acquire path (clips are local
assets); stock jobs acquire normally (Pexels etc.). Concat the two rendered MP4s
with the concat demuxer — same orientation ⇒ same 1280×720 h264+aac ⇒ `-c copy`
works. Verified combined video: `output/Temple of Dawn & Ocean Forces.mp4`.

## Quota

Free tier: 10 video generations/day. The submit response carries
"X of 10 video generations remain today". At 10/10 the submission is rejected and
`auto` falls back per scene (see job contract). Track usage; a 2-scene job = 2 gens.

## E2E verification recipe (proven)

1. `npm run agentic:modular plan -- --file input/scripts/<job>.json`
2. `npm run agentic:modular flux3 -- --file ...` (background; 4 gens ≈ 8-10 min)
3. Check `workspace/jobs/<id>/flux3.json` → expect `"fellBackScenes": 0`,
   one `bfl_job_*` id + `savedPath` per scene; check plan.json localAssets patched.
4. `visuals -- --no-acquire`, `voice`, `render` stages.
5. ffprobe dims match orientation; frame QA: `blackdetect=d=0.5:pix_th=0.10` and
   `freezedetect=n=-60dB:d=1` both zero hits.
6. Deliver: copy final mp4 to `C:\Users\PREM KUMAR\Downloads\` (user preference —
   "move that video to the downloads folder").
