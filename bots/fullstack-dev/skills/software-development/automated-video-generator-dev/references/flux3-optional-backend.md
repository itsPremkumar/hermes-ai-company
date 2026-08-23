# FLUX 3 Optional Backend — Bridge Contract & Pitfalls

Empirically verified 2026-08-01 (live generation, ffprobe-verified clips). FLUX 3 is an
AI video generator available through the Hermes Agent Nous Portal (free tier ~10 video
generations/day). Integrated into AVS as an OPT-IN job option with automatic fallback to
the stock visuals pipeline.

## Job fields

| Field | Values | Meaning |
|---|---|---|
| `flux3` | `"off"` (default) / `"auto"` / `"on"` | `auto` = use FLUX 3 when available, fall back per-scene to stock on ANY failure (quota, no sign-in, gateway error, scene fail) — the run never breaks. `on` = hard requirement, fails loud with the reason. `off`/absent = pipeline byte-for-byte stock. |
| `flux3Prompts` | `string[]` | Per-scene prompt overrides aligned to scene order (index 0 = scene 1). Fallback chain: override → `voiceoverText` → `searchKeywords` joined → job `title`. |

Stage: `npm run agentic:modular flux3 -- --file <job.json>` (standalone), or automatically
inside `pipeline` between plan and visuals.

## Per-job semantics (mixed job files)

`--no-acquire` is decided **per job inside runVisuals**:
`cliArgs['no-acquire'] === true || flux3Mode(job) !== 'off'`. One job file CAN mix a
FLUX 3 job (local assets, no stock download) with a stock job (normal
Pexels/Pixabay download) — the pipeline does NOT force `--no-acquire` globally anymore
(that was the v1 behavior; per-job is the fix that made `flux3-plus-stock.json` work).
`runFlux3` skips jobs with flux3 off. The stock stage needs populated
`PEXELS_API_KEY` / `PIXABAY_API_KEY` in `.env`.

## Architecture

- `scripts/flux3-bridge.py` runs under the **Hermes venv python**
  (`C:\Users\PREM KUMAR\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`,
  override with env `HERMES_PYTHON`) with `sys.path.insert(0, HERMES_REPO)` so it reuses
  Hermes' own Nous auth + managed BFL gateway transport — availability detection exactly
  matches the Hermes tool gate, no duplicated auth code.
- Availability = `check_bfl_requirements()` from `tools/flux3_video_tool.py`
  (True ⇔ Nous sign-in present; entitlement/quota is the gateway's call, not the tool's).
- Generate = `_endpoints()` → `_submit("text_to_video", {prompt, aspect_ratio, duration,
  generate_audio, resolution:"720p"})` → parse `details.id` from the submit JSON → loop
  `_handle_get_result({"id": job_id, "save_to": out})` until Ready.
- Output: `workspace/jobs/<id>/flux3/scene_N.mp4`; `plan.json` scene `localAsset` patched
  to the absolute path; `flux3.json` report written (job ids, prompts, fellBackScenes).
- Bridge stdout is single-line JSON: `available` → `{"available": bool, "reason"}`;
  `generate` → `{"job_id", "status", "saved_path"}` or `{"error"}`.
- Pure decision helpers in `src/adapters/cli/flux3-option.ts` (`flux3Mode`, `flux3Aspect`,
  `flux3PromptForScene`, `flux3Duration`) with unit tests in `flux3-option.test.ts` —
  keep logic there, NOT inline in agentic-modular.ts.

## Pitfalls (all hit empirically)

1. **`saved_path` shape mismatch (the big one).** The READY payload from
   `_handle_get_result` carries the path at **`details.saved_path`**; top-level
   `saved_path` only appears after the tool wrapper flattens it. Reading top-level only →
   Ready never detected → the loop re-polls and RE-DOWNLOADS every iteration, minting
   `-6`, `-7`, … `-51` suffix files (a unique-name helper appends `-N`). Read
   `details.get("saved_path") or payload.get("saved_path")`.
