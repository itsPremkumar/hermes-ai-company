# Remotion visual verification — real Chrome render recipe

The single biggest mistake is concluding "no Chromium, can't visually verify."
Chrome is frequently already installed. Probe, then render a real video.

## 1. Find Chrome
```bash
for b in google-chrome google-chrome-stable chromium chromium-browser chrome; do which $b 2>/dev/null; done
ls "/c/Program Files/Google/Chrome/Application/chrome.exe" 2>/dev/null
ls "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe" 2>/dev/null
# also Brave/Edge chromium builds under LOCALAPPDATA can work
```

## 2. Render a VIDEO, not a still
```bash
export CHROME_EXECUTABLE="/c/Program Files/Google/Chrome/Application/chrome.exe"
npx remotion render <CompId> out.mp4 --props=props.json --frames=0-149
```
- Props with nested assets go in a JSON file passed via `--props=`.
- Keep intro/outro `durationSec` small (1s) so a short frame range covers
  intro + a scene + outro.

### Why NOT `remotion still`
`renderStill` recopies the entire `public/` dir at render start. An ad-hoc
`staticFile('foo.png')` you just dropped in `public/` often is NOT served in
that pass:
- **missing image → hard crash** (exit 1, React stack).
- **present-but-unserved → silent BLACK frame** (no error).
Intro/outro cards (which use no `staticFile`) render fine either way, which
misleads you into thinking scenes are broken. `renderMedia` (the production
`npx remotion render`) serves assets correctly — use it.

## 3. Extract + inspect frames
```bash
node -e "const ff=require('ffmpeg-static');const{execFileSync}=require('child_process');
execFileSync(ff,['-ss','2.0','-i','out.mp4','-frames:v','1','-y','frame.png'],{stdio:'ignore'});"
```
Then vision-analyze `frame.png`.

### Pick SETTLED frames
Spring/kinetic entrances animate in over ~1s. A kinetic title at frame 15 will
look "fragmented" / "only first letters" / "doubled" — that's mid-animation,
NOT a bug. Sample a frame well after the entrance completes (frame 40+ at 30fps)
before judging. To confirm subtle effects (e.g. neon glow), crop-zoom the region:
```bash
# crop bottom third (caption area) of a 1080x1920 frame and scale up
-vf crop=1080:520:0:1300,scale=1080:520
```

## Bugs this recipe surfaced (all real, all fixed)
- Ghost/doubled caption: `SubtitleOverlay` + `KaraokeCaptions` both rendering.
  Fix = mutually exclusive (`segments?.length ? <Karaoke/> : <Overlay/>`).
- Kinetic title spread edge-to-edge: outer `AbsoluteFill` was the flex row.
  Fix = outer centers, inner width-bounded wrapping row holds the characters.
- Kinetic overlay title doubled the card's own title. Fix = `hideTitle` prop on
  the card + hide its centered decorative ring when hidden.
- Neon caption looked plain white (diluted by brand accent). Fix = fixed cyan
  halo `text-shadow: 0 0 6px #fff, 0 0 14px #00eaff, 0 0 26px #00eaff, ...`.

## Cleanup
Delete all `_verify_*` / `_vout*.mp4` / placeholder PNGs before committing.
gitignore study clones (`remotion/_study/`). Never push until user approves.
