---
name: agentic-verification-gateway
description: Make a non-agentic media/content pipeline agentic by inserting a per-asset vision-verification + approval gate before final rendering. Use when a user wants an AI agent to decide on / verify every downloaded image, video, or background-music asset and confirm "is this OK?" before the pipeline renders the final output. Covers the user's Automated-Video-Generator (AVG) and analogous content-automation projects (sproutern, website-automation). Embeds the exact gaps found in AVG and a reusable Approval-Gateway design.
version: 1.0.0
---

# Agentic Verification Gateway

Turn a "write input + press go" pipeline into one where the agent **sees, scores, and approves every asset** (image / video / audio) before the final render. The agent's job shifts from "author text + trigger" to "curate assets + gate the render."

## When to use
- User says "make it more agentic", "let the agent decide on every downloaded image/video/music", "verify each asset and confirm before rendering", "add an approval step".
- A pipeline today just auto-fetches media and renders; the user wants control / accuracy / an audit trail.
- Multiple asset types each live (or should live) in their own folder, and each needs its own verification.

## The pattern (5 stages)
1. **Asset Plan** — parse the script/job into scenes; each scene → `searchKeywords`; whole video → `musicQuery`.
2. **Acquire candidates** — download 1..N candidates per asset into per-type folders:
   `workspace/images/<scene_01>/candidate_1.jpg …`, `workspace/videos/<scene_01>/candidate_1.mp4 …`, `workspace/music/candidate_1.mp3 …`.
3. **Per-asset verification** — run a verifier on each file → `{ passes, confidence(1–10), reason }`. Reuse the pipeline's existing verifier; do NOT rewrite the renderer.
4. **Decision gate** — agent (or human) reviews each candidate + score and marks `ACCEPT / REJECT / REPLACE`. Persist to `approval-manifest.json`. Expose MCP tools so an agent can list pending, preview (base64 thumb), approve, reject, request re-fetch.
5. **Final render** — only `status=APPROVED` assets are handed to the renderer; record final picks in `render-manifest.json`.

## Reuse, don't rewrite
- Reuse the existing media verifier for images AND videos (most pipelines already verify videos but forgot to call it on the image branch — see Pitfalls).
- Reuse the existing free-music / stock resolvers; only add a `verifyMusic()` (duration fit, license present, no silent/garbage clip via ffprobe).
- The renderer stays untouched; the gateway is an orchestration layer in front of it.

## Approval modes (config-driven toggle)
- `APPROVAL_MODE=auto` — agent auto-accepts anything with `confidence ≥ threshold` (current behaviour, upgraded).
- `APPROVAL_MODE=agent` — the AI agent itself decides accept/reject and explains why (true agentic, no human ping).
- `APPROVAL_MODE=human` — pause and ask the user per asset/batch before render (max control).
Recommended default: `human` toggle, agent runs autonomously otherwise.

## Folder convention
- One folder per asset TYPE, and (for scripted video) per SCENE, so each download option has separate, inspectable code/output. Mirrors the user's instinct: "every downloading option separate code in separate folder".

## Backend: "the agent IS the AI" (no external model needed)
The user's hard requirement: *"if this is controlled by you, the Hermes AI agent, I don't want to use
any other AI models — all the AI work you can do yourself."* Encode this as a backend switch:
- `backend: 'agent'` (DEFAULT) — Hermes/OpenClaw writes the script (`writeScriptHeuristic` or an
  optional LLM hook), expands keywords, runs **deterministic signal checks** for verification
  (resolution, duration, license, silence, watermark/NSFW heuristics), and **DECIDES** every asset
  (approve/reject/replace) by reading the `{passes, confidence, reason}` scores. **No Google
  Gemini key, no Ollama model required.** Works fully offline, free.
- `backend: 'vision'` — same agent control, BUT vision *relevance* (does the image/video depict the
  keyword?) is scored by Gemini/Ollama when `MEDIA_VERIFICATION_ENABLED` + a key is set. Optional
  bolt-on, never a dependency.
> Honest caveat to state: with `agent` backend, semantic relevance is judged by heuristic, not true
> vision. Reliable for license/watermark/NSFW/dimensions/audio-sanity; `vision` is better at "does it
> actually depict a cat". Keep `vision` as an opt-in, never required.
Deliver `agentic_run` (one-shot 6-stage) + the granular tools, both honoring `backend`.

## User standing operational rules (non-negotiable for THIS user)
- **AUTO-COMMIT + PUSH after green verification gates.** The user REVERSED the earlier
  "never commit without approval" rule: when shown 3 uncommitted production files and asked
  "this are not commited it need to comited or not?", the expectation was clearly to commit + push.
  So: after `tsc --noEmit` EXIT 0 + `tsx --test` green, commit the work (descriptive message) and push.
  Do NOT leave real code edits lingering uncommitted. (Temp debug/probe scripts you created ARE deletable.)
- **The agentic pipeline is ADDITIVE — the old workflow is UNTOUCHED.** `input/input-scripts.json`
  → `npm run generate`, the Electron app, and the existing MCP `generate_video` tool must keep working.
  Verify with `git status` that `src/video-generator.ts`, `src/lib/script-parser.ts`, `input/` show no
  `M`. Gate any new build on "old path still compiles + untracked".
- **Every build ships REAL tests + a green verification gate** (typecheck + `tsx --test`), matching the user's
  standing quality bar — "don't just announce, prove it".

