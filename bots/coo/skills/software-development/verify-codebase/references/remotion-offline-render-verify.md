# Physically verifying a Remotion / headless-Chrome video pipeline (offline, low-RAM Windows)

When the user says "run it / test it / physically generate the video", and the host has
enough free RAM + ffmpeg-static + @remotion/renderer present, DO the real render and
validate the artifact. Do not settle for the unit suite or a skip-gated e2e.

## Pre-flight (one command)
- Free RAM: `node -e "console.log(Math.round(require('os').freemem()/1048576)+'MB')"`
  - A 1-scene, 2s fixture hit ~700MB RSS peak at ~1.2GB free — feasible.
    Below ~500MB free, skip or use a 1-frame fixture.
- Assets present? `ls node_modules/@remotion/renderer/package.json` and
  `node_modules/ffmpeg-static/ffmpeg.exe`.
- Remotion's headless Chrome cache: first run auto-downloads ~150MB. Ensure enough
  free space + network on first run.

## Trap: the project's own e2e gate can skip a render that would actually work
Many repos gate the real render behind `RUN_RENDER_E2E=1` AND a
`execSync('ffmpeg -version')` PATH check. On a box with only `ffmpeg-static`
(no global `ffmpeg` on PATH), that check returns false and the real render is
SKIPPED even though ffmpeg IS available.
Fix: either (a) put `node_modules/.bin` / resolve ffmpeg-static on PATH, or
(b) bypass the gate and call `renderVideo(outDir)` directly from a one-off `tsx` script.

## Minimal real-render recipe (one process, validated)
1. Write a fixture `scene-data.json` with `visual:null, audioPath:undefined,
   backgroundMusic:undefined` (no external assets → no network). 1 short scene,
   duration 1-2s.
2. `AUTO_FREE_MUSIC=false` so the free-music resolver doesn't hit the network.
3. One-off script: `import { renderVideo } from '../src/render'; await renderVideo(outDir);`
   then validate in the SAME process before the temp dir is cleaned.
4. Run: `timeout 540 npx tsx scripts/render-smoke.ts` (bound it; headless Chrome +
   webpack bundle can take a minute).
5. Confirm artifacts: final `*.mp4` + `thumbnail.jpg` in outDir.

## Validate the produced mp4 WITHOUT a broken probe flag
This `ffmpeg-static` (gyan.dev essentials 6.1) rejects `-show_format` /
`-show_streams` ("Unrecognized option"). Use the decode-to-null test instead — it
proves the file is a valid, fully-decodable mp4:
    ffmpeg.exe -v error -i "Real Render Probe.mp4" -f null -
    # exit 0 + no stderr errors => VALID PLAYABLE MP4
Also confirm container magic: `head -c 12 file.mp4` should read `ftypisom`
(or `ftyp` + a brand).

## Hardening (this host)
- Re-stat the outDir artifacts in the SAME terminal call as the render (filesystem can
  intermittently revert after heavy tsx/tsc runs).
- Copy the produced mp4 + thumbnail into a project dir (e.g. `output/real-render-proof/`)
  so the evidence survives temp cleanup and the user can open it.

## What this proves vs. doesn't
Proves: the real render path (Remotion bundle → headless Chromium → ffmpeg concat)
works and yields a playable video.
Does NOT by itself exercise: network-dependent features (auto-free-music fetch, a Kokoro
server, Ollama install) — those need their respective services and are unit-tested separately.
