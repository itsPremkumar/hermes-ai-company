# Single-Image Toolbox (`agentic:image`) — reference

Companion to G12 in the dev SKILL.md. This documents the standalone
image-editing CLI built because the video editor (`agentic-editor.ts`)
only accepts VIDEO inputs — there was no image-format conversion, no
image→video, and no text/emoji burn on a *standalone image* originally.

## Command table (18 commands)

Run: `npm run agentic:image <cmd> -- --input <img> [options]`
(or `npx tsx src/adapters/cli/agentic-image.ts <cmd> --input <img>`)

| Command | What it does | Key options |
| :------ | :---------- | :---------- |
| `convert` | Image format conversion (png→jpg/webp/tiff/bmp/gif) | `--output out.webp --quality 90` |
| `resize` | Scale to w×h (aspect-kept, padded) | `--w 1080 --h 1080` |
| `crop` | Crop region | `--w 1080 --h 1920 --x 100 --y 200` |
| `rotate` | 90/180/270/`hflip`/`vflip`/free° | `--angle 90` |
| `flip` | hflip / vflip convenience | `--dir h` |
| `adjust` | brightness/contrast/saturation/gamma | `--brightness 0.05 --contrast 1.2 --saturation 1.3` |
| `blur` | Whole or region `w:h:x:y` | `--strength 8 --region 200:200:100:100` |
| `text` | Burn text onto the image (sharp+SVG) | `--text "Free for students" --color white --size 90` |
| `emoji` | Burn an emoji/sticker (sharp+SVG, Segoe UI Emoji) | `--emoji "🔥" --size 260` |
| `watermark` | Overlay a logo image (corner + opacity) | `--image logo.png --position bottom-right --scale 0.15 --opacity 0.8` |
| `tint` | Brand color tint overlay | `--color #7C3AED --alpha 0.2` |
| `vignette` | Edge darkening | `--amount PI/5` |
| `border` | Colored border/padding | `--size 40 --color white` |
| `enhance` | Denoise + sharpen + deblock | `--denoise --sharpen` |
| `info` | Show image metadata (dims/format/size) | — |
| `to-video` | Image → video (Ken Burns zoom + optional text + music) | `--duration 5 --w 1080 --h 1920 --kenburns --text "..." [--music track.mp3]` |
| `gif` | Image → animated GIF (Ken Burns loop) | `--duration 3 --fps 15` |
| `contact-sheet` | Stack N images into one sheet (sharp) | `--files "a.png,b.png,c.png" --w 480 --gap 12` |

## Hard-won repo traps (the reason this CLI exists separately)

1. **`vstack`/`hstack` is BROKEN in the bundled gyan.dev ffmpeg 6.1.1.** Any
   `filter_complex` with vstack fails `Filter vstack:default has an unconnected
   output` even with same-width, `setsar=1` inputs. Do NOT use it for image
   stacks — use **`sharp`** (v8.17.3, a devDependency) to scale + composite.
   `contact-sheet` uses sharp for this reason.
2. **ffmpeg `drawtext` cannot render emoji on this Windows build.** It yields a
   blank/broken glyph. `text` and `emoji` commands therefore use **sharp + an
   SVG `<text font-family='Segoe UI Emoji'>`** — verified to render onto a
   real PNG. More reliable than the video-pipeline emoji path (G1).
3. **`zoompan` has no `enable=` timeline option** on this ffmpeg build — it
   errors "Not yet implemented in FFmpeg". Apply the Ken Burns zoom across the
   whole clip instead of gating it with `enable='between(t,...)'`.
4. **Format conversion**: ffmpeg handles png/jpg/webp/tiff/bmp/gif, but `sharp`
   gives cleaner webp/tiff — preferred for those two.

## Verification discipline (empirical, like the video gate)

- Run each command on a real PNG (`input/visuals/sproutern-*.png`).
- Then `vision_analyze` the OUTPUT to confirm the effect actually shows
  (text legible + bottom-positioned; emoji visible; watermark in corner).
- `to-video` / webm / long clips can exceed 60s — run those in background
  (`terminal(background=true, notify_on_complete=true)`), then probe the
  resulting mp4 with ffprobe / extract a frame (`-i file -ss N`, INPUT seek
  per G8) and vision-check it.

## Audio-only generation (Kokoro) — separate path, verified

- `npm run agentic:modular -- plan --file <array.json>` then
  `npm run agentic:modular -- voice --file <array.json>` writes
  `workspace/jobs/<id>/audio/scene_1_voice.wav` (24kHz PCM, verified real
  file). The `<array.json>` must be a JSON **array** of jobs (single-object
  file fails with "jobs is not iterable"), and `voice` requires a prior
  `plan` stage (it reads the saved plan).
- The `clone-voice` mode only saves a profile JSON — it does NOT output an
  audio file. True voice CLONING needs Chatterbox (`src/speech/backends/
  chatterbox_backend.py`), which is present in code but **UNVERIFIED** in this
  environment (may require a model download, conflicting with the zero-cost/
  no-PIP rule). Do not promise "clone voice → WAV" until Chatterbox is
  confirmed loadable in the venv.
