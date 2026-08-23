# AVS Offline End-to-End Verification Recipe (proven 2026-08-04)

Self-contained, network-free proof that the AVS pipeline produces a real, correct video.
Written because the older `references/` docs and `scripts/gen-variety.ts` / `monitor.ts` /
`verify-visual.ts` cited by the parent skill are ABSENT from the current checkout. This recipe
was run end-to-end on 2026-08-04 and produced 4 valid multi-aspect MP4s with real speech.

## Prerequisites (confirmed present on this box)
- `node_modules/ffmpeg-static/ffmpeg.exe` + `node_modules/ffprobe-static/` (win32 bin).
- Local fixtures in `input/visuals/`: at minimum `a.mp4` + `b.mp4` (portrait 720×1280
  yuv420p, ~3s each) and a few `ai_*.jpg` stills. If `a.mp4`/`b.mp4` are missing, generate
  them (see G24):
  `ffmpeg -y -f lavfi -i "color=c=teal:s=720x1280:d=3:r=25" -pix_fmt yuv420p -c:v libx264 -preset ultrafast input/visuals/a.mp4` (+ orange → b.mp4).
- RAM: ~1 GB free is enough for ONE 3-scene render (render ONE video at a time to avoid the
  G25 OOM cascade). Kill Brave first if free RAM < 0.5 GB.
- `npm run typecheck` must already be green (`tsc -p tsconfig.json --noEmit`, exit 0).

## Step 1 — author a local-asset job (no network)
Write `input/scripts/<name>.json` as a BARE JSON ARRAY (NOT `{jobs:[...}`):
```json
[
  {
    "id": "audit_p9x16",
    "title": "AVS Audit Reel",
    "orientation": "portrait",
    "hookFirst": false,
    "kenBurns": true,
    "kineticText": true,
    "captions": "burned",
    "captionTheme": "bold",
    "grade": "cinematic",
    "musicQuery": "calm ambient",
    "script": "Narration line one. [Visual: a.mp4]\nLine two. [Visual: ai_city_night.jpg]\nLine three. [Visual: b.mp4]"
  }
]
```
Rule: ONE `[Visual: file]`-tagged line = ONE scene. Bind only bare filenames that already
exist in `input/visuals/` (else the local asset is silently skipped → render dies with
"No approved visuals to render"). `musicQuery` needs NO API key (bundled tone fallback if off).

## Step 2 — run the 4 stages with workspace isolation (background-safe)
```bash
cd /c/one/Automated-Video-Generator
export AGENTIC_WORKSPACES_ROOT="C:/one/Automated-Video-Generator/workspace/audit-iso"
export AGENTIC_KEEP_WORKSPACES=5
rm -rf workspace/audit-iso && mkdir -p workspace/audit-iso workspace/tmp_agent_run
LOG=workspace/tmp_agent_run/audit_run.log; : > "$LOG"
{ echo "=== PLAN ===";  npx tsx src/adapters/cli/agentic-modular.ts plan   --file input/scripts/<name>.json >> "$LOG" 2>&1; echo "PLAN_RC=$?"
  echo "=== VOICE ==="; npx tsx src/adapters/cli/agentic-modular.ts voice  --file input/scripts/<name>.json >> "$LOG" 2>&1; echo "VOICE_RC=$?"
  echo "=== VISUALS --no-acquire ==="; npx tsx src/adapters/cli/agentic-modular.ts visuals --no-acquire --file input/scripts/<name>.json >> "$LOG" 2>&1; echo "VIS_RC=$?"
  echo "=== RENDER ==="; npx tsx src/adapters/cli/agentic-modular.ts render --file input/scripts/<name>.json >> "$LOG" 2>&1; echo "RENDER_RC=$?"
} && echo "ALL_STAGES_DONE" >> "$LOG"
```
Isolation (`AGENTIC_WORKSPACES_ROOT`) prevents another session's `pruneWorkspaces()` from
wiping the in-flight render (G26). All four stage RCs must be 0. A 3-scene render takes ~60–120s.

