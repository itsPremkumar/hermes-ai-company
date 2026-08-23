# AVS duration / voice / audio-mix bug chain (2026-08-01)

Context: user asked for a ~5-minute video ("different combinations", 19-scene
documentary, voiceover-driven durations). Renders came back 79.9s → 158s →
149.98s → 291.5s-video-but-59.9s-music-only-audio before the class was fixed.
Each fix looked "done" until the next consumer re-clobbered the value. Fix the
CLASS: duration precedence + voice-mix wiring, not individual sites.

## Symptom → root-cause table (the 7-bug chain)

| # | Symptom | Root cause | Fix |
|---|---------|-----------|-----|
| 1 | Run 2 (158s) reused run 1's 2.1–2.9s WAVs for scenes 1–18 | `voice-generator.ts` `resolveExistingAudio` (~L103) reused ANY WAV >1000B, no text match | `.txt-hash` sidecar per WAV, written at all 4 synthesis paths (Kokoro/Voicebox/XTTS/SAPI ~L257-312, 549, 614); reuse only on hash match, else delete + regenerate |
| 2 | Scenes capped at 8s / `\|\| 4` | `agentic-modular.ts` voiceScenes used plan `s.durationSec \|\| 4` instead of real WAV length | `estimateAudioDurationSafe(realWav)`; sync `asset.durationSec` |
| 3 | 19×8s ≈ 152s render despite 296s of full WAVs | `render.ts` asset loop overwrote WAV-derived `v.durationSec` with plan `durationSec` whenever positive | Voiceover duration wins; plan only when no voiceover |
| 4 | Still 152s | `durOf()` (`render.ts` ~L633) `plan.scenes[i].durationSec \|\| a.durationSec \|\| 4` | Flip to `a.durationSec ?? plan ?? 4` |
| 5 | Still 150.0s EXACT (suspiciously round) | Segmented branch `dur:` (`render.ts` ~L787) plan-first again | Flip to `a.durationSec ?? plan ?? 4` |
| 6 | 291.5s video BUT audio = 59.9s (music length, no narration) | Segmented path: segments video-only, `-c copy` concat has NO audio stream → final music pass `silentHasAudio=false` → music ALONE | Post-concat voice-attach pass: per-scene adelay → amix `duration=longest` + `apad` → limiter, `-c:v copy`; then music pass ducks under `[0:a]` |
| 7 | `Invalid stream specifier: vv0` fatal | My filtergraph joined only the `[vvN]` labels, dropped the `adelay` producer strings | `vDelays.join(';') + ';' + labels + 'amix=...'` |
| 8 | Voice-attach pass encodes FOREVER (7-min runaway `time=07:06` at 620×, size plateaued ~28MB, `ffmpeg failed (exit 1)` at render.ts:590) | `amix=duration=longest` ends at the last WAV (~345s) but `apad` pads the audio INFINITELY; the pass had NO `-shortest`, so the mux never stopped (music pass has `-shortest`, this one didn't) | Add `-shortest` to the voice-attach args (video is the shortest stream → mux stops at video length), or drop the unbounded `apad` |
| 9 | "concat failed" AFTER all segments rendered (7 min wasted): `File '..._av_<jobId>.mp4' already exists. Overwrite? [y/N]` | `-c copy` concat args had NO `-y`; a leftover `_av_*.mp4` from a killed/crashed run makes ffmpeg prompt → non-TTY stdin answers N | `-y` on the concat args (and every intermediate write); clean `_av_*`/`_seg_*`/`_concat_*` from `workspace/jobs/<id>/render/` before re-running after a crash |

Companion latent bug found in the same pass: music-branch amix used
`duration=shortest` + `-shortest` flag — would cut narration to music length AND
truncate the video. Changed to `duration=longest` + `apad` in ALL branches
(music+sfx, music-only, sfx-only, and the flat-volume fallback).

## Empirical probes that isolate each layer (no vision model needed)

1. **Per-stream ffprobe** — which stream is capped:
   `ffprobe -v error -show_entries stream=codec_type,duration -of default=noprint_wrappers=1 V`
   Read as: video=291.5s / audio=59.9s / data(chapters)=344.9s → audio is the
   broken stream (chapters carry the INTENDED timeline, great ground truth).
2. **SRT last timestamp = the renderer's ACTUAL duration chain.**
   `tail -4 <job>/archive/_captions_<job>.srt` — if SRT spans 297.5s but the
   video is 150s, the COMPOSE (not the caption/timing layer) cut it.
3. **WAV mtime check for cache-hit proof** (avoid racing file writes):
   `ls -la --time-style=+%H:%M:%S` + `date "+now: %H:%M:%S"` — old mtime +
   log shows "falling back" = instant cache hit (the log line prints BEFORE the
   wrapper's cache return — misleading).
4. **Plan-text hash vs sidecar** — cache validity:
   node one-liner: `hashText(plan.scenes[i].voiceoverText)` (djb2
   `h=((h<<5)+h+c)>>>0` base36) vs `fs.readFileSync('<wav>.txt-hash')`.
5. **Run the EXACT in-memory logic against workspace files** in a node probe
   (`workspace/probe_duration.js`): simulate the renderer's asset loop on
   `render-manifest.json` + plan + audio dir → if the probe yields 293.5s but
   the render yields 150s, the mismatch is in wiring not math.
6. **Direct SAPI probe** to isolate TTS vs cache:
   `Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Rate=0; $s.SetOutputToWaveFile(...); $s.Speak($text)`
   → 15.79s for a 220-char line proved the synthesizer was fine, the truncation
   was upstream (cache).

## Correct filter patterns (proven on gyan.dev Windows ffmpeg)

Voice-attach pass after segmented concat (inputs: `-i silent` = 0, then WAVs):

```
[1:a]adelay=delays=<sceneStartMs>:all=1[vv0];...;[vv0][vv1]...amix=inputs=N:duration=longest:normalize=0[vmix];[vmix]apad[vap];[vap]alimiter=limit=0.7:asc=1:level=disabled[voout]
args: -map 0:v:0 -map [voout] -c:v copy -c:a aac -b:a 192k -shortest -y
```

⚠ The `-shortest` (and `-y`) are MANDATORY on this pass (bug #8/#9): without
`-shortest`, `apad` after `duration=longest` creates an infinite audio stream
and the encode never ends; without `-y`, a leftover `_av_*.mp4` makes ffmpeg
prompt "Overwrite?" and fail on non-TTY stdin.

Music pass with voice present on `[0:a]`:

```
[1:a]volume=eval=frame:volume='<duckExpr>'[a];[0:a][a]amix=inputs=2:duration=longest:normalize=0[amixout];[amixout]apad[ap];[ap]alimiter=limit=0.7:asc=1:level=disabled[aout]
```

Scene start time: `introDur + offsetFor(visuals, i, xf)`, jCut applied to the
first scene only (`audioStart = max(0, picStart - (i===0 ? 0 : jCut))`).

## Verification recipe for a long (voiceover-driven) render

- Expect: video duration ≈ sum of WAV lengths (ffprobe), audio duration ≈ video
  duration (NOT music length), SRT spans the full timeline, 20+ chapter markers.
- If video ≈ 19×8s exactly → plan-duration clobber (bug class #2–5): grep every
  `durationSec` consumer in render.ts + agentic-modular.ts, make each asset-first.
- If audio = music length → voice never mixed (bug #6): check the concat's audio
  presence, then the post-concat voice attach.
- Keep all `_seg_*`/`_av_*`/`_fc_*` intermediates under `workspace/jobs/<id>/`
  (git-ignored); they get cleaned up by the renderer, but a failed run leaves
  them — delete before re-running.
