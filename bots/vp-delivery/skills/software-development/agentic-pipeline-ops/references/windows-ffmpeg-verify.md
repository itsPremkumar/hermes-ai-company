# Windows / ffmpeg-static verification recipe (agentic-pipeline-ops)

Captured 2026-07-18 while building the discrete-ops layer for
Automated-Video-Generator (merge/trim/crop/resize/rotate/extract-audio/voiceover
+ a natural-language intent router).

## The one trap that burned iteration
`ffmpeg-static` ships a **native Windows .exe**. When invoked from a
git-bash / MSYS shell, POSIX temp paths (`/tmp/...`, the `os.tmpdir()`
result) are NOT understood by the binary -> silent failures:

- `color`/lavfi source: `Output file is empty, nothing was encoded`
- `Error opening input: No such file or directory`
- `extractAudio`: `Output file does not contain any stream`
- `trim -ss before -i -c copy`: empty output file (0 bytes)

### Fix (use Windows-valid paths)
```ts
// GOOD — Windows-valid, ffmpeg.exe can open it
const tmp = fs.mkdtempSync('C:/one/_ops-test-');      // forward-slash C:/ works
// also works: 'C:\\one\\_ops-test-'  or bare '/c/one/_ops-test-'
// BAD — ffmpeg.exe cannot open these on MSYS
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'x'));  // -> /tmp/...
const tmp = '/tmp/x';
```

Verify ffmpeg can actually write before blaming code:
```bash
FF=$(node -e "console.log(require('ffmpeg-static'))")
"$FF" -f lavfi -i "color=c=green:s=720x1280:d=2" -pix_fmt yuv420p -y "C:/one/_t/t.mp4"
ls -la "C:/one/_t/t.mp4"   # must exist & be >0 bytes
```

## Fixture must carry a real audio track
Synthetic `lavfi color` has no audio. For `extractAudio` / copy-`trim` tests,
mux a sine:
```ts
execFileSync(ffmpeg, [
  '-f','lavfi','-i',`color=c=${color}:s=720x1280:d=${durSec}`,
  '-f','lavfi','-i',`sine=frequency=440:duration=${durSec}`,
  '-pix_fmt','yuv420p','-c:v','libx264','-c:a','aac','-shortest','-y',p
], { stdio:'ignore' });
```

## Per-op assertions that PROVE it ran (not just compiled)
| op | real assertion |
|----|--------------|
| mergeVideos(a,b) | `ffprobe` duration ~= dur(a)+dur(b) (±1s) |
| trimVideo(in,1,3) | output duration ~= 2s (±1s) |
| cropVideo preset 9:16 | output file exists, non-empty |
| resizeVideo 360x640 | output file exists |
| rotateVideo 90 | output file exists |
| extractAudio | output ends `.mp3`, exists, non-empty |

Router tests are pure heuristic (no network): assert `routeTask(prompt).kind`
matches expected for merge / trim+times / crop-preset / resize / rotate /
extract_audio / voiceover / download_image / download_video / full_video.

## Verification sequence (run in this order)
```bash
npx tsc --noEmit            # 0 errors across whole project
npx tsx --test "src/agentic/operations/operations.test.ts"   # 16/16
npx tsx --test "src/agentic/agentic.test.ts" ...  # pre-existing: 0 regression
git add ... && git commit && git push origin main
```
Cleanup leftovers: `rm -rf /c/one/_ops-test-* /c/one/_t` (Windows-valid
paths, so MSYS `rm` handles them fine).