## Step 3 — locate output
`output/<id>/` holds `<Title>.mp4` (portrait) + `_16x9` / `_1x1` / `_9x16` aspect variants,
plus `<Title>.srt`/`.vtt` and `<id>_thumbnail.jpg`.

## Step 4 — EMPIRICAL verification (the gate; never trust "exit 0" alone)
```bash
F="output/<id>/<Title>.mp4"; FF=./node_modules/ffmpeg-static/ffmpeg.exe
# dims + SAR (portrait must be 720x1280, SAR 1:1)
$FF -hide_banner -i "$F" 2>&1 | grep -E "Duration|Stream.*Video|Stream.*Audio"
# SPEECH PROOF (astats) — tone fallback = zcr≈0.01, peak≈-34.5dB; real speech = zcr 0.05–0.2, peak≈-0.3dB
$FF -hide_banner -i "$F" -af astats -f null - 2>&1 | grep -E "Peak level dB|Zero crossings rate"
# no blank frames / no frozen frames (empty output = good)
$FF -hide_banner -v error -i "$F" -vf "blackdetect=d=0.5:pic_th=0.98" -f null - 2>&1
$FF -hide_banner -v error -i "$F" -vf "freezedetect=d=2" -f null - 2>&1
# loudness (needs -v verbose, NOT -v error — G16)
$FF -hide_banner -v verbose -i "$F" -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"
# pillarbox check (needs -v info, NOT -v error — G21)
$FF -hide_banner -v info -i "$F" -vf "cropdetect=limit=16:round=2" -f null - 2>&1 | grep "crop=" | head
```
Pass criteria: video+audio streams present; SAR 1:1; **zcr > 0.05** (real speech, not tone);
blackdetect/freezedetect empty; mean_volume ≈ -20 to -30 dB; cropdetect = full frame (no bars).

## Step 5 — visual frame inspection (mandatory; G4)
Extract with INPUT seek (`-i file -ss N`, never `-ss N -i file` — G8):
```bash
$FF -hide_banner -v error -i "$F" -ss 5 -frames:v 1 workspace/tmp_agent_run/frames/s2.jpg -y
$FF -hide_banner -v error -i "$F" -ss 9 -frames:v 1 workspace/tmp_agent_run/frames/s3.jpg -y
```
Then `vision_analyze` each: confirm correct aspect, burned caption legible + matches
narration, NO black-box watermark corner (G1/G22 fixed), main visual visible. Different
JPG byte sizes at different timestamps ⇒ distinct content (not frozen).

## Control-surface audit
`scripts/verify-control-surface.ts` is FIXED (2026-08-04): it now scans every `*.json` array
under `input/scripts/` instead of the non-existent `input/scripts/examples/` dir. Run it directly:
`npx tsx scripts/verify-control-surface.ts` → expect `jobs=N checks=M passed=M failed=0`.
(2026-08-04 real result: 66 jobs × 398 FX-field assertions, all pass → schema→pipeline intact.)
The manual `ctl-check.ts` workaround below is retained only as a fallback if the script regresses.

