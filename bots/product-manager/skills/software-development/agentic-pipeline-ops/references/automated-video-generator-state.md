# Automated-Video-Generator — Agentic Layer State (updated 2026-07-18)

Local copy: `C:\one\Automated-Video-Generator` (itsPremkumar/Automated-Video-Generator, TS/Node).

## Command surface (verified by reading source, not guessing)
- **MCP agentic tools** — `src/adapters/mcp/register-agentic-tools.ts`:
  `agentic_plan`, `agentic_acquire`, `agentic_verify_all`, `list_pending_assets`,
  `get_asset_preview`, `approve_asset`, `reject_asset`, `agentic_gate`, `agentic_run`.
  These are STAGE tools — an agent can pause *between* stages, but every path
  still requires the full pipeline to yield a deliverable.
- **Bin entrypoint** — `bin/agentic-run.ts`: all-or-nothing
  `--topic "..."` -> full MP4. Flags: `--backend agent|vision`, `--orientation`,
  `--images|--videos`, `--renderer ffmpeg|remotion`, `--quality`, `--intro/--outro`,
  `--transition`, `--sfx`, `--no-ducking`, `--no-ken-burns`, `--dry-run`, `--preset`.
- **Shared brain** — `src/agentic/brain.ts` AgentBrain (free OpenRouter/Ollama,
  always falls back to heuristic; never crashes/hangs on model).
- **Plugins** — `src/agentic/plugins/` (watermark, LUT, captions, ducking,
  transitions, genres, platforms) registered via `agentic-plugins.config.json`.

## Discrete-ops layer — BUILT (this is the answer to "do only this part")
Created `src/agentic/operations/` + wired into `mcp-server.ts` via
`register-operations-tools.ts`. Committed + pushed (7eb3624) for the first
pass; a SECOND pass added the remaining ops + chain router (see "Second pass"
below — as of the last session it was CODE-COMPLETE but NOT yet re-verified
green due to a register-file syntax cascade; see write-file-corruption.md).

First pass (verified green, 16/16 tests, tsc clean, pushed 7eb3624):
- `edit.ts`: mergeVideos, trimVideo, cropVideo, resizeVideo, rotateVideo, extractAudio
- `voiceover.ts`: generateVoiceoverOnly (wraps Edge-TTS)
- `download-media.ts`: downloadImageByKeyword, downloadVideoByKeyword (free fetchers)
- `route.ts`: heuristic intent classifier (plain language -> single task)
- `dispatch.ts`: runs ONLY the routed task; falls back to full pipeline only for `full_video`
- `register-operations-tools.ts`: `do_task` router + merge_videos/trim_video/crop_video/
  resize_video/rotate_video/extract_audio/make_voiceover/download_image/download_video
- tests: operations.test.ts (real ffmpeg) + route.test.ts (classification)

Second pass (built, NOT yet green-verified at session end):
- `split.ts` (split_video), `captions.ts` (add_captions), `audio-track.ts`
  (add_music/add_audio_track), `localize.ts` (localize_video), `grade.ts`
  (grade_video), `motion.ts` (slow_motion/speed_ramp), `overlay.ts`
  (add_watermark/add_lower_third/add_progress_bar), `derivative.ts` (derive_outputs)
- `route.ts` upgraded: ~20 task kinds + file-path extraction + 2-step CHAIN
  detection ("crop then add music")
- `dispatch.ts` upgraded: runs chains (each step's output feeds the next) +
  quality-gates every video-producing step with verifyRenderedVideo
- `register-operations-tools.ts`: ~20 granular tools + `do_task` router
- REMAINING TO CLOSE before commit: dispatch.ts needs `import * as path` (used
  in runChain) OR the path ref removed; operations.test.ts + route.test.ts must
  type-narrow the `RoutedTask | RoutedChain` union (isChain guard). Then
  `npx tsc --noEmit` clean + real-ffmpeg tests + commit + push.

## User mandate (standing, from memory + repeated this session)
- ZERO-COST / NO paid API keys: Edge-TTS + ffmpeg-static + existing free fetchers only.
- Commit ONLY at a green checkpoint (tsc + real tests), push to itsPremkumar.
- Agentic layer must INHERIT every working legacy capability (additive, not replace).

## Tooling pitfall (host-specific)
`search_files` (rg) intermittently fails on Windows/MSYS paths with
`rg: ... The system cannot find the path specified. (os error 3)` even when the
dir exists. Use `terminal` + `grep -rniE "pattern" <path> --include=*.ts` instead.
See references/windows-ffmpeg-verify.md and references/write-file-corruption.md.
