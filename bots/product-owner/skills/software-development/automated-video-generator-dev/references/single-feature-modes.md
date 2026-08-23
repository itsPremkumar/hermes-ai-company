# Single-Feature Modes — API Map & Recipes

Dispatch: `src/agentic/operations/single-feature.ts:runSingleFeature(job, id, modeOverride?)`.
CLI: `npx tsx src/adapters/cli/agentic-batch.ts --mode <name> [--job <id>]`.
Per-job: set `"mode"` in `input/scripts/agentic-scripts.json`.

## Mode → underlying API (all REAL engines, no reimplementation)
| mode | calls | output dir under workspace/jobs/<id>/ |
|------|-------|----------------------------------------|
| `plan` | `buildPlan` (no network) | (none) |
| `download-images` | `fetchVisualsForScene(kw,false,orient,undefined,i)` + `downloadMedia` | `download-images/` |
| `download-videos` | `fetchVisualsForScene(kw,true,orient,undefined,i)` + `downloadMedia` | `download-videos/` |
| `download-music` | `resolveFreeBackgroundMusic({query})` (procedural fallback) | `download-music/` |
| `generate-voice-edgetts` | `generateAgenticVoiceovers` (Edge-TTS; SAPI offline fallback) | `voice-edgetts/` |
| `generate-voice-voicebox` | `runVoiceStageSafe` (kokoro/chatterbox; needs backend :17493) | `voice-voicebox/` |
| `clone-voice` | `cloneFromVoicesDir(clipPath, cacheFile)` (MUST be exported from `voice-controller.ts`) | `cache/voicebox-profile.json` |

## Per-mode job fields (in AgenticCliJob)
- `sceneIndices?: number[]` — restrict download-images/videos to these 0-based scenes.
- `edgeTtsVoice?: string` — override voice for `generate-voice-edgetts`.
- `kokoroVoice?: string` — set `VOICEBOX_PRESET_VOICE` for `generate-voice-voicebox`.
- `cloneVoiceFrom?: string` — filename in `input/voices/` for `clone-voice` (NOT `input/voiceover/`).
- `candidatesPerAsset` — how many candidates per scene/music track to fetch.

## Reference clip path gotcha
`clone-voice` resolves the clip as `path.resolve(cwd, 'input', 'voices', basename(clip))`.
Do NOT use `inputVoiceoverPath()` — that points at `input/voiceover/` and will report
"Reference clip not found". Drop the .wav/.mp3/.flac/.m4a into `input/voices/`.

## Expected degradation (NOT bugs)
- `generate-voice-voicebox` / `clone-voice` with backend down → `connect ECONNREFUSED 127.0.0.1:17493`.
  Start the vendored backend (`src/speech/`, venv `C:/one/voicebox/.venv/Scripts/python.exe`) to test for real.
- `generate-voice-edgetts` with no Edge-TTS runtime → falls back to Windows SAPI offline; still writes real WAVs.
- `download-music` with no stock source → `resolveFreeBackgroundMusic` returns procedural ambient (still a real mp3).

## Verification
`runSingleFeature` returns `{ mode, jobId, workspace, plan?, outputs: string[], summary }`.
Assert `outputs.length > 0` and each path exists on disk. Example jobs live in
`input/scripts/agentic-scripts.json` under ids `sf_images_only`, `sf_videos_only`,
`sf_music_only`, `sf_voice_edgetts`, `sf_voice_voicebox`, `sf_clone_voice`.
