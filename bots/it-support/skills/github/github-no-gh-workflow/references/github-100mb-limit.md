# GitHub 100 MB history limit + media compression

GitHub refuses any file **>100 MB at any point in git history**, not just in the current tree.
A large demo video / model / dataset committed locally will fail on `git push` (pre-receive
hook) or be silently rejected. You won't get a clear error from the MSYS curl path, so catch it
in the pre-push safety gate instead (see `pre-push-safety.md`, large-file guard).

## Symptom observed
- 250 MB `Assets/video.mp4` was tracked in a fresh local repo (2 commits, no remote).
- GitHub's hard limit is 100 MB per file in history -> the repo could never be pushed.

## Fix (do BEFORE committing the oversized file)
1. Compress the media so the largest blob is well under 100 MB (target <10 MB for headroom).
   No system `ffmpeg` is needed - use the bundled `imageio-ffmpeg` which downloads a working
   Windows ffmpeg binary on demand:
   ```python
   import imageio_ffmpeg, subprocess, os
   ff = imageio_ffmpeg.get_ffmpeg_exe()
   subprocess.run([ff, "-y", "-i", "Assets/video.mp4",
                   "-vf", "scale=1280:-2",
                   "-c:v", "libx264", "-crf", "30", "-preset", "medium",
                   "-c:a", "aac", "-b:a", "96k",
                   "Assets/demo.mp4"])
   ```
   Result: 250 MB -> ~2.9 MB (CRF 30, 1280-wide, 96 kbps audio). Quality is fine for a walkthrough.
2. Stop tracking the raw file and gitignore it:
   ```bash
   git rm --cached Assets/video.mp4        # if already staged/committed
   echo "Assets/video.mp4" >> .gitignore    # keep raw out of the repo
   ```
3. Commit only the compressed `demo.mp4`. If the oversized blob is already in history (even a
   local-only commit), re-init the repo to drop it:
   ```bash
   rm -rf .git && git init && git add -A && git commit -m "Initial commit"
   ```
   Safe only when there is **no remote** and no other branch to preserve (verify first).
4. Verify no >100 MB file remains in the staged tree before pushing:
   ```bash
   git ls-files | while read f; do [ -f "$f" ] && du -m "$f"; done | awk '$1>100{print "TOO BIG:",$0}'
   ```

## Apply the same pattern to
- ML model weights (`*.bin`, `*.gguf`, `*.safetensors`) - gitignore, or use Git LFS if the repo
  genuinely needs them in-repo.
- Large datasets, exported JSON, generated ffmpeg artifacts (see pre-push-safety.md Remotion note).
