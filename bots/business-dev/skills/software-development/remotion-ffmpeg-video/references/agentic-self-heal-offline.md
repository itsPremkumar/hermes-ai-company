# Agentic self-heal + offline run recipes (P22–P25)

Concrete diffs and run recipes for the Automated-Video-Generator (AVG) agentic
pipeline. Companion to P18/P21 in the main SKILL.md. All techniques verified
live on 2026-07-16 against ffmpeg-static 6.1.1 on Windows/MSYS.

## 1. Dead-host rejection in `fetchVisual()` (P22/P23)
File: `src/agentic/orchestrate.ts`, inside `acquireDeps.fetchVisual`.

```ts
fetchVisual: async (keywords, kind, orientation) => {
  const ladder = [keywords];
  if (keywords.length > 1) ladder.push([keywords[0]]);            // bare topic noun
  ladder.push(['coffee', 'nature', 'city', 'technology'].slice(0, 1)); // last resort
  const DEAD_HOSTS = /flickr\.com|staticflickr\.com|live\.staticflickr/i;
  for (const q of ladder) {
    try {
      const res = await fetchVisualsForScene(q, kind === 'video', orientation);
      const arr = !res ? [] : (Array.isArray(res) ? res : [res]);
      const usable = arr.filter((a) => a && typeof a.url === 'string'
        && a.url.length > 0 && !DEAD_HOSTS.test(a.url));   // <-- reject dead Flickr
      if (usable.length > 0) {
        return usable.map((a) => ({
          url: a.url, localPath: '', source: 'openverse/pexels',
          license: a.license, licenseUrl: a.licenseUrl,
        } as FetchedVisual));
      }
    } catch (e) { /* try next in ladder */ }
  }
  // true last resort: bright card (see #2)
  const ph = makePlaceholder(keywords, kind);
  return [{ url: '', localPath: ph, source: 'placeholder',
    license: 'CC0 (generated placeholder)', licenseUrl: '' } as FetchedVisual];
},
```

## 2. Bright placeholder card placed IN the scene dir (P23)
File: `src/agentic/orchestrate.ts`, `download` wrapper failure branch, and
`makePlaceholder`.

```ts
// download() — on final failure, place the card inside `dir`:
const local = require('path').join(dir, filename.replace(/(\.[^.]+)?$/, '.png'));
const ph = makePlaceholder([filename.replace(/\.[^.]+$/, '')], 'image');
try { require('fs').copyFileSync(ph, local); } catch { /* ignore */ }
return local;
```

```ts
// makePlaceholder() — BRIGHT background (luma > 55, clears blackdetect ~38):
const color = kind === 'video' ? '0x2a9d8f' : '0x264653';  // was 'teal'/'navy' (navy luma~15 FAILED)
```

Why: navy (luma ~15) fell under `blackdetect pix_th=0.15` (~luma 38) → a
legitimately-missing image was falsely flagged as black by X10. Bright teal
passes.

## 3. Offline deterministic run recipe (P24)
```bash
export PEXELS_API_KEY="<key>"
export OPENVERSE_ENABLED=false        # skip dead Flickr-sourced Openverse URLs
npx tsx bin/agentic-auto.ts --topic "5 fascinating facts about coffee" \
  --title "Coffee Facts" --images --preset cinematic --no-sfx --max-attempts 1
```
- `--max-attempts 1` avoids the 3× Edge-TTS 25s-timeout retry budget
  (25s × 3 scenes × 3 attempts ≈ 225s → shell 200s timeout / EXIT=124).
- `--no-sfx` skips the 404-ing free-music providers offline.
- Single attempt renders in ~60–90s; ffmpeg encode is fast, the only wait is the
  one-time 25s voice-fallback timeout per scene.
- Online (Edge-TTS reachable, music providers up): drop `--no-sfx` and
  `OPENVERSE_ENABLED=false`; real narration + soundtrack work.

## 4. Per-scene image diversity (P25)
File: `src/agentic/agent.ts`, `writeScriptHeuristic`.

```ts
const kw = primaryNoun(topic);                       // e.g. "coffee"
const angles = [`${kw} cup`, `espresso machine`, `barista cafe`,
                `${kw} beans roast`, `latte art`, `${kw} pour over`];
const visualFor = (i: number) => angles[i % angles.length];
// scene 0 -> "coffee cup", scene 1 -> "espresso machine", scene 2 -> "barista cafe"
```
Critical: the LEADING word must differ across scenes (the fetcher joins ALL
keywords into one query; a shared leading noun → same top Pexels result →
identical image → AI-generated look). Test assertion:
`writeScriptHeuristic('coffee','Coffee Facts')` → ≥2 distinct `[Visual: ...]` tags.

## Visual verification (independent of X10 gate)
```bash
FFMPEG=$(node -e "console.log(require('ffmpeg-static'))")
"$FFMPEG" -i render/<job>.mp4 -vf "blackdetect=d=0.3:pix_th=0.15" -f null -
# no "black_start" line == non-black == visually valid
```
Extract a representative frame to inspect content:
```bash
"$FFMPEG" -ss 3 -i render/<job>.mp4 -frames:v 1 -y verify_<name>.png
```
A real photo frame is ~250KB–1.1MB; a black frame would be ~5–10KB.
