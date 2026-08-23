# 2026-07-31 compose campaign — 3 bug classes (2 fixed + verified, 1 root-caused)

Campaign: render the 5 `agentic-scripts.json` jobs one-by-one via
`npx tsx src/adapters/cli/agentic-batch.ts --mode compose --job <id>` and verify
each output empirically (probe + pixel QA + frames). Found 3 real bugs. Two are
FIXED with regression tests; the third is root-caused with a fix direction.

---

## 1. ENAMETOOLONG — inline `-vf` with kinetic per-word captions silently drops ALL text (FIXED)

**Symptom:** log shows `⚠ overlay ffmpeg failed: ... ENAMETOOLONG`, `final.mp4`
exists and looks fine (probe passes) but has NO burned captions/intro/outro —
the failure is only logged, not fatal, so the video ships textless.

**Root cause:** the overlay stage built ONE giant inline `-vf` string. With
`kineticText:true` the caption stage emits one `drawtext` filter PER WORD × 7
scenes, plus title-card and outro drawtexts → the joined string exceeds the
Windows 32,767-char command-line limit → `spawnSync` throws ENAMETOOLONG.
Affects EVERY job with kinetic captions (all 5 jobs here).

**Fix (both render paths):**
- `src/agentic/operations/compose.ts` — overlay stage extracted to exported
  `applyOverlays(baseVideo, vf, outDir)`: writes the graph to
  `outDir/overlays_filter.txt` and passes **`-filter_script:v <file>`**
  (per-stream variant) instead of inline `-vf`; `finally` removes the script
  file. Returns `overlays.mp4` on success, unchanged `baseVideo` on failure.
- `src/agentic/orchestrator/render.ts` pass1 (~line 944) — same latent class:
  full-chain `-filter_complex` (xfade × scenes + per-word kinetic + audio).
  Switched to **`-filter_complex_script <file>`** (complex-graph variant),
  cleaned up in `finally`.

`-filter_script:v` / `-filter_complex_script` are core ffmpeg options (present
in ffmpeg-static 6.1.1 gyan.dev build — verified). Rule: ANY filtergraph whose
length scales with scene count × caption words must go through a script FILE,
never inline.