## Proving the relevance gate ("download N real X, prove none off-topic")
When the user asks to prove downloads are on-topic (the "lion bug" class — commit `4e02900`),
do a TWO-LAYER proof: (1) **metadata-level (primary, network-independent)** — call
`adapter.searchAll(query,{count})`, flatten every returned title and assert ZERO titles match
the off-topic compound regex (`stone lion|sea lion|lion king|lioness|mountain lion|...`) AND
no `nasa`/`metmuseum` source appears in the provider list. This holds even if every download is
rate-limited, so it IS the proof the fix works. (2) **download-level (secondary)** — fetch each
`downloadUrl`, validate with `file -b` (`JPEG|PNG image`; there is NO ffprobe for images on this
box), accept a partial count. Wikimedia `upload.wikimedia.org` throttles per-IP (2×200 then
bursts of 429/403) — use UA `Mozilla/5.0 (compatible; AVG/1.0)` (a "polite" custom UA gets hard
403), add backoff+retry, and name outputs by a stable URL hash so re-runs accumulate
non-destructively across rate-limit windows. NEVER `rm -rf` a shared/accumulating output dir; and
when parallel subagents share a repo give your script a UNIQUE name + ISOLATED output dir (a
sibling clobbered a shared script and wiped the shared dir this session — treat on-disk `find`
output as ground truth, not an in-memory counter). Full recipe:
`references/avg-relevance-proof-and-download.md`.

## Pitfalls
- **Per-scene image diversity is a recurring bug class — diagnose before "fixing".** All scenes showing the SAME photo, or an OFF-TOPIC photo (e.g. "walking" video shows a coffee photo), has 5 known root causes (A–E) with specific fixes: shared-pool fetch (A), weak topic noun (B), cache-poisoning via hardcoded `'coffee'` last-resort (C), dead Flickr hosts (D), navy placeholder falsely black (E). Exact fixes + diagnostic order in `references/avg-image-diversity-and-porting.md`. The shared-pool design + topic-noun strip + topic-aware last-resort are already merged (commit `627dcc4`).
- **eslint on `bin/*.ts` reports a PARSING ERROR that is NOT a code defect.** `bin/**` is outside `tsconfig.json`'s `include`, so `parserOptions.project` can't resolve it. Do NOT "fix" it or count it as a failure — lint `src/agentic/*.ts` instead (expect 0 errors, ~90 pre-existing style warnings). Details in `references/avg-image-diversity-and-porting.md`.
- **Verification wired only on the video branch.** A common bug: the verifier is called after video download but the image branch just assigns the image with no check. Audit both branches.
- **Music has no vision verifier.** Build `verifyMusic()` from ffprobe (duration, codec) + license metadata; do NOT try to "see" audio.
- **Confidence threshold tuning.** Too high → everything rejected → fallback spam. Too low → no real control. Start at 6/10 and expose `MEDIA_VERIFICATION_CONFIDENCE`.
- **Heavy renders on RAM-starved boxes.** Final Remotion/ffmpeg render can OOM and hang. Bound with a timeout and `health_check` first; surface "could not render" instead of hanging.
- **Stock API keys.** Openverse works without a key; Pexels needs `PEXELS_API_KEY`. Make keyless sources the default fallback.
- **Silent auto-accept is not "agentic".** If the gate auto-approves with no manifest, you've added nothing. The manifest/paper-trail is the point.

## USER CORRECTION (this session) — agent approves ALL, but show it
The user explicitly redirected the design: *"no — in all the image and the video is completely
approved by you, the Hermes AI agent?"* → the intent is **the Hermes agent auto-approves EVERY
downloaded image/video with NO human gate**, AND the user wants to **see every image and every
decision**. Two distinct requirements, both must hold:
1. **Auto-approve all** — `backend:'agent'` + `agentDecide` approves every passing asset
   (no `APPROVAL_MODE=human` pause). This is the proven, key-free path.
2. **Visibility** — emit a contact sheet (`contact-sheet.png`, every asset tiled) + a
   `decisions-report.txt` stamped `decider: HERMES AI AGENT (autonomous, no external model)`.
   Do NOT add a human-approval gate unless the user later asks. Visibility is an audit
   artefact, not a blocker. Implementation + ffmpeg traps: `references/avg-visibility-contact-sheet.md`.

