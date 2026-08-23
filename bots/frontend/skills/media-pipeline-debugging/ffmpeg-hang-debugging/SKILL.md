---
name: ffmpeg-hang-debugging
description: Diagnose ffmpeg commands that hang or encode forever.
---

# ffmpeg-hang-debugging

## When to use
- A render or test times out partway (e.g. `· render 79%` then never completes).
- An ffmpeg invocation runs far longer than the source duration (minutes for a 4s clip).
- A pipeline step "hangs" with no error — just silent non-termination.
- You suspect a filter graph or muxer option makes ffmpeg wait on a stream that never EOFs.

## The core method — do this BEFORE patching orchestration code
1. **Isolate the exact ffmpeg command.** Find which `runFfmpegSpawn` / `execFile` / `spawn` call is stuck. The progress `%` usually comes from parsing `time=HH:MM:SS` in stderr. If it climbs past the source length, the encode is *runaway*, not merely slow.
2. **Build minimal repro inputs.** Recreate the smallest version of each input:
   - silent video: `ffmpeg -f lavfi -i color=c=navy:s=720x1280:d=4 -c:v libx264 -pix_fmt yuv420p -t 4 -y silent.mp4`
   - tone WAV: `ffmpeg -f lavfi -i "sine=frequency=330:duration=2" -c:a pcm_s16le -y a.wav`
3. **Run the EXACT `filter_complex` standalone with a hard timeout + watchdog.** On bash: `timeout 25 ffmpeg <args> 2>log.txt`. If it hits the timeout, it is a real hang, not slowness.
4. **Read the stderr `time=` line.** A healthy 4s job shows `time=00:00:04.xx` then exits. A runaway shows `time=00:02:00`, `00:06:06`, `00:43:07`… climbing indefinitely — the muxer is waiting on a stream that never ends.
5. **Fix at the ffmpeg-arg level, verify the repro exits 0 and produces BOTH expected streams, THEN apply to source.** Never patch the orchestrator blind.

## The trap this session hit (verified)
**Symptom:** a render path concatenated per-scene video segments into a *silent* (video-only) MP4, then a voice-mix block muxed per-scene voice WAVs via `amix` and copied the video. The test hung at "render 79%" forever (240s timeout).

**Root cause:** the silent video (from `-c copy` concat) has **no audio track**. The filter used `amix=inputs=N:duration=longest`. `duration=longest` only governs how `amix` pads the *mixed audio* — it does NOT bound the *video* output. With the video stream copied (`-c:v copy`) and no `-shortest`/`-t`, ffmpeg keeps the muxer open waiting on the video's (nonexistent) audio and copies the video stream forever. Observed: **4h+ of output for a 4-second source.**

**Fix:** add `-shortest` to the output args so the encode caps at the shortest stream (the video). Verified: exit 0, produced a 4.00s MP4 with both `Video:` and `Audio:` streams.

**Rule of thumb:** whenever you `-map` a copied video AND mix/process only the audio with `duration=longest`, you MUST add `-shortest` (or `-t <videoDur>`) or the video encodes forever.

## Why empirical repro first (not guessing)
- A test timeout tells you *something* hangs; it does NOT tell you *which* ffmpeg arg. Guessing wastes a full 8-minute suite re-run per iteration and risks OOM on low-RAM boxes.
- A 25s standalone repro with `timeout` isolates the bad arg in one cheap iteration and gives you the `time=` evidence to prove the fix.

## Pitfalls
- `duration=longest` on `amix` does NOT bound video output — only the mixed-audio length. Always pair video-copy + audio-mix with `-shortest`.
- `-c copy` of a concatenated silent video yields a video with NO audio track; downstream audio filters then have no reference and the muxer can wait forever.
- Do NOT add `-threads 1` to "fix" a hang — it bounds RAM, not runtime. A hang is a muxer/stream-EOF issue, not CPU.
- On low-RAM boxes, run the SINGLE failing test file (`node --import tsx --test --test-timeout=120000 "path/to/test.test.ts"`) instead of the full suite.
- `runFfmpegSpawn` wrappers that resolve only on `cp.on('close', code===0)` with no timeout will hang the whole test if ffmpeg never closes — the watchdog repro is how you find it.

## References
- `references/ffmpeg-hang-repro.md` — the exact reproduction recipe + observed evidence (AVS `render.test.ts` hang).
- `scripts/ffmpeg-watchdog.sh` — run any ffmpeg command under a hard timeout and flag a runaway encode via stderr `time=`.