**Regression test:** `src/agentic/operations/compose-regression.test.ts`
(`applyOverlays` case) builds 500 `drawbox` filters (chain > 32,767 chars —
asserted as a test precondition so the test can't silently weaken), calls
`applyOverlays` on a real 3s clip, asserts: returned path is `overlays.mp4`
(NOT the base — the old code fell back silently), filter script file removed,
output duration ≈ 3s.

---

## 2. xfade offset off-by-one — 7 scenes render as one scene's length, ffmpeg EXITS 0 (FIXED)

**Symptom:** `final.mp4` is ~8.08s when the 7 `scene_*.mp4` clips sum to ~51s.
NO error anywhere — `crossfadeSlideshow` returns success. The truncated video
passes ffprobe dimension checks.

**Root cause (`compose.ts` `crossfadeSlideshow`):** the loop pushed each xfade
with `offset` BEFORE incrementing it. So transition 1 fired at `offset=0`
(instant fade at t=0), and every later offset was one scene early. The xfade
chain degenerates (each stage's first input is shorter than the next offset) →
ffmpeg produces a valid-looking short file and exits 0. **Silent truncation:
xfade offset bugs do NOT error — assert output duration.**

Correct math: offset for transition i = `sum(dur[0..i-1]) - i*segDur`, i.e.
`offset += durOf(i-1) - segDur` must run BEFORE emitting the transition.
(`render.ts`'s `cursor`-based version was already correct — only compose.ts had
the bug.)

**Repro that proved it:** replayed the as-written filter string standalone →
8.08s (identical to broken base.mp4); same chain with corrected offsets → 48.6s.

**Verification rule:** after any slideshow/xfade change,
`ffprobe -show_entries format=duration` must be ≈ `Σ scene durations -
(n-1)*segDur`. The old off-by-one produced 8.08s ≈ one scene — the duration
assertion catches it.

**Regression test:** exported `crossfadeSlideshow` (was module-private), drove
it with 3 lavfi color-card clips (2s each, durations [2,2,2], fade+slide,
segDur 0.4) → assert output 5.2s (±1s), NOT ~2.08s. Export the function under
test — private functions can't be regression-tested.

---

## 3. Voice-group 25s timeout discards valid SAPI speech → whole video gets 220Hz tone "voice" (ROOT-CAUSED, fix pending)

**Symptom:** final audio maxes at ~-16.7 dB while the source voice WAVs are
-0.3 dB (hot). Compose log says `voice=tts` and voice-gen says "Successful:
7/7" — both LIE about voiceover quality.

**Traceback (mtime + content forensics):**
1. `audio/scene_N_voice.wav` (Windows SAPI output) = REAL speech, peak -0.3 dB.
2. But `compose/audio_list.txt` fed `voice_concat.aac` with files from
   `workspace/tmp/tone-fallback/vo_*.wav` — 220Hz sine at `volume=0.15` →
   peak exactly -34.5 dB, zero-crossing rate ~0.01 (pure tone; speech is ~0.1).
3. Root cause: `src/agentic/media/tts.ts` wraps the whole Edge-TTS voice GROUP
   in `withTimeout(..., 25_000)`. The Windows offline speech (SAPI) fallback
   (`src/lib/voice-generator.ts` `runPowerShellEncodedAsync`) legitimately takes
   up to 120s per scene. The group times out mid-batch → the rejection empties
   `allResults` → `fillMissing()` substitutes tones for EVERY scene — even
   though SAPI actually finished writing real speech files to `audio/`.

**Fingerprint recipe (tone vs speech — do this, don't trust the log):**
```bash
ffmpeg -hide_banner -i <wav> -af astats -f null - 2>&1 | grep -E "Peak level dB|Zero crossings rate"
# tone:    Peak ≈ -34.5 dB, Zero crossings rate ≈ 0.01 (220 Hz sine @ volume=0.15)
# speech:  Peak ≈ -0.3 dB,  Zero crossings rate ≈ 0.05–0.2
```
Also verify the concat LIST: `cat compose/audio_list.txt` — if entries point at
`workspace/tmp/tone-fallback/` instead of `audio/scene_N_voice.wav`, the voice
stage degraded. Check file mtimes to see which run created cached tone files
(jobs can REUSE a prior run's tone files via shared cache paths).

**Fix direction (not yet applied):** collect per-scene SAPI results as they
complete (resolve the group when all scenes settle, don't reject the batch on a
25s timer), or raise/remove the group timeout for the SAPI path, or have
`fillMissing` prefer an existing `audio/scene_N_voice.wav` before synthesizing a
tone. Add an astats-based regression test asserting voice files are speech
(zero-crossing rate > 0.02), not tones.

---

## Campaign verification battery (worked well, reuse)

When `vision_analyze` is unavailable (provider without image support), the
pixel-level QA battery per rendered job:
1. `cropdetect=limit=16:round=2` (run with `-v info`; `-v error` suppresses the
   crop= lines) → only trivial `crop=W:H:0:0` = no bars.
2. `blackdetect=d=0.5:pic_th=0.98` → 0 black frames.
3. `freezedetect=n=0.02:d=2` → 0 freeze segments (use n=0.02, not 0.001 — see
   pitfall #57 on Ken Burns false positives).
4. `volumedetect` with `-v verbose` → mean -20..-25 dB healthy.
5. `signalstats` YAVG mid-range (~100-130) = content present, not black/blown.
6. Frame-variety: extract at 3 timestamps → file sizes differ.
7. Caption-strip text presence: crop the caption region
   (`crop=W:220:0:H-220`), threshold `format=gray,geq='if(gt(lum(X,Y),180),255,0)'`,
   then YAVG ≈ 25-30% = white text pixels present. (Signals text is burned;
   vision is still the only full proof.)
8. Audio content: astats zero-crossings + peak (see bug 3 fingerprint).