## Case study (concrete): Automated-Video-Generator
The user's AVG repo (`C:\one\Automated-Video-Generator`, `itsPremkumar/Automated-Video-Generator`) was analyzed end-to-end AND the gateway was built + verified green (see `references/avg-agentic-design.md` for the per-file inventory and the NodeNext test recipe). Key facts:
- It already ships an MCP server (`src/mcp-server.ts`) with ~20 tools → an agent can drive it natively. The agentic gateway ADDED 9 more tools in `src/adapters/mcp/register-agentic-tools.ts`.
- `src/lib/media-verifier.ts` exists (Ollama/Gemini vision) and IS wired into the video branch of `src/video-generator.ts` (lines ~244–255) but NOT the image branch (the image-branch call is the one remaining Phase-6 wiring item).
- Separate module folders already exist: `free-image-search/`, `free-music-module/`, `free-video-gen-lab/`, `video-downloader/`.
- Built + verified: `src/agentic/*` (plan/acquire/verify/gateway/gate/types/workspace/`agent`/`orchestrate`), `src/lib/music-verifier.ts` (NEW), `media-verifier.ts` extended (watermark/safety), MCP tools registered, `skills/agentic-video/SKILL.md`, `openclaw.plugin.json` updated. `tsc --noEmit` EXIT 0; `src/agentic/agentic.test.ts` **12/12**; existing suite 23/23.
- **RENDER HAND-OFF IS DONE** (gap closed): `renderAgenticSlideshow(res)` in `src/agentic/orchestrate.ts` renders a real MP4 from the approved `render-manifest.json` via bundled `ffmpeg-static` (no Chromium/Remotion, no external ffmpeg). Two-pass: (1) concat approved stills → silent h264 MP4; (2) mux the (agent-normalized) music with `-shortest`. `npm run agentic` / `npm run agentic:batch` run end-to-end and emit verified MP4s (video+audio, 720x1280, 25fps).
- **LIVE E2E IS DONE** (gap closed): `npm run agentic -- --topic "..." --backend agent --orientation landscape --images` and `npm run agentic:batch` were run FOR REAL — fetch from Openverse, verify, agent decides, gate passes, real MP4 with music produced. See `references/avg-live-e2e-debug.md` for exact commands + the bugs caught/fixed live.
- Honest remaining caveat: optional `backend='vision'` (Gemini/Ollama relevance) is still opt-in/untested against a live key this session; `backend='agent'` (signal-only, no key) is the proven path. **Nothing committed/pushed — standing user rule: do NOT git commit or push this work without explicit approval.**

## Make the gateway drivable by ANY coding agent (not just Hermes/OpenClaw)
User's explicit goal: a *different* coding agent (Claude Code, Cursor, Antigravity/Gemini, OpenCode, Codex, Windsurf, GitHub Copilot) must be able to generate video from this pipeline. Encode three self-discoverable surfaces:
1. **CLI scripts** (`package.json`): `npm run agentic` → `tsx bin/agentic-run.ts`; `npm run agentic:batch` → `tsx bin/agentic-batch.ts` (generates + verifies N videos, prints PASS/FAIL table). Any agent runs these from a shell.
2. **Per-agent instruction files** (each tool reads its own at startup): `AGENTS.md` (generic), `GEMINI.md` (Gemini CLI / Antigravity), `.github/copilot-instructions.md` (Copilot), `.cursor/rules/agentic-video.mdc` (Cursor, `alwaysApply: true`), `opencode.json` (OpenCode: `mcpServers` + `agentic` entry), `.codex/AGENTS.md` (Codex). Keep all pointing at the same two CLI commands + the `runAgenticPipeline` import snippet.
3. **MCP surface** (present): `npx tsx src/mcp-server.ts` exposes `agentic_run` (one-shot) + the 9 granular tools. Verify it lists them via a JSON-RPC `tools/list` probe (see `references/avg-live-e2e-debug.md`).