Write `workspace/tmp_agent_run/ctl-check.ts` (only if the script above is unavailable):
```ts
import { buildPipelineRequest } from 'C:/one/Automated-Video-Generator/src/adapters/cli/cli-job.js';
import * as fs from 'fs';
const BASE = 'C:/one/Automated-Video-Generator';
const SCRIPTS = BASE + '/input/scripts';
const FX_FIELDS = ['chromaKeyScenes','blurScenes','stabilizeScenes','clipSpeedByScene','paletteFilter','filterByScene','emojiByScene','sfxByScene','sfxOnCut','loopVideo','exportFormat','contactSheet','posterScene','titleCard','lowerThird','endCta','progressBar','musicQuery','licenseFilter','voiceSpeed','dialogueVoices','captionTheme','captions','kenBurns','transition','grade','kineticText','vignette','jCutSec','preset','format','aspect','platform','videoType','brand','renderer','maxAttempts','languages','intro','outro','backgroundMusic','musicVolume','candidatesPerAsset','hookFirst','variablePacing','backend'];
let jobs=0, checks=0, passed=0; const fails:string[]=[];
const live = JSON.parse(fs.readFileSync(SCRIPTS+'/agentic-scripts.json','utf8'));
for (const job of live) {
  if (!job || typeof job!=='object' || !('id' in job)) continue;
  const id=(job.id||'x').toLowerCase().replace(/[^a-z0-9]+/g,'_').slice(0,64);
  const req = buildPipelineRequest(job as any, id, job.topic??job.title??'Untitled');
  jobs++;
  for (const f of FX_FIELDS) if (f in job && job[f]!==undefined) {
    checks++; const ok = JSON.stringify((req as any)[f])===JSON.stringify(job[f]);
    if (ok) passed++; else fails.push(`${job.id}.${f}`);
  }
}
console.log(`jobs=${jobs} checks=${checks} passed=${passed} failed=${fails.length}`);
if (fails.length) console.log('FAIL:', fails.slice(0,20));
```
Run: `npx tsx workspace/tmp_agent_run/ctl-check.ts`. Expect `checks=NNN passed=NNN failed=0`.
(2026-08-04 real result: 17 jobs × 105 checks, all passed → schema→pipeline ingestion intact.)

## Known-expected fallbacks — do NOT flag as bugs
- `⚠ voicebox backend unavailable ... using Edge-TTS fallback` then SAPI: EXPECTED (Kokoro
  needs GPU/RAM this box lacks). The 2026-08-04 run produced REAL speech via SAPI
  (zcr 0.07–0.10, peak ≈ -0.3 dB) — proof the fallback path works, not a tone substitute.
- `music duck expression unsupported on this ffmpeg build; using flat volume`: EXPECTED (G2/G10).

## Repo-level QA gotchas (2026-08-04)
Two SILENT defects surfaced while making the verification workflow runnable + pushing (the
build/push "works" until a linter or a second account objects):

1. **Duplicate JSON keys in `package.json` are a SILENT lint defect.** Node/TS `JSON.parse`
   accepts duplicate object keys (last-wins), so `npm run <script>` keeps working — but the
   editor's JSON language server flags `Duplicate object key` (severity 4), and it IS a real
   defect. This repo had `agentic:batch` twice (`bin/agentic-batch.ts` vs
   `src/adapters/cli/agentic-batch.ts`) and `agentic:clean` twice. **De-dup before committing
   any `package.json` edit.** A naive `JSON.parse` reviver with a `seen` object gives FALSE
   `DUP KEY: 14` positives on array indices — use a line-scan scoped to top-level objects:
   ```bash
   node -e "const t=require('fs').readFileSync('package.json','utf8').split('\n');const d=[];let s={};for(const l of t){const m=l.match(/^\s*\"([^\"]+)\"\s*:/);if(m){if(s[m[1]])d.push(m[1]);s[m[1]]=1;}if(/^\s*[}\]]\s*,?\s*$/.test(l)&&!/[{[]/.test(l))s={};if(/[{[]/.test(l))s={};}console.log(d.length?'DUPS: '+d.join(', '):'clean')"
   ```
2. **GitHub push 403 between two logged-in `gh` accounts (prem-the-dev vs itsPremkumar).** When
   `gh auth status` shows `prem-the-dev` active but the remote is `itsPremkumar/...`, a push can
   fail `Permission denied to prem-the-dev` / HTTP 403. This is a **transient keyring token-swap
   race** — a plain `git push` retry succeeded seconds later. Do NOT immediately `gh auth switch`
   or rewrite remotes; retry once first. If it persists, confirm the active `gh` account
   (`gh auth status`) matches the repo owner, then `gh auth switch <owner>` as last resort.
