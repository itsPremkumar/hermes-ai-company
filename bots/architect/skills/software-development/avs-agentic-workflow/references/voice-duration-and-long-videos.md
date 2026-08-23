# Voice-driven scene length & long-video authoring (AVS)

## The core mechanism: scene duration = voiceover duration
On the MODULAR CLI path (`agentic-modular.ts` plan → voice → visuals → render), each
scene's final length is the duration of its synthesized narration WAV. The planner's
`durationSec` (default 8s) is only a fallback. Consequences:

- **To make a LONG video, write LONG narration** — ~40 words/scene ≈ 16s at SAPI
  Rate 0. 19 scenes × 16s ≈ 5 minutes. There is NO reliable `minSceneDuration` padding
  on this path: `minSceneDuration` / `maxSceneDuration` / `sceneDurationByScene` are
  documented job fields but NOT wired into the modular CLI (grep agentic-modular.ts —
  zero matches). Don't waste a render cycle testing them.
- **The renderer sizes visuals from `manifest.assets[].durationSec`**
  (`orchestrator/render.ts`: `visuals[i].durationSec ?? 4`), not from plan.json.
  The modular voice stage now syncs real WAV durations there (fix 2026-08-01:
  voiceScenes builder + `result.manifest.assets[].durationSec` sync in
  `agentic-modular.ts`).
- The orchestrator path (`orchestrator/pipeline.ts:578-586`) already did
  `estimateAudioDurationSafe` per asset; the modular path did NOT until the fix —
  a 16s narration was silently cut at the plan's 8s default.

## Voice cache: text-hash sidecars (stale-WAV bug fixed 2026-08-01)
`resolveExistingAudio` (`src/lib/voice-generator.ts:103`) previously reused ANY
existing WAV/MP3 >1000 bytes **regardless of the script text it was generated from**.
Re-running a job with CHANGED narration silently kept the OLD short speech. Symptom
this session: 40-word lines rendered as 2.5s audio; the ONLY scene that sounded right
was a newly added scene 19 (no stale file existed → synthesized fresh at 12.5s).

Fix now in the code:
- every generated voice file gets a `<file>.txt-hash` sidecar (djb2 hash of the exact
  voiceover text);
- reuse only when the sidecar matches; stale files are DELETED → regenerated;
- sidecars written on all 4 fresh-generation paths (Kokoro, Voicebox, XTTS, SAPI).

**Debugging rule:** when re-run audio sounds wrong/short, ffprobe each
`scene_N_voice.wav` and check the `.txt-hash` sidecars BEFORE blaming SAPI or Edge-TTS.
Also compare total voice time against the WAV sum: a run that claims 19 scenes but
sums far under the expected narration length = cache reuse, not synthesis.

## Windows SAPI probe (empirical, for isolating voice bugs)
Plain `powershell.exe -Command "...New-Object System.Speech.Synthesis.SpeechSynthesizer..."`
throws `Cannot find type [System.Speech.Synthesis.SpeechSynthesizer]` — the assembly is
NOT auto-loaded. Required: `Add-Type -AssemblyName System.Speech` first. Minimal working
probe (write a `.ps1` under `workspace/`, run with
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File <path>`):

```powershell
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = 0
$synth.SetOutputToWaveFile("C:\one\Automated-Video-Generator\workspace\sapi_probe.wav")
$synth.Speak("<text>")
$synth.Dispose()
```
Then measure: `ffprobe -v error -show_entries format=duration -of
default=noprint_wrappers=1:nokey=1 <wav>`. SAPI at Rate=0 speaks ~14 chars/s — a
220-char line ≈ 15.8s. If a pipeline WAV is ~2.5s for a long line, it is NOT SAPI —
it's the cache (above) or truncation upstream.

## 5-minute "everything combined" video recipe (proven shape, 2026-08-01)
- 19 scenes, ~38-42 words each (~650-750 words total ≈ 4:45-5:30 at SAPI Rate 0).
- ~12 unique images staged in `input/visuals/` (Pollinations AI `sana` + Pexels
  photos), each bound with `[Visual: file]`, re-used ~1.5× across scenes.
- Layer the full feature surface in ONE job: per-scene `[Filter: bw|sepia|vintage]`,
  `[Grade: warm|cool|cinematic|vivid]`, `[Transition: zoomblur|glitch|lightleak|
  fade|dissolve|slide|fadeblack]`, one `[KenBurns: off]` still for contrast,
  kineticText, burned captions, vignette, sfx on cut, duckDepth, progressBar,
  hookFirst, intro/outro cards, contactSheet, posterScene.
- Render in the background (`npm run agentic:modular pipeline -- --file
  input/scripts/<job>.json`), then verify: total duration ffprobe, per-scene WAV
  lengths, frame QA (freeze hits → check against intentional stills), copy to
  `C:\Users\PREM KUMAR\Downloads`.
- Job file referenced: `input/scripts/five-min.json` (uncommitted).
