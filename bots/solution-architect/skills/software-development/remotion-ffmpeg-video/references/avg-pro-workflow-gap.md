# AVG vs. Professional Video-Editor Workflow (20-stage gap map)

Produced in the 2026-07-17 session by auditing the ACTUAL code (not docs) against
the user's "complete professional editor workflow" prompt. Use this to decide what
to build next — the already-covered stages are done; the NOT-done stages are the
real backlog. The AVG pipeline is a ZERO-COST, NO-API-KEY, autonomous short-form
generator, so some "professional" stages are intentionally out of scope.

## Stage status (Done / Partial / Not done) — verified against code

| # | Stage | Status | What exists in code |
|---|---|---|---|
| 1 | Client brief / branding / deliverables | Partial | topic+title only; branding = watermark/logo config. No brief-intake UI. |
| 2 | Project setup / storage / backup / version | Partial | per-job isolated workspace (`workspace.ts`) + `pruneWorkspaces()`. No backup/archive/version. |
| 3 | Import / verify / proxy / sync / bins / metadata | Partial | downloads stock (Pexels→Pixabay→Wikimedia→Archive→Openverse ladder, P31) + verifies (`media-verifier`, `asset-checks`). NO proxy/transcode/bin/metadata tagging. |
| 4 | Footage review / logging / best-take | Not done | N/A — stock+AI, not dailies. No clip logging. |
| 5 | Story / pacing / narrative / continuity | Partial | script→scenes (`plan.ts`) + mood heuristic + AgentBrain. No emotion-pacing craft. |
| 6 | Assembly → rough cut | Done | Remotion builds timeline from plan (`AgenticVideo.tsx`). |
| 7 | Fine cut / frame-trim / polish | Partial | timing from script duration + speed-ramp. No manual trim UI. |
| 8 | J/L-cuts, match/montage/parallel/multicam, speed-ramp, freeze, stabil | Partial | speed-ramp, Ken-Burns, punch-in, shake, parallax, match-cut, morph-cut. NO J/L-cut, multicam, montage, stabilization, freeze-frame UI. |
| 9 | VFX / compositing / keying / rotoscoping / object removal / tracking | Not done | zero. (grep "composit/tracker" were false positives on "composition".) |
| 10 | Motion gfx / titles / lower-thirds / infographics / kinetic | Partial | lower-third, dynamic captions, typewriter, watermark, progress-bar, safe-zones. NO infographics/UI-animation/kinetic design system. |
| 11 | Audio: dialogue repair / EQ / comp / de-ess / Foley / mix / LUFS | Partial | SFX gen, beat-sync, audio-ducking, LUFS normalize, ambience, free BGM. VO is TTS (already clean) so dialogue repair is moot. |
| 12 | Color: correction / WB / exposure / shot-match / skin / LUT / HDR | Partial | LUT loader (.cube/.3dl), color-wheels (lift/gamma/gain), film-grain, halation. NO auto WB/exposure, shot-match, skin-tone, HDR. |
| 13 | Subtitles / captions / localization / accessibility | Partial | burned-in dynamic captions (DONE: `tts.ts`+`src/lib/captions.ts` write `.srt`/`.vtt` with tests). NO sidecar-SRT delivery wrapper, NO multi-language, NO accessibility compliance. |
| 14 | Pro QC / frame-check / sync / spelling / safe / artifacts | Partial | verification gate (`gate.ts`) + `video-analyzer` (X7–X15) + contact-sheet. NO frame-by-frame human QC / platform-compliance matrix. |
| 15 | Export / codec / bitrate / broadcast / streaming / archive master | Done | `export.ts`: multi-aspect (TikTok/Reels/Shorts/landscape), thumbnails, free metadata. Codec/bitrate = Remotion defaults, not per-platform tuned UI. |
| 16 | Client review / revisions / approval / collab | NOW DONE | `src/agentic/revision.ts` (this session): state machine draft→in_review→changes_requested→approved, structured change hints, persisted `revision-state.json`. |
| 17 | Final delivery / packaging / cloud / invoice / handoff | Partial | local multi-aspect outputs. NO cloud packaging / invoice / handoff doc. |
| 18 | Archiving / consolidation / backup verification | NOW DONE | `src/agentic/archive.ts` (this session): copies deliverables+source assets into `<ws>/archive/`, writes `archive-manifest.json` (role/size/sha1), `verifyArchive()` re-checks integrity. |
| 19 | Collaboration with director/colorist/sound/VFX | Partial | single autonomous pipeline; "collaborators" are internal plugins. No multi-human role handoff. |

## Easiest-to-build backlog (Tier ranking — no ML/keys needed)

- Tier 1 (hours, pure logic, no media): sidecar SRT delivery wrapper (stage 13 — .srt already exists, just wire a delivery path), multi-language voiceover via Edge-TTS free voices (`tts.ts`+`config.ts`), client revision loop (stage 16 — DONE this session), archive/consolidation (stage 18 — DONE this session).
- Tier 2 (medium, ffmpeg/Remotion): auto white-balance/exposure (ffmpeg `eq`/`colortemperature` — note P10 `eq` has no `temperature`!), freeze-frame hold (Remotion `freeze()`), platform-compliance QC auto-check (extend `gate.ts`).
- Tier 3 (hard, AVOID in zero-cost stack): VFX rotoscoping/object-removal/3D-tracking (needs ML), HDR encode, full multicam sync, real dialogue repair (moot — TTS is clean).

## Key truth for future agents
SRT/VTT captions (stage 13) were ALREADY implemented before this session — do NOT
rebuild them. The two genuinely-missing Tier-1 items this session were stage 16
(revision loop) and stage 18 (archive), now added. When extending the pipeline,
grep the real code first: features that "sound missing" are often already there
(e.g. captions, multi-aspect export, LUTs).
