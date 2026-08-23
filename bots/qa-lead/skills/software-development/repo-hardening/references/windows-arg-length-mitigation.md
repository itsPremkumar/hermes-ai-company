# Windows ENAMETOOLONG — Arg-Length Limit Mitigation

On Windows, `child_process.spawn()` rejects with `ENAMETOOLONG` when any
single argument exceeds the ~8 KB limit (or the total command line exceeds
~32 KB). This is a **real, repeatable failure** in ffmpeg-based rendering
pipelines that build compound filter strings.

## Root cause (in the Automated-Video-Generator)

The `filter_complex` argument for the single-pass ffmpeg invocation contains
one `drawtext` filter per **caption word** (word-level karaoke timing). With
7 scenes × ~15 words each × ~200 chars per drawtext filter, the string
exceeds 8 KB → `ENAMETOOLONG`.

Contributing factors:
- Long Windows temp paths (`C:\Users\LongName\AppData\Local\Temp\...`) as
  separate `-i` file arguments — each `-i` <path>` adds ~60 chars.
- The single monolithic `-filter_complex` approach (all scenes in one
  filtergraph) compounds the problem linearly with scene count.

## Fixes applied

### 1. Merge word-level captions → line-level (highest impact)

`mergeWordsToLines()` groups consecutive word-level caption segments into
lines of ≤7 words, preserving the timeline (start of first word, end of last
word). This reduces drawtext filter count from ~105 (15 words × 7 scenes) to
~14 (2 lines × 7 scenes) — well under the 8 KB limit even in single-pass mode.

```ts
export function mergeWordsToLines(
    segs: { text: string; startMs: number; endMs: number }[],
    maxWords = 7,
): { text: string; startMs: number; endMs: number }[] {
    // If chunkCues already produced line-level, return as-is
    if (segs.length <= maxWords) return segs;
    const lines: typeof segs = [];
    let cur: typeof segs[0] | null = null;
    for (const s of segs) {
        const wc = cur ? cur.text.split(' ').length : 0;
        const sc = s.text.split(' ').length;
        if (!cur || (wc + sc > maxWords) || /[.!?]$/.test(cur.text)) {
            if (cur) lines.push(cur);
            cur = { text: s.text, startMs: s.startMs, endMs: s.endMs };
        } else {
            cur.text += ' ' + s.text;
            cur.endMs = s.endMs;
        }
    }
    if (cur) lines.push(cur);
    return lines;
}
```

### 2. Default to segmented rendering

Instead of one giant ffmpeg call, render each scene as an independent segment
(small filter per call), then concatenate the segments:

```
Segment ffmpeg calls:
  scene_0 → _seg_0.mp4  (small -filter_complex, well under 8 KB)
  scene_1 → _seg_1.mp4
  ...
  concat demuxer → final.mp4
```

Benefits beyond arg-length:
- Per-segment retry isolation (one failed scene doesn't lose the whole render)
- Smaller intermediate files → less RAM pressure
- Easier to debug a single scene's rendering

### 3. `filter_complex_script` (not available on this build)

Some ffmpeg builds support `-filter_complex_script <file>` which reads the
filtergraph from a file instead of the command line, bypassing the arg-length
limit entirely. However, many `ffmpeg-static` Windows builds **do not include
this option**. Verify with:

```
ffmpeg -h 2>&1 | grep filter_complex_script
```

If absent, fall back to option 1 or 2 above.

## Verification

After applying the fix:
1. Run a 7+ scene render with captions enabled.
2. Check exit code (should be 0, not ENAMETOOLONG).
3. Verify the MP4 is valid: `ffprobe -v error -show_entries format=duration:stream=codec_type -of default=noprint_wrappers=1 output.mp4`
4. Confirm captions appear at correct timestamps.

## Related

- `repo-hardening/SKILL.md` §8 "Windows ENAMETOOLONG — arg-length limit mitigation"
- `src/agentic/orchestrate.ts` `mergeWordsToLines()` implementation
- `src/agentic/orchestrate.pure.test.ts` unit tests for `mergeWordsToLines`
