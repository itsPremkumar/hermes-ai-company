# Vision Text-Hallucination & Placeholder-Acceptance QA

Recipes proven 2026-07-28 during the production-hardening matrix run, where
vision models repeatedly "saw" the string `candidate_1` burned into rendered
videos. Pixel ground-truth proved the text was NOT present — the model had
pattern-matched a filename from the prompt context onto the pixels.

## 1. The trap: filename in the prompt primes the model

Both the auxiliary vision model and the agent's own `vision_analyze` reported
`candidate_1` "burned into the center" of every video frame, across
Kids-story / Tech-review / Travel. The asset PNG (`candidate_1.png`) actually
has NO text, and no `drawtext` call in `compose.ts` uses a filename as text.

**RULE: never put a filename or the suspected literal into a vision prompt.**
E.g. do NOT ask `vision_analyze(frame, "is the text 'candidate_1' here?")`.
Ask neutral: `vision_analyze(frame, "is there white text in this region?
answer yes/no only")`. Even then, treat the answer as suspect until pixels agree.

## 2. Pixel ground-truth recipes (ffmpeg-static)

```bash
FF=node_modules/ffmpeg-static/ffmpeg.exe

# (a) CENTER-crop brightness vs WHOLE-frame brightness.
#     A real centered text string spikes the center crop YAVG well above the
#     full-frame YAVG (white text ≈ Y235 vs gradient ≈ Y68).
#     ~equal => NO text spike => vision is hallucinating.
"$FF" -hide_banner -i frame.png \
  -vf "crop=iw/3:ih/3:iw/3:ih/3,signalstats,metadata=print:key=lavfi.signalstats.YAVG" \
  -f null -   # read: Parsed_metadata ... YAVG=<center>
"$FF" -hide_banner -i frame.png \
  -vf "signalstats,metadata=print:key=lavfi.signalstats.YAVG" -f null -   # full YAVG
# Observed: center=70.6  vs full=68.6  -> no text.

# (b) % of BRIGHT (text) pixels. Binarize luminance >180, then measure mean.
#     The printed YAVG on the binarized image == fraction of bright pixels.
#     A real 48px white caption is FAR above a few %.
"$FF" -hide_banner -i frame.png \
  -vf "format=gray,geq='if(gt(lum(X,Y),180),255,0)'" -frames:v 1 bw.png
"$FF" -hide_banner -i bw.png -vf "signalstats,metadata=print:key=lavfi.signalstats.YAVG" -f null -
# Observed: YAVG≈5.77% in the video center -> consistent with a faint label,
# NOT a large white caption. Confirmed false-alarm for "candidate_1".
```

## 3. Motion (reuse from SKILL.md): PSNR/MD5, not freezedetect

```bash
"$FF" -y -ss 1   -i video.mp4 -frames:v 1 a.png
"$FF" -y -ss 1.5 -i video.mp4 -frames:v 1 b.png
"$FF" -hide_banner -i a.png -i b.png -filter_complex psnr -f null -  # avg ~55dB => motion
# 2s-apart frames PSNR 27-28 dB => large zoom/pan over time.
```

## 4. Placeholder-acceptance (asset-content validation)

A solid-color gradient (e.g. AVS `generateFallbackVisual`, colors
`0x1e3a8a:0x0f172a`) can land in `assets/images/scene_NN/candidate_1.png` and
be shipped as a scene visual with a MISLEADING license label
("Source: openverse/pexels" in the render-manifest).

QA recipe — reject near-uniform images before they become scene visuals:
```bash
# spatial variance check: a real photo has detail; a gradient is flat.
"$FF" -hide_banner -i candidate.png -vf "signalstats" -f null - 2>&1 | grep -iE "YMIN|YMAX|YAVG"
#   flat gradient: YMIN≈YMAX (e.g. 41 vs 88 but TINY local variance across the frame)
#   real photo:    wide YMIN..YMAX spread + non-trivial local variance
```
Heuristic: compute `YAVG` of the whole frame vs `YAVG` of many small random
crops; if all crops are within a few units of each other => uniform => reject.
Add an `isRealPhoto(localPath)` guard to candidate selection in
`src/agentic/pipeline/acquire.ts` (and the `fetchVisual` return at
`src/agentic/orchestrator/pipeline.ts:324`) so placeholders fail over to the
next source, and label generated placeholders `placeholder` — NEVER
`openverse/pexels`.

## 5. Decision rule

```
vision says "text X here"  ──►  PIXELS first (recipe 2)
   center YAVG ≫ full YAVG, OR bright% ≫ few %  ──►  REAL text, go fix it
   center ≈ full, bright% tiny                ──►  HALLUCINATION, ignore
vision says "frozen"        ──►  PSNR/MD5 (recipe 3)
   PSNR high + MD5 differ                    ──►  smooth zoom, false alarm
   identical MD5 + PSNR ∞                     ──►  real still, fix it
```

This is the same "pixel > vision" discipline as the freezedetect/PSNR trap and
the chroma byte-size trap: miscalibrated perception (human-model or metric) is
never proof. Pixel math decides.
