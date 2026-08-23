# ffmpeg Overlay Composition (Logo Watermark + Screenshot PIP)

After a pipeline-generated video is complete, add overlays (logo watermark, screenshot PIP, text titles) via ffmpeg post-processing — avoids re-rendering the entire pipeline.

## Two-pass overlay technique

### Pass 1: Logo watermark (bottom-right, throughout)

```bash
# Python subprocess wrapper (no system ffmpeg on Windows)
import subprocess, os
ff = os.path.expanduser(
    r'~/AppData/Local/hermes/hermes-agent/venv/Lib/site-packages/'
    r'imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
)
subprocess.run([
    ff, '-i', 'base.mp4', '-i', 'logo.png',
    '-filter_complex',
    '[0:v][1:v]overlay=W-w*0.12-20:H-h*0.12-20:format=auto[wm]',
    '-map', '[wm]', '-map', '0:a',
    '-c:v', 'libx264', '-preset', 'fast', '-crf', '20',
    '-c:a', 'copy',  # no audio re-encode
    '-y', 'pass1-wm.mp4'
])
```

- `W-w*0.12-20` = logo at 12% of video width, 20px from right edge
- `H-h*0.12-20` = same from bottom edge
- Use `preset fast crf 20` for quick first pass; final can use `preset slow crf 18`

### Pass 2: Time-windowed screenshot PIP

The bundled ffmpeg v7.1 does NOT support `enable=between(t,...)` on overlay filters. Use `split` + `trim` + `concat` instead:

```bash
ffmpeg -i pass1-wm.mp4 -i screenshot.png \
  -filter_complex \
    '[0:v]split=3[pre][mid][post];
     [pre]trim=0:6,setpts=PTS-STARTPTS[pre_v];
     [mid]trim=6:14.5,setpts=PTS-STARTPTS[mid_t];
     [post]trim=14.5:end,setpts=PTS-STARTPTS[post_v];
     [1:v]scale=iw*0.42:ih*0.42[screenshot];
     [mid_t][screenshot]overlay=20:H-h-20:format=auto[mid_v];
     [pre_v][mid_v][post_v]concat=n=3:v=1:a=0[final_v]' \
  -map '[final_v]' -map '0:a' \
  -c:v libx264 -preset slow -crf 18 \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  -y final.mp4
```

Key details:
- `split=3` creates 3 video copies: pre-window, during-window, post-window
- `trim=6:14.5` keeps frames between 6.0s and 14.5s
- `setpts=PTS-STARTPTS` resets timestamps so each segment starts at 0
- `overlay=20:H-h-20` = 20px from left, 20px from bottom
- `concat=n=3:v=1:a=0` merges the 3 video segments (no audio concat — audio comes from `-map 0:a`)

### Pass 3 (optional): Text overlay

Use `drawtext` (which DOES support `enable`):

```bash
-vf "drawtext=text='TITLE':fontfile=C\\:/Windows/Fonts/arial.ttf:\
      fontsize=36:fontcolor=white:x=(w-text_w)/2:y=50:\
      enable='between(t,0,4)'"
```

- Text centered top (`x=(w-text_w)/2`, `y=50`)
- Font path must use MSYS escapes (double backslash after drive letter)

## Verifying overlay placement

Extract keyframes and compare file sizes:

```bash
ffmpeg -i final.mp4 -ss 8 -vframes 1 -q:v 3 -y frame_8s.jpg
```

**Heuristic:** frames with a large solid-background overlay (white GitHub page, logo) compress much smaller (~0.4MB vs ~1.2MB for natural footage). This confirms overlay timing without needing vision.

## Bundled ffmpeg path (Windows)

The `imageio_ffmpeg` package ships a static ffmpeg binary. On this system:
- Path: `~/AppData/Local/hermes/hermes-agent/venv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe`
- No ffprobe bundled (use ffmpeg's built-in stream info instead)
- Use Windows-style paths with forward slashes for Python subprocess