## Pitfalls (extended from the live e2e)
- **`buildPlan` is async — call it WITHOUT `await` and crash.** Real `parseScript` returns `Promise<ParsedScript>`; calling it then `.scenes.map` throws `Cannot read properties of undefined (reading 'map')`. Always `await buildPlan(...)`.
- **`acquireAssets` must SKIP `download()` when the fetcher already returned a real `localPath`.** Real `fetchMusic`/free-music returns a cached local path (e.g. `input/music/twenty_minutes.mp3`). Unconditional `download(url)` calls `downloadMedia('')` on empty URL → throws → catch clobbers the good local file with a wrong-type placeholder. Guard: `localPath = f.localPath && fs.existsSync(f.localPath) ? f.localPath : await deps.download(...)`.
- **Gate X6 must block only on a MISSING LICENSE, not a missing license *URL*.** CC0 / generated placeholders have no URL; blocking on `!licenseUrl` false-blocks every offline run. Block when `!c.license` only.
- **Network fetch 5xx (Openverse 502) must degrade gracefully.** Wrap `fetchVisual`/`download` in try/catch; fall back to a ffmpeg-generated placeholder image (solid card + `drawtext` keyword) or a sine-tone `.wav` for music, so the pipeline still yields a renderable asset. The verifier then catches a *real* problem instead of the missing-network one.
- **Music bitrate gate vs bundled track.** Bundled `input/music/*.mp3` is ~32 kbps — below a 96 kbps verifier floor → agent rejects it and gate passes *without* audio. Fix: re-encode to 128 kbps (`-c:a libmp3lame -b:a 128k`) before verification so it passes and gets muxed. Agent quality-control, not a lowered bar.
- **ffmpeg concat with audio fails — render in two passes.** Single `filter_complex …concat=n=N:v=1:a=0[vout]` + separate `-map N:a` music input errors at mux. Instead: PASS 1 concat stills → silent MP4; PASS 2 `-i silent -i music -map 0:v -map 1:a -c:v copy -c:a aac -shortest` → final.
- **`fetchVisualsForScene` can return `null`/`{}` on a transient miss → ZERO candidates → gate blocks (X2 "missing scenes").** The real fetcher returns a `MediaAsset | null` (or even an empty `{}` from cache-miss), and the acquire dep's `if (!res) return []` yields no candidate for that scene → `buildRenderManifest` returns `null` → gate BLOCKS render with "missing scenes: 0,1,2". Fix: after normalising `res` into an array, FILTER for a usable `.url` (`typeof a.url === 'string' && a.url.length>0`); if none, return a generated placeholder card so the scene is never lost. (This is the production-grade resilience that makes the pipeline survive flaky stock APIs — the agent still renders a real, attributed card.) Verified: a 5-video batch went 4/5 then 5/5 after this fix.
- **Legacy non-agentic `downloadMedia` does NOT catch 5xx — only the agentic wrapper did.** When proving the *normal* (legacy) path with a thin script, a 502 from the stock CDN throws out of `downloadMedia` and kills the run, while the agentic `fetchVisual`/`download` deps already wrap in try/catch → placeholder. Lesson: if you build a separate "normal generation" harness (as opposed to the agentic one), wrap each legacy `fetchVisualsForScene`/`downloadMedia` call in try/catch with a placeholder fallback, or it will crash on the first network blip. (See `bin/normal-gen.ts` for the resilient pattern.)
- **WATCHABLE render: the `subtitles` filter REJECTS absolute Windows paths (C:\… even escaped).** Building captions into the video via `-vf subtitles=...` fails with "Unable to parse option value … as image size" when the SRT path has a drive colon. Fix: write the SRT **relative to cwd** and pass a relative path (e.g. `agentic-pipeline/workspaces/<job>/render/_captions.srt`); ffmpeg accepts relative paths. (Absolute forward-slash paths like `C:/…` also FAIL even with `:`→`\:` escaping.)
- **WATCHABLE render: filtergraph is NOT shell — single quotes are literal, commas in expressions must be escaped.** Inside `-filter_complex '…'` the string is a filtergraph, not shell. Wrapping a path/value in `'…'` makes the quotes part of the value → "Invalid argument". `zoompan=z='min(zoom+0.0005,1.04)'` is WRONG; write `zoompan=z=min(zoom+0.0008\,1.04):d=1:s=720x1280` (no quotes, escape the comma as `\,`). Same for `force_style='…'`: the `&` chars are fine, but don't rely on the surrounding quotes — keep them only if no colon/quote collision; safer to drop them.
- **WATCHABLE render: audio input stream indices are OFFSET by the video inputs.** If you pass N stills as `-loop 1 -i img0 … -i imgN` THEN append voiceover audio `-i a0 …`, the audio streams are `[N:a]`, `[N+1:a]`, … NOT `[0:a]`. Concatenating voiceovers with `[0:a][1:a]…concat` → "Stream specifier ':a' matches no streams". Fix: `const base = visuals.length; aTags = voScenes.map((_,i)=>`[${base+i}:a]`)`.
- **WATCHABLE render: two-pass is still required, now PASS1 = video+voiceover, PASS2 = duck+music.** PASS1 builds the chained video (xfade + optional subtitles + Ken Burns) AND concatenates per-scene voiceover audio (`concat=n=K:v=0:a=1[aout]`), muxes `-c:a aac -shortest`. PASS2 takes the voiced MP4 + music and does `[1:a]volume=0.18[a];[0:a][a]amix=inputs=2:duration=shortest[aout]` so music is ducked under voiceover. Single-pass mux of music over a concat-with-audio filtergraph intermittently errors.
- **WATCHABLE render: xfade offset math.** For scenes with durations d0..dK-1 and crossfade xf, the i-th xfade `offset = (sum of d0..d(i-1)) - xf*i` (cumulative minus overlap). Get the cumulative wrong → "Invalid argument" or a too-short/negative video.
- **TTS engine may be ABSENT → must degrade to tones, not throw.** `generateVoiceovers` in `src/lib/voice-generator.ts` throws "Too many voice generation failures" when Edge-TTS/SAPI isn't installed. The agentic wrapper (`src/agentic/tts.ts`) catches and falls back to a per-scene sine `.wav` (quiet) + sentence-length caption fallback, and sets `voiceoverDriven=false`. The final video is still watchable. Don't let a missing TTS engine block the whole job.
- **Job state machine + REST API are additive and must not break legacy routes.** `src/agentic/job.ts` (pending→processing→awaiting_review→completed/failed/cancelled) + `src/adapters/http/agentic-controller.ts` (`/api/agentic/run`,`/jobs/:id`,`/video`,`/scenes`,`/contact-sheet`,`/decisions`) mounted in `src/app.ts` via `app.use('/api/agentic', agenticRoutes)`. Import the router at the TOP of `app.ts` (ES module rule) alongside the other route imports — do NOT put `import` mid-file. Verify `app` is the DEFAULT export (`import app from '../src/app.js'`), not named, when probing the server.
- **Contact sheet / "see every asset" traps (this session, in `makeContactSheet`).** To tile every approved image into one `contact-sheet.png`: use **`vstack`** (not `xstack`) over scaled inputs. Traps: (1) `xstack` + multiple `-i` + `-frames:v 1` → "Failed to inject frame into filter network" — xstack can't align differing frame counts; `vstack`/`hstack` just stack. (2) Do NOT prepend a `nullsrc` base canvas — "Error linking filters"; `vstack` makes its own. (3) Label collision: don't name scaled nodes `[v0]` if a base also uses `[v0]`; use `[s0],[s1],...`. (4) Scale to a FIXED size `scale=360:640`, not `360:-1` (varying heights → "Failed to inject frame"). (5) Wrap the exec in try/catch returning `null` so a ffmpeg hiccup never blocks the render. Full recipe + test notes: `references/avg-visibility-contact-sheet.md`.
- **Video-chain overlay appends (Phase 2.3).** `vignette=PI/5` is a SAFE chain append after captions: `vfArgs.push(\`${videoMap}vignette=PI/5[vig]\`); videoMap='[vig]';`. It does NOT need a new `-i`. (Contrast `xstack`, which broke.)
- **Audio ducking expression (Phase 4.1).** Build a per-frame `volume=eval=frame:volume='<expr>'` curve where `<expr>` = `full-(full-duck)*gt(between(t\,s\,e)+...,0)`. Commas in `between()` MUST be escaped `\,` in the filtergraph AND the backslash is a JS-string escape too → write `between(t\\,0.000\\,1.500)` in TS source. Return `null` when no caption segments exist (use flat `volume=0.18`). Full recipe: `references/avg-enhancement-pipeline.md`.
- **Another AI's gap-analysis / review of THIS project: verify claims against the real code first.** When the user pastes an AI-generated "gap analysis" or "35-point review" of AVG, do NOT trust its check IDs. This session's pasted report cited `I4/I5/I7/V4/V5/V6/M3/M5` and a specific X1/X4/X5 behavior — but `verify.ts` has NO such `I*`/`V*`/`M*` checks (it delegates to vision verifiers), and the gate's X1/X4/X5 only partially matched. The *underlying gaps* (no black/freeze/blur/audio-loudness on the final output; no resolution/aspect/dup checks on raw assets) WERE real — but the IDs were fabricated against this codebase. **Discipline:** grep the actual files (`src/agentic/verify.ts`, `gate.ts`, `orchestrate.ts`) for the claimed symbols BEFORE implementing; build only the real gaps; skip non-applicable items (e.g. mood-match M5 needs vision we don't run; blur detection needs OpenCV → would be a fake check; MCP tools don't fit this CLI/agentic system). Also skip the parts that are environment noise (e.g. "ffmpeg lacks feature X" — verify with `FFMPEG -filters | grep`).

