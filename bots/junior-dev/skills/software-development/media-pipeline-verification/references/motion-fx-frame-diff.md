# Motion-FX verification via per-scene PSNR frame-diff (AVS bug hunt, 2026-07)

Proving an ffmpeg motion effect (shake / speed-ramp / punch-in / parallax) actually
CHANGED the output — and only in the target scene — without eyeballing frames.

## Method
1. Render a no-FX baseline and one video per FX via the same driver
   (`workspace/bug-hunt/compose-direct.mjs` calls composeVideo() directly).
2. Compare per scene-time-window with PSNR (robust, one number):
   ```
   ffmpeg -ss T -t 1.5 -i fx.mp4 -ss T -t 1.5 -i base.mp4 -lavfi psnr -f null - 2>&1 | grep -oP 'average:\S+'
   ```
   - `average:inf` = bit-identical → FX was a SILENT NO-OP for that scene.
   - ~40–57 dB = encoder noise / negligible; <30 dB = real visual change.
   - Shake at intensity 0.6 gave ~17 dB in its scene, 53–57 dB elsewhere → correct scoping.
3. Black-edge check for crop-jitter effects (shake): probe 4px edge strips —
   `-vf "crop=W:4:0:0,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-"`,
   take the MIN YAVG across frames. Near-0 min = black border leaking in.
4. Unit-probe each applyX() with tsx to isolate FX-function bugs from wiring bugs:
   check returned path (`=== input` means no-op) + ffprobe duration/dims of output.

## Pitfalls (cost time this session)
- **STALE BASELINE**: the driver overwrites a shared `compose-out/final.mp4`; a
  leftover baseline from an earlier differently-configured run had different
  dimensions (720x720 vs 720x1280) → all PSNR calls failed with
  "Failed to configure input pad" (psnr requires equal dims). Always RE-RENDER the
  baseline in the same batch as the FX runs.
- `blend=difference,signalstats` piped to awk failed silently on Windows/MSYS
  (metadata:file=- ordering); plain `-lavfi psnr` is more reliable.
- `npx tsx -e "await import(...)"` fails (CJS top-level await); write a .mts probe
  file and import the module via `import mod from '...'; const {fn} = mod as any`
  (named imports of these AVS operation modules also failed).

## Recurrent bug classes found (add to your hypothesis list)
- **Value-type no-op**: field documented as number but code branches
  `typeof v === 'string' ? presets[v] : [v.from, v.to]` — a plain number hits the
  object branch, `.from` undefined → defaults → silent no-op. ALWAYS test the most
  natural value type the docs suggest.
- **setpts speed-ramp math**: `setpts='PTS*f(T)'` (multiplying PTS by a time-varying
  factor) is WRONG — correct variable speed needs the integral of 1/speed(t).
  Symptoms: non-monotonic PTS → mass frame drops (8s→2.6s for a 1→2 ramp), or
  absurd durations (8s→26.8s for 1→0.4). Verify with ffprobe duration vs the
  analytic integral.
- **Field dropped in CLI wiring**: FX works when the operation fn is called
  directly but the field never appears in the CLI job type / PipelineRequest
  forwarding list → grep the field name across cli-job.ts + orchestrator types;
  count 0 = the smoking gun.
- **Clamp mangles intent silently**: `Math.max(1.05, zoom)` turns a user's 0.4
  into 1.05 with no warning — check clamps against plausible misuse values.
- **zoompan d=1 resets `zoom` per frame** → no progressive zoom/drift; "parallax"
  becomes a static micro-crop. Any zoompan animation needs d>1 or expressions in
  `on`/time, and explicit centered x/y.
