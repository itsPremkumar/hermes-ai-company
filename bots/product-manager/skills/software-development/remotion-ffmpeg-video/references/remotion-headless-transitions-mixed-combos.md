# Headless Remotion transitions, stills, and mixed-source combo videos (July 2026 session)

Findings from building `src/agentic/media/remotion-sequence.ts` / `remotion-verify.ts` in Automated-Video-Generator and the mixed (Pexels + Remotion + screenshot) combo videos.

## @remotion/transitions under headless Chrome (no GPU)
- **Subpath imports required**: `slide` and `wipe` are NOT exported from the `@remotion/transitions` main entry — import from `@remotion/transitions/slide` and `/wipe`. Main entry only has `TransitionSeries`, `linearTiming`, `springTiming`, `crossZoom`, `filmBurn`, `linearBlur`. Wrong import → runtime `(0, esm_namespaceObject.slide) is not a function` (delayRender timeout masks it unless you read the error head).
- **Wipe directions are `from-*`** (`from-right`, `from-left`, ...). `to-left` throws `Unknown direction` from `makePolygonOut`.
- **Shader/canvas transitions HANG headless**: `crossZoom`, `filmBurn`, `linearBlur`, and even `wipe`/`dissolve` (canvas-based) hang under headless Chrome without a GPU — swiftshader (`chromiumOptions: { gl: 'swiftshader' }`) does NOT save them. Only pure-CSS `slide` is reliably safe. Solution shipped: map every transition to `slide` by default; `allowShaderTransitions` opt-in for GPU machines.
- **renderStill needs a real composition duration**: `durationInFrames={1}` makes `frame: 30` invalid ("highest frame = 0"). Give the Still composition e.g. 120 frames.

## "Hang" that was actually slowness / harness kill
A 3-scene TransitionSeries render takes 2–3 min headless (bundle + render). Background runs via the agent harness were killed (~exit 1, log only shows "Load") giving a false hang diagnosis. **Run foreground with `timeout 280` and file-based logging** (`fs.appendFileSync` to a log; `| head`/`| tail` in non-tty swallows stdout). Exit 1 + no ERROR in log = process killed, not a code throw.

## Mixed combo composition (video + image + Remotion + screenshot)
- Pexels URLs from `searchVideos`/`searchImages` are direct-download; if the project's `downloadMedia` fails with `undefined`, native `fetch` + `writeFileSync` with a `User-Agent` header works fine. Load `.env` via `dotenv.config()` in ad-hoc drivers (only mcp-server loads it).
- Compose: normalize videos (`scale=1920:1080:force_original_aspect_ratio=decrease,pad=...`, `-r 30`, `-an`), images → ken-burns via `zoompan=z='min(zoom+0.0008,1.25)':d=<frames>:s=1920x1080:fps=30`, then `-f concat -c copy`.
- **Full-page website screenshots are TALL — never fit-inside+pad** (produces unreadable thin vertical strips; vision check caught this). Correct treatment: `scale=1920:-2,crop=1920:1080:0:'min(t*60,ih-1080)',fps=30` → readable scroll-pan "screen recording" look.
- Screenshot assets: `browser_vision` returns a `screenshot_path` in Hermes cache (`AppData/Local/hermes/cache/screenshots/`) — copy those PNGs into `input/visuals/` as sources.
- Verification pattern that satisfies the user: ffprobe-gate EVERY segment (extract frame at segment midpoint, size >2KB), vision_analyze a representative sample (endpoints + all Remotion/screenshot segments). Write a per-segment pipe-delimited report file.
- Reusable round harness: seed combination shuffles by round name so each round produces different orderings ("continuous" testing).

## ESM driver gotchas
- `.mts` drivers via `node --import tsx`: no `require` (import `spawn` from `child_process`); `node --import tsx -e "..."` breaks dynamic imports — always write a probe file.