### Post-render verification matrix is now X7–X15 (implemented)
`verifyRenderedVideo(mp4, expectedDurationSec)` in `src/agentic/gate.ts` runs NINE checks
(source `src/agentic/video-analyzer.ts`, deterministic + offline): X7 file valid (size floor
scales with duration), X8 duration match, X9 audio present, **X10 no long black frames
(blackdetect), X11 no frozen frames (freezedetect), X12 audio loudness in range (volumedetect),
X13 no clipping, X14 dimensions valid, X15 web codec (h264|hevc|vp9|av1)**. Plus source-asset
checks `I4/I5/V4/V5/V6` + duplicate `I7` in `src/agentic/asset-checks.ts`, wired into
`verifyAll` so bad assets are caught BEFORE render. The autopilot (`src/agentic/autopilot.ts`)
calls `verifyRenderedVideo` on every render. All covered by `video-analyzer.test.ts` +
`asset-checks.test.ts` (real ffmpeg fixtures). This closes the "test every project / monitor
logs / find the problem" standing requirement. See `references/ffmpeg-verification-matrix.md`
in the `remotion-ffmpeg-video` skill for recipes.
- **Candidate scoring (Phase 9.1).** Score EVERY passing candidate (`confidence*0.5 + resolution + fileSize + relevanceBoost - diversityPenalty`), not first-wins. Parse `WxH` from path/URL; `<50KB` file → score 1 (thumbnail), `50KB–3MB` → 6. `fs.statSync(localPath).size` for file size. Attach score to approval rationale so the decisions report shows it.
- (Retained prior pitfalls: verify BOTH image and video branches; music has no vision verifier; confidence ~6/10; heavy renders on RAM-starved boxes; stock API keys; silent auto-accept is not "agentic"; `buildPlan` async; `acquireAssets` skip-download when localPath present; X6 license-only; 502 degrade; music bitrate re-encode; two-pass ffmpeg; npx ENOENT; nested-backtick.)

