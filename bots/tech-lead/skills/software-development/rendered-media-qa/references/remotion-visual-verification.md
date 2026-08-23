# Remotion visual verification recipe (real Chrome)

For pipelines that render via Remotion comps (`.tsx` under `remotion/`), verify
the comps visually — `remotion still`/`renderMedia` need a real browser.

## 1. Find + export Chrome
Windows box: `C:/Program Files/Google/Chrome/Application/chrome.exe`.
```bash
export CHROME_EXECUTABLE="/c/Program Files/Google/Chrome/Application/chrome.exe"
```
Without this, `npx remotion render` falls back to a black frame / headless
failure. (Discovered: the box DOES have Chrome; the earlier "no Chromium →
ffmpeg fallback only" assumption was WRONG.)

## 2. Render a short VIDEO (not a still) for scene checks
```bash
npx remotion render AgenticVideo out.mp4 --props=props.json --frames=0-149
```
Why video over `renderStill`: `remotion still` re-copies the project `public/`
dir and an ad-hoc `staticFile('x.png')` placeholder is often NOT served →
black frame, or a missing image crashes the whole render with a React stack.
The `renderMedia` path serves `public/` correctly.

## 3. Extract settled frames + vision-check
```bash
ffmpeg -ss 0.5 -i out.mp4 -frames:v 1 -y f_intro.png
ffmpeg -ss 2.0 -i out.mp4 -frames:v 1 -y f_scene.png
ffmpeg -ss 4.2 -i out.mp4 -frames:v 1 -y f_outro.png
# zoom-crop a caption region to judge a glow precisely:
ffmpeg -i f_scene.png -vf "crop=1080:520:0:1300,scale=1080:520" -y f_capcrop.png
```

## 4. Timing traps (looks-broken ≠ is-broken)
- Spring/text animations settle over ~15–40 frames. Intro title at frame 15 =
  only first chars. Render settled frames (intro ~frame 40, outro ~frame 180
  for 30fps/60-frame intro) before declaring a layout bug.
- Mid-animation "fragmented title" / "S u" partial text are NORMAL.

## 5. Known Remotion bugs to watch for + fixes applied here
- **Ghost/duplicate caption**: both `SubtitleOverlay` and `KaraokeCaptions`
  rendered the same text → faint duplicate. Made them mutually exclusive
  (`captionSegments?.length > 0 ? Karaoke : SubtitleOverlay`).
- **Kinetic title colliding with card's own title**: doubled text. Added a
  `hideTitle` flag to the intro/outro card; parent passes `hideTitle={kineticTitle}`.
- **KineticText fragmentation across full frame**: characters stretched
  edge-to-edge. Constrained to a centered `maxWidth:'90%'` row (`flexWrap:wrap`,
  `justifyContent:'center'`) instead of an `AbsoluteFill` flex row.
- **Neon caption glow washed out**: brand accent diluted it. Used a FIXED
  electric-cyan halo `#00eaff` so the neon identity is unmistakable.
- **Static `Circle` ring overlapping kinetic title**: gated the card ring on
  `!hideTitle`.

## 6. tsconfig / eslint blind spots (real, silent)
- `tsconfig` `include` MUST contain `remotion/**/*.tsx`. With only `*.ts`, every
  `.tsx` is UNchecked and `typecheck` lies (reports 0). Fix: add the `.tsx` glob.
- `eslint src/` only lints `src/`; extend to `src/ remotion/` and ignore the
  `_study/` reference-clone dir (mirror tsconfig `exclude`). Wire `eslint` into
  CI so the (many) latent errors can't ship silently.
