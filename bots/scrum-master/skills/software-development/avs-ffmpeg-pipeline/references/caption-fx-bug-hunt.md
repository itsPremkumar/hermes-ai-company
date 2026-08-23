# Caption / Chroma / KenBurns / Wordpop bug-hunt (2026-07-28)

Harness: `node workspace/bug-hunt/harness.mjs <job.json> <name>` → renders via
modular CLI stages (plan → voice [lockfile-serialized kokoro] → visuals
--no-acquire → render), then emits a 4-frame vision grid at
`workspace/bug-hunt/grids/<name>.jpg`. Job files are JSON ARRAYS.

## Fixture assets (ffmpeg-generated, no network)
```bash
FF=node_modules/ffmpeg-static/ffmpeg.exe
# green-screen clip: red square moving over pure green
"$FF" -y -f lavfi -i "color=c=green:s=1280x720:d=6:r=25" \
  -f lavfi -i "color=c=red:s=200x200:d=6:r=25" \
  -filter_complex "[0][1]overlay=x='100+80*t':y=260" \
  -c:v libx264 -pix_fmt yuv420p assets/gs.mp4
# still image for Ken Burns
"$FF" -y -f lavfi -i "gradients=s=1280x720:d=1" -frames:v 1 assets/pic.png
```

## Job fixtures (workspace/bug-hunt/)
- `cap_job.json` — 2 scenes, `captions:"burned"` → verifies word-timed burn.
- `pop_job.json` — `captions:"none"`, `kineticText:true`, script contains
  emphasis words (`secret`, `always`, `best`, `real`, `truth`) so the
  style-engine emits a wordpop cue (style-engine.ts:130-134 picks the first
  match of its hardcoded emphasis list).
- `chroma_job.json` — `advanced: {"0": {"chromaKey": true}}` on gs.mp4.
- `kb_job.json` — kenBurns on a still + `advanced.keyframes` + emojiByScene
  (deliberately reproduces bugs 36–39).

## Standalone repro one-liners
```bash
# BUG 36: t undefined in zoompan (escaped OR unescaped both fail; time works)
"$FF" -f lavfi -i color=c=red:s=320x240:d=1 -filter_complex \
 "[0:v]zoompan=z='if(lte(t,3),1,1.35)':d=75:s=320x240[v]" -map "[v]" x.mp4
 # → [Eval] Undefined constant ... ; replace t→time → succeeds

# BUG 37: d=1 cumulative-zoom no-op — render 4s, diff frame@0.1 vs @3.8:
# max pixel diff 6/255, mean 0.045 → static.
```

## Bug → file:line map (as of 2026-07-28)
- 36 keyframe zoompan `t`+`\,`: render.ts:500-507 (mono), :738-742 (segmented)
- 37 kenBurns d=1 no-op: render.ts:488 (mono, also 8-backslash escape), :691 (seg)
- 38 dropped segment + false ✅: render.ts:789-795 retry/existsSync, :797-808 concat
  (observed: `⚠ segment 1 attempt 3 failed` then `✅ Rendered`, ffprobe 3.367 s
  for a 2-scene ~7 s job)
- 39 dead emoji options: cli-job.ts:203/315, orchestrator/types.ts:123/170
  declared; agentic-modular.ts + render.ts consume nothing.

## Verified working (vision-checked grids)
- bh_cap: captions burned both scenes, per-scene timing restart, bottom third.
- bh_pop: white lower-third box + centered yellow `SECRET` wordpop; drawtext
  `enable='between(t\,start,end)'` escaping correct (drawtext HAS `t`).
- bh_chroma: format=rgba,colorkey=0x00FF00:0.3:0.2 → overlay over black:
  no green anywhere, no fringe, captions burn on keyed scene.

Full report: `<repo>/workspace/bug-hunt/findings_captions.md`.
