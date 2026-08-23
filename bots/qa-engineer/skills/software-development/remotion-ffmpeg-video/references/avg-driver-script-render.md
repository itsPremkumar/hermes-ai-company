# AVG: driver-script rendering & TTS/CI pitfalls (session 2026-07-19)

Concrete, reusable lessons from driving the Automated-Video-Generator agentic
pipeline to actually render a short video offline (no API keys). All verified
against real runs, not guessed.

## 1. script-parser: `[visual cue]` MUST be on the SAME line as the sentence
The parser (`src/lib/script-parser.ts`) splits scenes on blank lines, but a
`[cue]` placed on its OWN line becomes a SEPARATE scene (parsed as a scene with
the bracket text as its keywords). To get N intended scenes, put the cue inline:

```
A single glass can sharpen focus and lift that afternoon brain fog. [glass of water]
```

NOT:
```
A single glass can sharpen focus and lift that afternoon brain fog.
[glass of water]   <-- this becomes its own (garbage) scene
```

Symptom: plan reports 2× the scenes you wrote, each with weird `[...]` keywords,
and total duration balloons.

## 2. Fetched VIDEO clips inflate scene duration past the scripted length
`renderAgenticSlideshow` overrides `scene.durationSec` with the fetched video
clip's REAL length (`estimateAudioDurationSafe` on the clip). So a 29s stock
clip makes the scene 29s → total blows past the X5 `≤60s` gate (and 6 such
scenes = ~171–314s). Fix: pass `preferVisual: 'image'` (or set
`req.preferVisual='image'`) so scenes use still images and keep the scripted
~5–8s each. Plan total then ≈ sum of parser durations (≈ `ceil(chars/15)`,
~7s/scene → ~42s for 6 scenes). This is the reliable way to hit a 30–60s target
offline.

## 3. VOICEBOX_PROFILE_ID placeholder → TTS hang + render timeout
If `.env` has `VOICEBOX_PROFILE_ID=<your-voicebox-profile-id-here>` (placeholder),
the TTS layer tries Voicebox, gets `ECONNREFUSED 127.0.0.1:17493`, and retries
3×/scene with ~40s waits → the whole render times out. Fix for offline runs:
`env -u VOICEBOX_PROFILE_ID npx tsx bin/...` so it falls back to Edge-TTS (if
network) or agent tone fallback. (Real Voicebox needs the GPU backend running
with a valid profile id.)

## 4. KNOWN UNRESOLVED: `spawn ENAMETOOLONG` on render
When rendering with the agent tone fallback, the temp voiceover paths
(`C:\Users\PREM KUMAR\AppData\Local\Temp/agentic_vo_<ts>_<i>_<rand>.wav`) plus
the long workspace/output paths can push the ffmpeg CLI arg string past the
Windows 8KB limit → `spawn ENAMETOOLONG`. Gate passes, voiceover done, then
`renderAgenticSlideshow` crashes spawning ffmpeg. Suspected fix: shorten temp
paths (set `TEMP`/`TMP` to a short path like `C:\T`) or split the ffmpeg filter
chain. NOT yet fixed as of this session — record here when resolved.

## 5. Driver-first script injection (the "driver writes the script" mode)
`runAgenticPipeline` accepts `req.agent.writeScript: (topic,title)=>Promise<string>`.
Injecting your own script here makes the DRIVER (not the offline heuristic) the
author — this is the user's standing "driver-first" rule in action. The
returned string is parsed by `parseScript` (see #1 for format). Backend
`agent` needs NO keys; it uses free Openverse/Wikimedia/Internet Archive sources
for visuals when Pexels key is absent (some downloads 403 → placeholder card
fallback, which is fine).

## 6. gitleaks-action@v3 PR-scan fix (CI)
The `Secret Scan (gitleaks)` job fails on PRs with:
"🛑 GITHUB_TOKEN is now required to scan pull requests."
Fix in `.github/workflows/ci.yml`: the job needs BOTH
```yaml
permissions:
  contents: read
  pull-requests: read
```
AND the token passed as an ENV var (NOT `with: token:` — that is an invalid
input and warns "Unexpected input(s) 'token'"):
```yaml
- name: Run gitleaks
  uses: gitleaks/gitleaks-action@v3
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    GITLEAKS_ENABLE_UPLOAD: 'false'
```
(The "Review Dependencies" job failing separately is just the repo's Dependency
Graph being disabled in GitHub Settings → Security; enable it there, not code.)
