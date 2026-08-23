# 30-Command FFmpeg Video Editor CLI Reference

## Overview

The `agentic-editor.ts` CLI provides 30 standalone video editing operations as thin
ffmpeg wrappers. Each command wraps `child_process.spawnSync(ffmpeg-static, args)`.

**Entry point:** `npm run agentic:editor <command> [options]`
**File:** `src/adapters/cli/agentic-editor.ts`

## Commands Reference

### Trim & Split
```bash
# Trim by timecode
npm run agentic:editor trim --input video.mp4 --start 00:05 --end 00:15
npm run agentic:editor trim --input video.mp4 --start 00:05 --duration 5

# Split at timestamp → two files
npm run agentic:editor split --input video.mp4 --at 00:15

# Merge multiple files
npm run agentic:editor merge --files "part1.mp4,part2.mp4" --output joined.mp4

# Auto-detect scene changes and split
npm run agentic:editor split-scenes --input video.mp4 --threshold 0.3
```

### Audio Operations
```bash
# Extract audio track
npm run agentic:editor extract-audio --input video.mp4 --output audio.mp3  # MP3
npm run agentic:editor extract-audio --input video.mp4 --output audio.wav  # WAV (PCM)

# Replace audio track
npm run agentic:editor replace-audio --input video.mp4 --audio new-audio.wav

# Remove audio
npm run agentic:editor mute --input video.mp4

# Audio effects
npm run agentic:editor noise --input video.mp4 --type reverb
npm run agentic:editor noise --input video.mp4 --type robot
npm run agentic:editor noise --input video.mp4 --type chipmunk
npm run agentic:editor noise --input video.mp4 --type echo
npm run agentic:editor noise --input video.mp4 --type white   # white noise
npm run agentic:editor noise --input video.mp4 --type slow   # slow-motion voice

# Audio filter (noise reduction, equalizer)
npm run agentic:editor audio-filter --input video.mp4 --noise 0.3 --volume 2.0
```

### Speed & Time
```bash
# Speed up/slow down
npm run agentic:editor speed --input clip.mp4 --rate 2.0    # 2x speed
npm run agentic:editor speed --input clip.mp4 --rate 0.5    # half speed

# Reverse playback
npm run agentic:editor reverse --input video.mp4

# Loop clip N times
npm run agentic:editor loop --input video.mp4 --count 3

# Freeze frame at timestamp
npm run agentic:editor freeze --input video.mp4 --at "00:05" --duration 3
```

### Transform (Size, Crop, Rotate)
```bash
# Resize to specific dimensions
npm run agentic:editor resize --input video.mp4 --w 1920 --h 1080

# Crop region (w:h:x:y)
npm run agentic:editor crop --input video.mp4 --w 720 --h 720 --x 200 --y 0

# Rotate
npm run agentic:editor rotate --input video.mp4 --angle 90
npm run agentic:editor rotate --input video.mp4 --angle 180
npm run agentic:editor rotate --input video.mp4 --angle hflip  # horizontal flip
npm run agentic:editor rotate --input video.mp4 --angle vflip  # vertical flip
```

### Visual FX
```bash
# Enhance (denoise + sharpen + deblock)
npm run agentic:editor enhance --input video.mp4
npm run agentic:editor enhance --input video.mp4 --denoise false --sharpen true

# Add fade in/out
npm run agentic:editor fade --input video.mp4 --fade-in 1.0 --fade-out 1.0
npm run agentic:editor fade --input video.mp4 --fi 0.5 --fo 0.5 --color white

# Brightness/Contrast/Saturation adjustment
npm run agentic:editor adjust --input video.mp4 --brightness 0.1 --contrast 1.2 --saturation 1.3

# Blur
npm run agentic:editor blur --input video.mp4 --strength 5

# Chroma key (green/blue screen)
npm run agentic:editor chroma-key --input greenscreen.mp4 --bg background.jpg
npm run agentic:editor chroma-key --input greenscreen.mp4 --color blue --similarity 0.2

# Stabilize video (two-pass: detect + transform)
npm run agentic:editor stabilize --input shaky.mp4
```

### Overlay
```bash
# Add text/caption to video
npm run agentic:editor overlay-text --input video.mp4 --text "Hello!" --color yellow --size 64
npm run agentic:editor overlay-text --input video.mp4 --text "Title" --x 100 --y 100

# Add image watermark
npm run agentic:editor overlay-image --input video.mp4 --image logo.png
npm run agentic:editor overlay-image --input video.mp4 --image logo.png --position top-left

# Picture-in-picture
npm run agentic:editor pip --input main.mp4 --overlay corner.mp4 --position bottom-right --size 0.3
```

### Export
```bash
# Animated GIF
npm run agentic:editor gif --input video.mp4 --fps 5 --width 240

# Thumbnail/poster frame
npm run agentic:editor thumbnail --input video.mp4 --at "00:02" --width 320

# Extract single frame as image
npm run agentic:editor extract-frame --input video.mp4 --at "00:10" --output frame.png
```

### Pipeline Integration
```bash
# Extract one scene from a rendered workspace video
npm run agentic:editor concat-scene --job avs_agentic_reel --scene 3

# Show video metadata (duration, codec, resolution, bitrate)
npm run agentic:editor info --input video.mp4
```

## JSON Output / Script-friendly Mode

Pass `--json` flag (not yet implemented — for future use) to get machine-readable output.

## Architecture Pattern

Each command follows the same pattern:

```typescript
const COMMANDS: Record<string, (args: Record<string, any>) => void> = {
    'command-name': (args) => {
        const input = resolveInput(args.input);
        const output = resolveOutput(args.output, `default_${path.basename(input)}`);
        const ff: string[] = ['-i', input, /* filter and codec args */, output, '-y'];
        runFfmpeg(ff, 'Description of operation');
    }
};
```

Key helpers:
- `ffmpegPath()` — resolves `ffmpeg-static` binary, falls back to PATH
- `ffprobePath()` — resolves `ffprobe-static` binary
- `getMediaInfo(file)` — returns JSON from ffprobe (duration, streams, format)
- `runFfmpeg(args, desc)` — spawnSync + output + error handling
- `resolveInput(input)` — checks file exists, exits with error if not
- `resolveOutput(output, fallback)` — uses provided path or generates one

## Verification

Test any command with a real video file. Commands produce real output files that
can be inspected with `info` or played back:

```bash
npm run agentic:editor info --input "output/my_video/My Video.mp4"
npm run agentic:editor trim --input "output/my_video/My Video.mp4" --start 00:05 --duration 5
npm run agentic:editor thumbnail --input "output/my_video/My Video.mp4" --at "00:02"
```
