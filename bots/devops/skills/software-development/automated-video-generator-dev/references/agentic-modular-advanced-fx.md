# Agentic-modular per-scene advanced FX (agentic-scripts.json → ffmpeg)

The user drives videos via `npm run agentic:modular` (`src/adapters/cli/agentic-modular.ts`)
with `input/scripts/agentic-scripts.json`. This path calls `buildPlan(...)` then
`renderAgenticSlideshow` (render.ts) — it does NOT go through `cli-job.ts`'s `AgenticCliJob`
arrays (`chromaKeyScenes`, `clipSpeedByScene`, etc.), which only feed the legacy `compose` path.
So to make advanced editing reachable from the JSON, add a per-scene `advanced` map.

## Job shape (agentic-scripts.json)
```json
[
  {
    "id": "adv_proof",
    "title": "Advanced FX Proof",
    "script": "Green screen scene. [Visual: greenscreen_test.mp4]\nSlowed scene. [Visual: techclip.mp4]\nB/W scene. [Visual: cityclip.mp4]",
    "orientation": "portrait",
    "kokoroVoice": "af_heart",
    "backend": "agent",
    "hookFirst": false,
    "variablePacing": false,
    "advanced": {
      "0": { "chromaKey": true },
      "1": { "speed": 0.5 },
      "2": { "filter": "bw" }
    }
  }
]
```
Keys are scene **indices** (written as strings in JSON).

## Wiring chain (file:line roughly)
1. `src/agentic/types.ts` `ScenePlan` — add `chromaKey?`, `speed?`, `stabilize?`,
   `filter?: 'bw'|'vintage'|'sepia'`, `blur?`, `keyframes?: {t,z,x?,y?}[]`.
2. `src/agentic/pipeline/plan.ts` — `PlanOptions.advancedByScene?` + in `scenes.forEach((s,i)=>…)`:
   ```ts
   const advRaw = opts.advancedByScene as Record<string,any>;
   const adv = advRaw ? advRaw[i] ?? advRaw[String(i)] : undefined;  // STRING-KEY FIX
   if (adv) { s.chromaKey = adv.chromaKey; s.speed = adv.speed; … }
   ```
3. `src/adapters/cli/agentic-modular.ts` — in the `buildPlan(..., { … })` opts add
   `advancedByScene: job.advanced`.
4. `src/agentic/orchestrator/render.ts` `sceneFilters` map (the `visuals.map((a,i)=>…)`):
   ```ts
   const sp = res.plan.scenes[i];
   const adv: string[] = [];
   if (sp.speed && sp.speed !== 1) adv.push(`setpts=${1/sp.speed}*PTS`);
   if (sp.chromaKey) adv.push('colorkey=green:0.3:0.1');
   if (sp.filter==='bw') adv.push('format=gray');
   else if (sp.filter==='vintage') adv.push('curves=vintage,saturation=1.2');
   else if (sp.filter==='sepia') adv.push('sepia=0.8');
   if (sp.blur) adv.push('boxblur=10');
   if (sp.keyframes?.length>=2) { /* nested if(lte(t,T),Z,…) zoompan expr */ }
   const advStr = adv.length ? ','+adv.join(',') : '';
   // append advStr between settb=1/25 and ,${grade},format=yuv420p
   ```
   All additive; absent fields → today's behavior preserved.

## Traps that cost debug cycles (verified this session)
- **JSON keys are strings.** `opts.advancedByScene?.[i]` (numeric) misses `"0"` → FX never
  apply, render duration unchanged. MUST use `advRaw[i] ?? advRaw[String(i)]`.
- **Stale-frame verification.** After fixing the key bug, the generated filter string shows
  the FX (`[ADV-FILTER] scene 0: …colorkey=green:0.3:0.1…`), but if you vision-check an
  OLD render's frame you'll see "still green / still colored" — that's stale evidence.
  Re-render and inspect the NEW output.
- **Auto-clone hijack (CPU box).** Any `*.wav` in `input/voices/` makes the voice stage
  clone via `chatterbox_turbo` → HTTP 500 on CPU → long stall before render. Move the clip
  aside (`mv input/voices/sample_narrator.wav input/voices/_sample_narrator.wav.bak`) to
  force kokoro and reach the FX stage. chatterbox 500 is environment, not code.
- **speed + xfade timing.** `setpts=2*PTS` extends playback but the scene-duration math still
  uses base duration → slow-mo scenes may overlap the next transition slightly. Functional
  but needs a duration-scaling tweak for perfect timing.

## Local-only proof recipe (avoids the slow stock-download stall)
Generate 3 tiny local clips so no network fetch is needed:
```bash
FFMPEG=$(node -e "console.log(require('ffmpeg-static'))")
"$FFMPEG" -y -f lavfi -i "color=c=green:s=1080x1920:d=4,drawbox=x=440:y=800:w=200:h=200:color=red:t=fill" -t 4 -c:v libx264 -pix_fmt yuv420p input/visuals/greenscreen_test.mp4
# + techclip.mp4 (blue+text), cityclip.mp4 (orange+text)
rm -rf workspace/jobs/adv_proof
npx tsx src/adapters/cli/agentic-modular.ts pipeline --file input/scripts/_adv_proof.json > workspace/logs/adv.log 2>&1
# grep ADV-FILTER (confirms filters in command); ffprobe duration; extract frames (-ss AFTER -i); vision_analyze
```
Use `[Visual: <local>.mp4]` tags so the scenes bind locally (no Pexels fetch, no stall).
