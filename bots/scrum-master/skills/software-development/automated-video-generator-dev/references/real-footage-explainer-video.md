# Bypass-compose: build a "real data + real footage" explainer video

When the user wants a video about a company/topic's REAL numbers or REAL images (e.g.
"Google & YouTube's actual earnings"), the AVS `compose` mode is the WRONG tool: it fetches
visuals by keyword and only honors ONE `defaultVisual` fallback image for ALL empty scenes — you
cannot pin specific verified images to specific scenes. Instead, assemble the slideshow directly
with `node_modules/ffmpeg-static/ffmpeg.exe`. This was proven building
`workspace/jobs/google_youtube_earnings/google_youtube_earnings.mp4` (1:23, 1080x1920, h264+aac,
real Edge-TTS narration, 11 vision-verified CC images).

## Why bypass compose (not a workaround, a hard limit)
`runCompose` (single-feature.ts ~L527) loops scenes, calls `runBulkImageFetch(kw,...)` per scene,
and only falls back to `job.defaultVisual` when fetch returns nothing. There is NO per-scene
local-file pin. So to use 11 specific real photos, drive ffmpeg yourself.

## Pipeline (proven order)
1. **Facts from PRIMARY source.** Never a blog. For Alphabet/Google: SEC EDGAR.
   - Submissions index: `https://data.sec.gov/submissions/CIK0001652044.json` (CIK 0001652044).
   - XBRL metric: `https://data.sec.gov/api/xbrl/companyconcept/CIK0001652044/us-gaap/Revenues.json`
     — filter `units.USD` entries with `fp=='FY'` + `end` for ANNUAL; for quarterly segments read
     the 8-K text: `https://www.sec.gov/Archives/edgar/data/1652044/<ACCN_NO_DASHES>/<ACCN>.txt`.
   - **MUST send a `User-Agent` header** (e.g. `research@example.com`) or EDGAR returns 403.
   - Verified figures used (2026-07-25): FY2025 revenue **$402.8B**, net income **$132.2B**;
     Q2-2026 (qtr ended 2026-06-30) revenue **$119.8B** (+24% YoY), operating income **$40.8B**
     (34% margin), YouTube ads **$11.06B** (+13%), Google Cloud **$24.8B** (+82%),
     Google Services **$94.5B** (+15%).
2. **Images from Openverse** (CC aggregator; AVS itself uses it). `https://api.openverse.org/v1/images/?q=<query>&page_size=N&license_type=all`.
   - Keep ONLY commercial-friendly licenses: `by`, `by-sa`, `cc0`, `pdm`. Drop `by-nc*`, `by-nd`.
   - **VISION-VERIFY EVERY DOWNLOAD.** Openverse returned WRONG matches under "Google"/"YouTube":
     a D-Wave boardroom (labelled data center), a 1902 Theodore Roosevelt stereoview (labelled
     YouTuber), the Tin Man (labelled Android), a Ghibli Castle-in-the-Sky robot (labelled Android).
     Reject anything not obviously on-topic; dedupe by md5 (the downloader reused bytes for two
     queries -> same file, different name).
   - No CC VIDEO exists for these topics on Commons/Openverse (video API 404s) -> motion comes from
     Ken Burns `zoompan` on stills (legitimate, not a placeholder).
3. **Voiceover**: `py-edge-tts` is installed. `edge_tts.Communicate(text,'en-US-JennyNeural')`,
   `await comm.save('vN.wav')`. Probe duration with `ffmpeg -i vN.wav` -> `Duration: H:M:S.ms`;
   hold each scene = narration + ~0.4s. Real voice, no tone fallback.
4. **Per-scene clip**: Ken Burns via zoompan, length = narration duration.
   ```
   ffmpeg -y -loop 1 -i <img> -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.0008,1.14)':d=<frames>:s=1080x1920:fps=25:x='if(gte(zoom,1.02),x+5,x)'" -t <dur> -r 25 -pix_fmt yuv420p -c:v libx264 -preset veryfast -crf 20 <segN>.mp4
   ```
   Alternate `x=`/`y=` per scene for pan direction variety.
5. **Burn caption per scene** (AVS-style lower-third):
   ```
   drawtext=text='<CAPTION>':fontfile='C\:/Windows/Fonts/arialbd.ttf':fontcolor=white:fontsize=58:bordercolor=black:borderw=4:x=(w-tw)/2:y=h-th-120:box=1:boxcolor=black@0.45:boxborderw=20
   ```
   Escape: `text.replace('\\','\\\\').replace(':','\\:').replace("'","'\\''")`.
6. **Title card (3s) + end card (4s)** with `drawtext` (two filters, comma-separated is FINE for
   drawtext; the comma rule only bites inside `enable=`).
   - Title copy: keep <= ~46 chars; fontsize <= 52 on 1080-wide. End CTA <= ~38 chars; fontsize <= 50.
   - SEE TRAP #3 below — larger font truncates the right edge (vision caught "MAK" and "breakdow").
7. **Concat** title + seg0..N + end. **TRAP #1: write ABSOLUTE paths** in the concat list
   (`file 'C:/one/.../seg0.mp4'`), never `build/seg0.mp4` (ffmpeg resolves relative to the list
   file's dir -> `build/build/seg0.mp4` -> fail -> silent 9.9s output).
8. **Audio**: concat `vN.wav` (absolute paths again) -> `narr_full.wav`; add a quiet ambient
   `sine=frequency=110:duration=85` at `volume=0.06` via `amix=inputs=2:duration=longest` -> aac.
9. **Final mux**: `ffmpeg -i final_video_only.mp4 -i mixed.wav -map 0:v -map 1:a -c copy <out>.mp4`.
   **TRAP #2: do NOT use `-shortest`** here — it truncated 76s video to 11s. Assert `Duration`
   after mux.

## ffmpeg concat/mux traps (captured 2026-07-25)
1. **concat `file` list path**: resolved relative to the LIST FILE's dir, not CWD. Use absolute paths.
2. **`-shortest` on a copy-stream mux** can truncate to the wrong stream. Use `-map 0:v -map 1:a -c copy`, no `-shortest`; assert Duration.
3. **Text overflow**: `drawtext x=(w-tw)/2` centers but oversized font truncates the right edge. Cap title ~52px / end ~50px and shorten copy; vision-check.
4. **`execute_code` sandbox does NOT persist large downloads** to real FS — run the downloader as a `.py` via `terminal`.
5. **`vision_analyze` rejects `/c/one/...`** — use literal `C:/one/...`.

## Provenance manifest (ship it with the video)
`assets/MANIFEST.md` table: file | subject (vision-verified) | license | source. Plus a "Financial
figures" section citing the exact SEC endpoint/accession, and a licensing note (NC assets are fine
for personal/educational; for public release prefer the CC0/PDM/BY files and attribute creators).

## Verification (your quality bar)
Extract frames with `-ss AFTER -i` (output-accurate seek; `-ss before -i` returns black/garbage on
shifted streams) and `vision_analyze` each: title, 2-3 mid scenes, end card. Confirm 9:16
orientation, caption readable + NOT truncated, real on-topic image, figures correct, SUBSCRIBE +
hashtags present on end card. Use `C:/one/...` paths in vision_analyze (MSYS `/c/one` 404s).

## Tooling notes
- ffmpeg binary: `node_modules/ffmpeg-static/ffmpeg.exe` (resolve via
  `os.path.abspath(os.path.join(ROOT,'..','..','..','node_modules','ffmpeg-static','ffmpeg.exe'))`
  from the job dir).
- py-edge-tts, vision_analyze, and the Openverse/SEC endpoints are all available on this box.