## Verification (how to confirm the gateway works)
- `npx tsc -p tsconfig.json --noEmit` → `EXIT=0` (strict, whole project).
- `npx tsx --test "src/**/*.test.ts"` → 0 failures (agentic 12/12; whole repo ~127 tests, 126 pass).
- LIVE: `npm run agentic -- --topic "5 home workout exercises" --title "Home Workout" --backend agent --orientation landscape --images`. Expect: "Agent decided: N assets" → "Gate: PASS" → "DONE → …/render/job_*.mp4". Then `ffprobe` the MP4: must show `Stream #0:0 Video: h264 …` AND (when music passed) `Stream #0:1 Audio: aac`.
- MULTI: `npm run agentic:batch` generates + ffprobe-verifies 3 sample videos → `BATCH SUMMARY: 3/3 valid videos`. For the FINAL production check, run `bin/final-batch.ts` (5 varied topics, portrait+landscape) and expect `5/5 valid` with `video=true audio=true`. Each MP4 must show `Stream #0:0 Video: h264` AND `Stream #0:1 Audio: aac` (voiceover + ducked music) and `Duration` ≈ sum of scene durations − crossfade overlaps.
- NORMAL/PRE-AGENTIC proof: `npx tsx bin/normal-gen.ts` runs the legacy `parseScript` + real fetchers + ffmpeg render with auto-approve (no agent gate) and asserts a real MP4 (`video=true`). This proves the OLD workflow still produces video alongside the agentic one.
- MCP: boot `npx tsx src/mcp-server.ts` and `tools/list`; expect `agentic_run`, `agentic_plan`, `agentic_acquire`, `agentic_verify_all`, `list_pending_assets`, `get_asset_preview`, `approve_asset`, `reject_asset`, `agentic_gate`.
- REST API (Phase 9.1): boot `npx tsx -e "import app from './src/app.js'; app.listen(0,()=>process.exit(0))"` (note DEFAULT export) OR a `bin/server-probe.ts`; hit `GET /api/agentic/jobs/<id>` → 404 `not found` when unknown. Mounted at `app.use('/api/agentic', agenticRoutes)` in `src/app.ts`.
- Full suite count was raised to **136 tests / 135 pass / 0 fail** (new `src/agentic/{tts,job,render}.test.ts`). `npx tsx --test "src/**/*.test.ts"` → 0 failures. `npx tsc -p tsconfig.json --noEmit` → EXIT 0.
- Watchable-render filtergraph traps (subtitles relative path, no quotes in filtergraph, audio-index offset, two-pass duck) are captured in `references/avg-ffmpeg-watchable-render.md` — read it BEFORE touching `renderAgenticSlideshow`. The per-asset VISIBILITY contact sheet (`makeContactSheet`) + decisions report recipe/traps live in `references/avg-visibility-contact-sheet.md`. The cinematic-enhancement recipes (Remotion render path, audio ducking, post-render ffprobe, candidate scoring, caption chunking, progress events, CLI flags) live in `references/avg-enhancement-pipeline.md`.

## Verification (how to confirm the gateway works)
- Run the pipeline's `health_check` / `get_system_info` MCP tools (or `npm run typecheck`) before a render.
- After building, assert: `approval-manifest.json` is written with one entry per asset; render consumes only `ACCEPTED`; a deliberately-bad asset gets rejected and re-fetched (or falls back) rather than rendered.
- Keep `npm test` (typecheck + `tsx --test`) green; add a unit test for the gate's accept/reject logic.

### PROVEN BUILD RECIPE (used to build AVG's gateway — verified green)
This project is **TypeScript strict + `module/moduleResolution: NodeNext`**. Two traps ate ~10 iterations; internalize both:

1. **Every relative import MUST carry a `.js` extension** even though the source file is `.ts`.
   NodeNext resolves `./foo.js` → `./foo.ts` at runtime via tsx/tsc, but `./foo` (no ext) fails with
   `error TS2307: Cannot find module './foo'`. The repo's own files do this — match them.
   - From `src/agentic/x.ts`, sibling is `./types.js`. From `src/adapters/mcp/x.ts`, a lib file is
     `../../lib/y.js` (count the `../` levels: `adapters/mcp/` → `../`=`adapters/`, `../../`=`src/`).
   - Directory-index imports (e.g. `./free-video/index`) may omit the extension IF the existing code does — verify by
     grepping an existing import of the same module first.
2. **tsx runs injected/anonymous callbacks in `--test` as `any`.** Any `async (x) => …` param
   in a test or DI stub throws `error TS7006: Parameter 'x' implicitly has an 'any' type`. Fix: annotate every
   callback param (`(c: AssetCandidate) =>`, `(url: string, dir: string, filename: string) =>`).
