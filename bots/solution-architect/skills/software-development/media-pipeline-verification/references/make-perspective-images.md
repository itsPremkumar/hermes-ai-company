# Generating distinct LABELED test images for visual verification

To visually verify a render (orientation, correct per-scene image, watermark, captions),
you need frames that are INSPECTABLE — i.e. each scene's source asset must be visually
distinct and ideally labeled. The AVS repo only ships `github-profile.png` and
`logo-automation.png` (and `logo-automation.png` has an opaque black background — see the
watermark bug). Generate a set of labeled gradient images with `sharp` (already installed).

## Generator (run with `npx tsx`)

```ts
import sharpDefault from 'sharp';
const sharp = sharpDefault as unknown as (b: Buffer) => any; // CJS default-export interop
import * as fs from 'fs';

const VIS = [
  { name: 'persp_aerial.png',    bg: ['#1a2a6c', '#b21f1f', '#fdbb2f'], label: 'AERIAL VIEW' },
  { name: 'persp_closeup.png',   bg: ['#0f2027', '#203a43', '#2c5364'], label: 'CLOSE-UP' },
  { name: 'persp_wide.png',      bg: ['#414345', '#232526', '#414345'], label: 'WIDE SHOT' },
  { name: 'persp_angle.png',     bg: ['#8E2DE2', '#4A00E0', '#8E2DE2'], label: 'LOW ANGLE' },
  { name: 'persp_top.png',       bg: ['#11998e', '#38ef7d', '#11998e'], label: 'TOP DOWN' },
  { name: 'persp_night.png',     bg: ['#0b0b2b', '#1a1a40', '#24243e'], label: 'NIGHT' },
  { name: 'persp_warm.png',      bg: ['#f12711', '#f5af19', '#f12711'], label: 'WARM TONE' },
  { name: 'persp_cool.png',      bg: ['#2980b9', '#6dd5fa', '#ffffff'], label: 'COOL TONE' },
  { name: 'persp_urban.png',     bg: ['#232526', '#414345', '#485563'], label: 'URBAN' },
  { name: 'persp_nature.png',    bg: ['#134e5e', '#71b280', '#134e5e'], label: 'NATURE' },
];

const W = 1280, H = 720;
const svg = (bg: string[], label: string) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}">
    <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="${bg[0]}"/><stop offset="50%" stop-color="${bg[1]}"/><stop offset="100%" stop-color="${bg[2]}"/>
    </linearGradient></defs>
    <rect width="100%" height="100%" fill="url(#g)"/>
    <rect x="40" y="${H-200}" width="${W-80}" height="120" fill="#000000" opacity="0.45" rx="12"/>
    <text x="60" y="${H-120}" font-family="Arial" font-size="84" font-weight="bold" fill="#ffffff">${label}</text>
  </svg>`;

fs.mkdirSync('input/visuals', { recursive: true });
for (const v of VIS) {
  await sharp(Buffer.from(svg(v.bg, v.label))).png().toFile(`input/visuals/${v.name}`);
}
```

Notes:
- `import sharp from 'sharp'` fails with `sharp is not a function` (CJS interop); use the
  `as unknown as (b: Buffer) => any` cast shown above.
- Reference them in a job via `"localAssets": ["persp_aerial.png", ...]` and
  `[Visual: persp_aerial.png]` in the script — no network fetch.
- Each label lets you confirm in a vision pass that the CORRECT perspective image is shown
  for each scene (catches asset-binding regressions that ffprobe cannot).

## Frame extraction + vision loop

```bash
ffmpeg -y -ss 1.0 -i output/<id>/<Title>.mp4 -frames:v 1 -vf scale=480:-1 workspace/tmp/frames/a.png
ffmpeg -y -ss 3.0 -i output/<id>/<Title>.mp4 -frames:v 1 -vf scale=480:-1 workspace/tmp/frames/b.png
```
Then `vision_analyze` each with orientation / watermark / caption questions (see the
VISUAL VERIFICATION section in avs-agentic-verification.md).
