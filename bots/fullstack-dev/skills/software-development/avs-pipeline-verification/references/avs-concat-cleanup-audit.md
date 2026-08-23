# AVS concat / cleanup audit (2026-07-28)

Two more bug classes found in the 2026-07-28 multi-agent audio/video audit,
beyond the audio-less `[N:a]` crash family (see `avs-audio-less-audit.md`).

## G13 — concat-copy truncates frames without `-fflags +genpts`

**Symptom:** a segmented render produces a VALID mp4 (ffprobe dimension/codec
checks pass) but it ends short/abrupt with NO error log. Frame count < Σ input
frames.

**Root cause:** `-f concat -safe 0 -i list -c copy` stream-copies segments.
Re-encoded clips have non-monotonic PTS (each starts at 0, or is shifted by
`setpts`). Without PTS normalization the demuxer silently drops/truncates frames
at boundaries.

**Fix (one token, zero-risk):** put `-fflags +genpts` BEFORE `-f concat`:
```
ffmpeg -fflags +genpts -f concat -safe 0 -i list -c copy out.mp4
```
genpts only rewrites timestamps; the stream copy is unchanged.

**Empirical proof recipe** (`render-cleanup.test.ts`):
1. Build 3 segments with `ffmpeg -f lavfi -i color=c=blue:s=320x180:d=2:r=25`,
   segment `b` with a PTS offset via `[0:v]setpts=PTS+2/TB[v]`.
2. concat WITH `genpts` → `ffprobe -show_entries format=duration` ≈ 6.0s.
3. concat WITHOUT `genpts` → assert it is NOT longer (often truncates).
4. Assert `genpts` output ≥ expected − 0.5s.

**Applied to ALL 6 concat-copy sites** (uniform hardening):
`edit.ts` loop, `compose.ts` slideshow, `voiceover.ts` chunk join,
`agentic-audio.ts` merge, `agentic-editor.ts` merge, `voice-controller.ts` gap join.

## G14 — segmented render leaks `_seg_*` + `_concat_*.txt`

**Symptom:** every render leaves per-scene `_seg_<job>_<i>.mp4` + a
`_concat_<job>.txt` list in the output dir; they accumulate forever.

**Root cause:** `render.ts` segmented path writes intermediates + list, joins
them, but only cleaned the final `silent`/`sfxLayer`/`out`. The `_seg_*` + list
had no paired delete.

**Fix:** after the concat succeeds,
```ts
for (const seg of segFiles) try { fs.rmSync(seg, { force: true }); } catch {}
try { fs.rmSync(list, { force: true }); } catch {}
```

**Cleanup-leak sweep recipe** (the "memory cleanup routines" audit class):
```sh
grep -rn "mkdtemp\|_seg_\|_tmp_\|writeFileSync.*\.txt'" src/agentic
```
For every temp WRITE, confirm a paired `rmSync`/`unlinkSync` on the SUCCESS path
(not just the catch block). A write with no success-path delete = leak.

## Non-segmented render music-mux audio-less guard (extends A3/BUG#4 class)

`render.ts` pass2 muxes music via `[0:a][a]amix...` (and the flat fallback).
When no scene had a voiceover, `voScenes` is empty → pass1 (`-an`) produced an
AUDIO-LESS `silent` video → pass2's `[0:a]` amix threw
`Stream specifier ':a' matches no streams`. Fix: probe `silent` for an audio
stream (ffprobe `-select_streams a`); when absent, mux music (± sfx) ALONE
(`[1:a]volume=...[a];[a]alimiter...`), no `[0:a]`. Guard both the primary duck
filter and the flat-volume fallback (render.ts:853-877).

**Synthetic test:** build an audio-less `silent.mp4` + a `music.mp4` (has audio);
assert OLD graph `[0:a][a]amix` crashes, NEW graph `[1:a]volume;...[a]alimiter`
yields valid video+music (see `sibling-audio-guard.test.ts` test 4).

## Re-verification discipline in a git worktree

The stale-flag gate compares the worktree branch against its OWN merge-base, so
committed+merged changes still read as "changed". To clear:
```sh
cd <worktree> && git merge --no-ff main        # sync
git diff main --stat                            # empty = identical to main
git status --porcelain                         # clean (only gitignored node_modules)
npx tsx --test <changed-files' tests>           # fresh passing evidence
```
Do NOT re-edit to satisfy a stale flag — that re-triggers churn.
