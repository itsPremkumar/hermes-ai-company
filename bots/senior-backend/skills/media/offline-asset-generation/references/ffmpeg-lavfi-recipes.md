# ffmpeg lavfi recipes — proven offline (ffmpeg 6.1.1 gyan.dev essentials, Node 22)

All commands below were executed and confirmed to produce non-empty files:
- image: 14,227 bytes `.jpg`
- video: 17,008 bytes `.mp4`

`ffmpegPath` = `require('ffmpeg-static')` (CJS) or
`createRequire(import.meta.url)('ffmpeg-static')` (ESM-only).

---

## Image: branded vertical gradient placeholder (720x1280 → .jpg)

```js
execFileSync(ffmpegPath, [
  '-y',
  '-f', 'lavfi',
  '-i', 'gradients=s=720x1280:c0=0x1e3a8a:c1=0x0f172a:x0=0:y0=0:x1=0:y1=720:nb_colors=2',
  '-frames:v', '1',
  out, // ending in .jpg
], { stdio: 'pipe' });
```

Notes:
- `c0`/`c1` are hex colors WITHOUT the `0x`-prefix inside lavfi? NO — in this
  build `c0=0x1e3a8a` (with `0x`) works. Use `0xRRGGBB`.
- `x0,y0,x1,y1` define the gradient axis; `x1=0,y1=720` = top→bottom.
- `-frames:v 1` = single still frame.

---

## Video: Ken Burns zoompan over silent audio (720x1280 → .mp4, 4s)

```js
execFileSync(ffmpegPath, [
  '-y',
  '-f', 'lavfi',
  '-i', 'gradients=s=720x1280:c0=0x1e3a8a:c1=0x0f172a:x0=0:y0=0:x1=0:y1=720:nb_colors=2',
  '-f', 'lavfi',
  '-i', 'anullsrc=r=44100:cl=stereo',
  '-filter_complex', '[0:v]scale=1440:2560,zoompan=z=1.15:d=100:s=720x1280:fps=25,format=yuv420p[v]',
  '-map', '[v]',
  '-map', '1:a',
  '-c:v', 'libx264',
  '-c:a', 'aac',
  '-t', '4',
  '-shortest',
  out, // ending in .mp4
], { stdio: 'pipe' });
```

Notes:
- `scale=1440:2560` overscans 2x so the `zoompan` (1.15x) never reveals black
  borders. Output is forced back to `s=720x1280`.
- `zoompan=z=1.15:d=100` → 100-frame (4s @ 25fps) slow zoom. Increase `z` for a
  stronger push-in.
- `anullsrc=r=44100:cl=stereo` → silent stereo audio so the mp4 has an audio
  stream. Omit `-map 1:a`/audio inputs if you want video-only.
- `format=yuv420p` required for broad player compatibility.
- `-t 4 -shortest` caps duration; with `anullsrc` (infinite) `-shortest` ends it
  at the video length.

---

## Solid color variant (flat fill)

Replace the `gradients=...` input with:
`color=c=0x1e3a8a:s=720x1280:d=4`  (video, `d` = duration seconds)
and for a still image add `-frames:v 1`.

---

## Things that DO NOT work here (and why)

- `ffmpeg -i foo.svg out.jpg` → "no decoder found for: svg" (essentials build
  lacks librsvg). Use `gradients`/`color` lavfi instead.
- sharp `.toBuffer()` inside a sync function → it's async; `await` is illegal in
  a non-async fn and `deasync` isn't installed. Stay on the ffmpeg path.
- Hardcoding the ffmpeg path → it lives in node_modules; resolve via the package.