2. **Poll budgets are short.** `_POLL_BUDGET_SECONDS = 180`, `_CALL_BACKSTOP_SECONDS =
   240` in flux3_video_tool.py — one `_handle_get_result` call gives up after ~3-4 min
   and returns "still generating". A bridge must loop: sleep ~5 s, re-call, with its own
   deadline (≈15 min). Generation takes 2-7 min for 5-8 s clips.
3. **Foreground terminal cap.** A 5-8 s generation exceeds the 600 s foreground timeout.
   Run the bridge via `terminal(background=true, notify_on_complete=true)`; when called
   from TS use `execFileSync` with `timeout >= 960_000` ms. NOTE: killing the bash
   wrapper on Windows may NOT kill the python child — after any timed-out bridge run,
   check for strays: `powershell Get-CimInstance Win32_Process | Where CommandLine -match 'flux3-bridge'`.
4. **Quota:** free tier = 10 video generations/day; submit responses include "N of 10
   video generations remain today". `available` checks sign-in only, NOT quota — treat
   submit-time gateway refusals as the fallback trigger in `auto` mode.
5. **ffprobe/ffmpeg path quirk on this box:** `ls` works with `/c/...` git-bash paths,
   but ffprobe/ffmpeg need `C:\...` (or `C:/...`) Windows paths; `$var` inside a
   double-quoted Windows path in bash mangles the name — single-quote the whole path.
6. **Windows ffmpeg can't read MSYS `/tmp` paths.** A concat list written to
   `/tmp/concat_list.txt` fails with "Error opening input file". Put the list inside the
   project (e.g. `workspace/concat_list.txt`) with `C:/...` entries, then
   `ffmpeg -f concat -safe 0 -i <project path> -c copy out.mp4`. Non-monotonic DTS
   warnings on the audio boundary of `-c copy` concat are harmless.

## Combined "one long video" recipe (FLUX part + stock part)

User asked for ONE long video containing both a FLUX 3 segment and the normal stock
segment. Works without code changes: one job file with two jobs (`flux3: "auto"` on one,
no field on the other — per-job semantics above), run `pipeline` on it (each job renders
independently to `output/<id>/`), then concat the two outputs. Both must share codec
(h264+aac) + resolution (same `orientation`) for `-c copy`; verify combined duration ≈
sum of parts. Frame QA: `ffmpeg -i f -vf "blackdetect=d=0.5:pix_th=0.10" -an -f null -`
and `freezedetect=n=-60dB:d=1` — empty grep = clean. Example: `input/scripts/flux3-plus-stock.json`.

## Verified integration points (reused, not changed)

- `visuals --no-acquire` accepts absolute `localAsset` paths (`path.isAbsolute(la) ? la :
  …`), `.mp4` → kind `video`, existence checked (agentic-modular.ts ~line 306-333).
- compose.ts loops/holds short clips to scene duration (`-loop 1 -t hold`, libx264) — a
  5-6 s FLUX 3 clip for a longer scene is fine.
- Render-manifest asset shape: `{kind, sceneIndex, localPath, license}`.
- Aspect mapping: portrait→9:16, square→1:1, landscape→16:9. Duration: clamp scene
  durationSec to 5-20 whole seconds.
- Full-suite gate: `npm test` (typecheck + all unit tests); targeted:
  `node --import tsx --test src/adapters/cli/flux3-option.test.ts` and
  `src/adapters/cli/agentic-cli.test.ts` (4/4).

## Reusable pattern

The whole thing is the template for "call a Hermes managed-tool backend from an external
project": spawn Hermes' venv python, import the tool module internals, probe the real
`check_*_requirements()` gate, submit → poll-loop with a caller-side deadline, verify the
file with ffprobe, and always keep an availability probe + fallback so quota/gate
failures degrade gracefully instead of breaking the run.