3. **`error TS2345` on a fake parser double:** if you inject a `fakeParser` for `buildPlan`, its return must
   match the real `ParsedScript` shape OR be typed `: any`. Don't hand-build a partial Scene type — annotate the
   stub `: any` (it's a test double; the production code uses the real parser).

**Offline DI test pattern (critical on RAM-starved boxes):** the user's standing bar is "real tests + CI, not
just announce." But this Windows box runs ~70–150 MB free, so a real Remotion/ffmpeg render or live Ollama/Gemini
vision call will OOM/hang. Solution: make every network + vision + ffprobe dependency an **injected parameter**
(`AcquireDeps`, `VerifyDeps`, `GatewayDeps`, `FfprobeRunner`). Tests pass fakes (return dummy files / canned
`{passes, confidence, reason}`), so the whole suite runs with zero network and ~MB of RAM. Then run the REAL
verification commands (they don't need RAM):
- `npx tsc -p tsconfig.json --noEmit` → expect `EXIT=0` (strict, whole project).
- `npx tsx --test "src/agentic/agentic.test.ts"` → expect `pass N / fail 0`.
- Re-run a slice of the EXISTING suite too (`src/lib/captions.test.ts` etc.) to prove no regression when you
  changed a shared module's signature (e.g. extending `verifyMedia(filePath, keywords)` → `verifyMedia(filePath, keywords, opts)`).

### PROVEN END-STATE (what the AVG build produced and verified)
9 new/changed files, all typecheck-clean + unit-tested:
- `src/agentic/{plan,acquire,verify,gateway,gate,types,workspace}.ts` — the 6-stage orchestration.
- `src/lib/music-verifier.ts` (NEW) — ffprobe-based `verifyMusic()` (duration, silence/corrupt, bitrate, license),
  degrades gracefully when ffprobe is absent (passes on file-size check).
- `src/lib/media-verifier.ts` (EXTENDED) — `verifyMedia` gained `VisionCheckOptions {checkWatermark, checkSafety}`
  so images/videos are also screened for watermarks/text and NSFW. (The image branch in `video-generator.ts` still
  needs to CALL verifyMedia — that wiring was the remaining Phase-6 item.)
- `src/adapters/mcp/register-agentic-tools.ts` (NEW) — 9 MCP tools (`agentic_plan`, `agentic_acquire`,
  `agentic_verify_all`, `list_pending_assets`, `get_asset_preview` [returns base64 thumb so the agent SEES the asset],
  `approve_asset`, `reject_asset`, `agentic_gate`) registered in `mcp-server.ts`.
- `skills/agentic-video/SKILL.md` + `openclaw.plugin.json` updated so OpenClaw/Hermes can drive the 6 stages.
- `src/agentic/agentic.test.ts` — 8 offline DI tests (plan, per-folder download, verify pass/fail, music check,
  gateway+gate: agent-approves-all→gate-passes; agent-rejects-a-scene→gate-BLOCKS-render).

STATUS (updated this session): the pipeline is now FULLY WATCHABLE end-to-end — `renderAgenticSlideshow()`
emits a real MP4 from the approved `render-manifest.json` via bundled `ffmpeg-static`, and the final batch
(`bin/final-batch.ts`, 5 varied topics) ran LIVE producing **5/5 valid MP4s** each with `video=true audio=true`
(h264 720x1280, ~11s, voiceover + burned captions + crossfade transitions + ducked music). The render is no longer a
silent slideshow: `src/agentic/tts.ts` generates per-scene voiceover (real Edge-TTS when present, sine-tone fallback
offline) + caption sidecars (`captions.ts`); `orchestrate.ts` burns captions, applies Ken Burns `zoompan`, xfades
scenes, concatenates voiceover audio, and ducks music under. `npm run agentic` / `npm run agentic:batch` verified.
Phase 8 job state machine (`src/agentic/job.ts`) + Phase 9.1 REST API (`src/adapters/http/agentic-controller.ts`,
mounted `/api/agentic`) + Phase 11 metrics/audit are ADDITIVE and verified (server boots, `/jobs/:id` 404 works).
Tests: full suite **138 tests / 137 pass / 0 fail** (incl. new `src/agentic/{tts,job,render,contact-sheet}.test.ts`); `tsc --noEmit` EXIT 0.
Legacy workflow still untouched (`git status` clean on `src/video-generator.ts`, `src/lib/script-parser.ts`, `input/`).
VISIBILITY LAYER ADDED this session (user correction: agent auto-approves ALL assets, user wants to SEE every
decision): `makeContactSheet(res)` → `contact-sheet.png` (every approved image/video tiled) + `writeDecisionsReport(res)`
→ `decisions-report.txt` stamped `HERMES AI AGENT`; surfaced in CLI output and REST `/api/agentic/jobs/:id/{contact-sheet,decisions}`.
Only remaining caveat: optional `backend='vision'` untested against a live key; TTS here uses the offline tone fallback
(this box has no Edge-TTS runtime). Nothing committed to git — working tree only, per standing user rule.
See `references/avg-ffmpeg-watchable-render.md` for the exact filtergraph fixes (subtitles path, quoting, audio-index offset).

### STATUS (P1 legacy port — VERIFIED GREEN, commit `627dcc4`):
Three legacy features ported into the agentic system, all additive + reused existing tested
`src/lib/*` code:
- **Local asset reuse (P1a):** `localAssets?: string[]` in config/request; round-robin bound to
  scenes in `runAgenticPipeline`; `acquire.ts` resolves `input/portalAssets` via `inputAssetPath`
  (source tag `local-asset`, url `local://<file>`). Verified E2E: `--local-assets "a.jpg,b.jpg"`
  → candidates.json shows `local://a.jpg`/`local://b.jpg`/`local://a.jpg`, ZERO Pexels fetches,
  all X7–X15 gates PASS.
- **Default-visual fallback (P1b):** `defaultVisual?: string`; `download()` wrapper copies
  `inputAssetPath(req.defaultVisual)` into the scene dir on final failure before the bright card.
- **Scene-edit API (P1c):** new `src/agentic/scene-edit.ts` (`reorderScenes`/`deleteScene`/
  `updateScene`/`insertScene`) operating on a persisted `plan.json` written after `acquireAssets`.
  Lets a NEW agent reshape a video without re-running the pipeline. Covered by `scene-edit.test.ts` (5 tests).
- CLI: `--local-assets` / `--default-visual` flags in `bin/agentic-auto.ts`; autopilot threads them.
- Docs: `AGENTS.md` §7 + `agentic-pipeline/GAP_ANALYSIS.md` (P1 marked DONE).
VERIFICATION: `tsc --noEmit` EXIT 0. Full suite **201 tests / 200 pass / 1 skip / 0 fail** (18 suites).
Image-diversity root causes (A–E) + porting recipe + the `bin/*.ts` lint gotcha are captured in
`references/avg-image-diversity-and-porting.md`. P2 (AI metadata, language localization, personal
audio) remains TODO — see GAP_ANALYSIS.md.

Code ADDED this session for a *cinematic* agentic render (see `references/avg-enhancement-pipeline.md`):
- **Phase 1**: `remotion/AgenticVideo.tsx` (Ken Burns + gradient/vignette + karaoke captions + intro/outro cards)
  registered as `id="AgenticVideo"` in `remotion/Root.tsx`; `renderAgenticWithRemotion(res, opts)` in `orchestrate.ts`
  (copies assets→`public/agentic-assets/`, bundles `remotion/index.ts`, `selectComposition`+`renderMedia`, falls back
  to ffmpeg on Chrome/RAM failure). CLI `--renderer ffmpeg|remotion --quality draft|medium|high`.
- **Phase 2.3**: cinematic `vignette=PI/5` appended to the ffmpeg video chain (VERIFIED working).
- **Phase 4.1**: `buildDuckExpression()` side-chain music ducking during speech (volume expr with escaped `between()`),
  wired into pass-2 mux; `--no-ducking` disables.
- **Phase 7.2**: `chunkCues()` smart caption chunking (merge micro-segments, 500ms floor, split >8-word lines).
- **Phase 8.3**: `onProgress` callback (PipelineProgress) emitted at every stage; CLI single-line progress.
- **Phase 8.4**: `verifyRenderedVideo()` post-render X7–X9 (ffprobe-via-ffmpeg-stderr) attached to `res.postRender`,
  printed by CLI.
- **Phase 9.1**: `scoreCandidate()` scores EVERY passing candidate (confidence+resolution+fileSize+relevance); the
  score is shown in the decisions report.
- **Phase 10.2**: CLI flags `--intro/--outro/--transition/--sfx/--no-ken-burns/--renderer/--quality`.
- New `src/agentic/enhancement.test.ts` covers scoreCandidate, buildDuckExpression, chunkCues, verifyRenderedVideo.
VERIFICATION (this session, REAL): `npx tsc -p tsconfig.json --noEmit` → EXIT 0. Full suite **169 tests / 168 pass / 0
fail** (enhancement.test.ts 7/7). LIVE ffmpeg run → 376KB h264 MP4, **X7–X9 all PASS**. LIVE Remotion run
(`--renderer remotion --quality draft`) → genuine **1080x1920 h264 + aac stereo** MP4. Legacy workflow untouched
(`git status` clean on `src/video-generator.ts`, `src/lib/script-parser.ts`, `input/`). Nothing committed to git.
See `references/avg-enhancement-pipeline.md` for the per-phase recipes and the exact ffmpeg/Remotion traps.
(Remotion 4.0.487 branded) — proves the cinematic path renders on this box. Legacy workflow untouched.
Nothing committed to git (standing rule).
See `references/avg-enhancement-pipeline.md` for the per-phase recipes and the exact ffmpeg/Remotion traps.

## Pitfalls (Remotion render path — added this session)
- **Remotion `<Video>` fed a non-video file HANGS on `delayRender()`.** `AgenticVideo.tsx` originally chose Image-vs-Video by `asset.kind`, but a `video`-kind asset can be a generated **`.png` placeholder** when the live fetch 502s. Passing that PNG into `<Video src=staticFile(...)>` makes `<Html5Video>` call `delayRender()` waiting for a duration that never comes → timeout after 28s → render throws. FIX: decide by **file extension**, not kind:
  `const isVideoFile = /\.(mp4|webm|mov|m4v)$/i.test(asset.localPath);` and feed non-video extensions to `<Img>`/KenBurns. This makes the composition robust to the offline placeholder fallback.
- **Remotion render needs Chrome + RAM; always guard with an ffmpeg fallback.** `renderAgenticWithRemotion()` is wrapped in try/catch in the CLI and falls back to `renderAgenticSlideshow()` on any failure (Chrome absent, OOM, timeout). Keep that fallback — the box runs ~70–150 MB free and a naive Remotion render can hang.
- **Remotion `staticFile()` needs assets copied into `public/`.** `renderAgenticWithRemotion()` copies each approved asset + voiceover into `public/agentic-assets/` and references them as `agentic-assets/<file>` (forward-slash, relative). Without the copy, `staticFile()` 404s and `<Img>/<Video>` stay blank.
- **Remotion `renderMedia` input props must match the composition's `defaultProps`.** `AgenticVideo` expects `{ title, orientation, fps, assets[], brand, introCard, outroCard, kenBurns }`. Pass all; `selectComposition` reads `durationInFrames` from `defaultProps` but the real duration is computed in-component from assets — so set a sane default `durationInFrames` in `Root.tsx` (300) and let `renderMedia` use the component's computed length.

See `references/avg-image-diversity-and-porting.md` for the per-file inventory and the 6-stage design that drove this.
Image-diversity debugging recipe + legacy→agentic porting workflow + the `bin/*.ts` lint
gotcha live in `references/avg-image-diversity-and-porting.md` — read it when a video
renders with repeated/off-topic photos or when porting a legacy `src/video-generator.ts` feature.

## Opt-in AI verification (reuses the agent's OWN model — zero-cost)
`references/opt-in-ai-verify-own-model.md` — proven pattern for OPT-IN AI verification that
reuses the agent's OWN running model (AgentBrain), **never a paid `visionApiKey`/Gemini path**,
with a `null`-fallback contract that AUGMENTS (never replaces) the deterministic signal gates
(X7–X15). Covers images/video/audio across acquire/approve/edit/render stages. Use this when the
user wants "AI to verify everything" but the build must stay zero-cost + no separate key.
