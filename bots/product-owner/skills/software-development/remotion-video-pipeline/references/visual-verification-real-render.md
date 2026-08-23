# Real visual verification of Remotion compositions (Chrome + renderMedia)

This is the loop that actually catches rendering bugs static checks (typecheck +
pure-helper unit tests) cannot. Proven on the Automated-Video-Generator repo.

## 0. Chrome is present — verify, don't assume absent
```bash
ls "/c/Program Files/Google/Chrome/Application/chrome.exe"   # usually exists
export CHROME_EXECUTABLE="/c/Program Files/Google/Chrome/Application/chrome.exe"
```
The project chrome-gate checks `process.env.CHROME_EXECUTABLE`. With it set,
Remotion renders for real. NEVER report "visual verification blocked, needs
Chrome" without running this check first.

## 1. renderMedia (production path) — NOT renderStill for scenes
`renderStill` recopies the entire `public/` dir at render start; an ad-hoc
placeholder you just wrote to `public/` is not reliably served → missing asset
CRASHES the render (exit 1, React stack), present-but-unserved asset renders a
BLACK frame with NO error. Intro/outro (no `staticFile`) render fine and MASK the
problem. Use a real short video instead:

```bash
# generate a placeholder asset under public/ (served via staticFile('name.png'))
node -e "const ff=require('ffmpeg-static');const{execFileSync}=require('child_process');execFileSync(ff,['-f','lavfi','-i','color=c=0x2277cc:s=800x800','-frames:v','1','public/_vph.png'],{stdio:'ignore'})"

# props JSON: assets[].localPath is relative to public/ (e.g. '_vph.png')
export CHROME_EXECUTABLE="/c/Program Files/Google/Chrome/Application/chrome.exe"
npx remotion render AgenticVideo out.mp4 --props=props.json --frames=0-149

# extract frames at chosen timestamps
node -e "const ff=require('ffmpeg-static');const{execFileSync}=require('child_process');execFileSync(ff,['-ss','2.0','-i','out.mp4','-frames:v','1','-y','f_scene.png'],{stdio:'ignore'})"
```
Then `vision_analyze` each frame.

## 2. Crop+upscale before judging subtle effects
A full 1080x1920 frame downscaled for the vision model hides soft glows / small
text — the model will say "plain white text, no glow". Crop the region first:
```bash
node -e "const ff=require('ffmpeg-static');const{execFileSync}=require('child_process');execFileSync(ff,['-i','f_scene.png','-vf','crop=1080:520:0:1300,scale=1080:520','-y','f_crop.png'],{stdio:'ignore'})"
```

## 3. Render SETTLED frames, not mid-animation
Kinetic/spring text is mid-flight in early frames. "Fragmented / missing letters"
at frame 15 is just the stagger still running — render a frame well past the
animation window (e.g. intro title fully in by ~frame 40) before calling it a bug.

## Real bugs this loop caught (would have shipped otherwise)
1. **Ghost/doubled caption.** Scene rendered BOTH `SubtitleOverlay` AND
   `KaraokeCaptions` when `captionSegments` existed → faint duplicate under the
   main caption. Fix: make them mutually exclusive (ternary): karaoke/styled when
   word-timed segments exist, static overlay otherwise. Rendering both any time
   the same text is stamped twice is the recurring caption-ghost pattern.
2. **Kinetic title vs card title collision.** Overlaying `KineticText` on top of
   `IntroSceneCard`/`OutroSceneCard` while the card still rendered its own plain
   title → doubled text + stray letters. Fix: `hideTitle?` prop on the cards, set
   `hideTitle={kineticTitle}`; also hide the card's decorative ring when hidden.
3. **KineticText edge-to-edge fragmentation.** Outer `AbsoluteFill` was the flex
   `row`, so characters stretched across the full frame width and the centered
   decorative circle overlapped mid-word. Fix: outer node = pure centering
   container; put chars in an INNER `div` with `flexWrap:'wrap'`,
   `justifyContent:'center'`, `maxWidth:'90%'`.
4. **Neon glow washed out.** `NeonCaption` used the brand accent (orange) for its
   halo, diluting the "neon" identity, and was too subtle. Fix: fixed electric
   cyan `#00eaff`, layered `text-shadow` (multiple blur radii), `fontWeight:900`.

## User expectation
The user explicitly pushes past "typecheck passes" — they want the effect SEEN
and confirmed, and they treat "needs Chrome" as a challenge to solve, not a stop.
Do the real render, extract frames, vision-verify, fix what you see, re-render.
Nothing is pushed until the user approves at a green + visually-verified checkpoint.
