# AVS: verify-before-push protocol + patch-tool false-positive gotcha

## 1) The `patch` tool's inline `lint` field LIES on Windows (TS6053)

After every `patch`/`write_file` on this repo, the tool returns a `lint` block
like:

```
"lint": {"status": "error", "output": "error TS6053: File
'/c/one/Automated-Video-Generator/src/agentic/orchestrator/pipeline.ts'
not found."}
```

**This is a false positive** — the patcher resolves the path as
`/c/one/...` (MSYS style) while tsc expects `C:/one/...`. The file IS written
correctly. Do NOT chase it. The REAL gate is:

- `npm run typecheck` (tsc --noEmit on `tsconfig.json`) — MUST be 0 errors.
- `npm run lint` — 0 errors required; ~2426 pre-existing warnings are NOT yours.

Real errors (the ones that matter) surface as `error TS2307` (module not
found — usually a wrong relative `../` depth), `TS2345` (wrong arg type/order),
`TS7006` (implicit any). Fix those; ignore the TS6053 wrapper.

## 2) Empirical end-to-end verification (the user's standard)

"Verified" = real ffmpeg pixel QA, NOT the pipeline's own X7–X15 checks.

On the 6GB box:
1. **Free RAM first.** Close the browser (Brave/Chrome) — `powershell -command
   "Stop-Process -Name brave -Force"`. Observed: 0.77 GB -> 1.9 GB after killing
   Brave + msedgewebview2. Do NOT kill Hermes, Windsurf, or the language server.
2. **Run a real job** backgrounded with notify (it takes minutes):
   `npm run agentic -- --topic "..." --title "..." --backend agent --orientation landscape --images`
   Poll `workspace/jobs/<jobId>/` for progress (plan.json, audio/*.wav,
   verification/*.json). Voice cache writes `<file>.wav.txt-hash` sidecars.
3. **Independent ffmpeg QA on the output mp4** (pipe to null, grep the stderr):
   - duration/size: `ffprobe -v error -show_entries format=duration,size`
   - black frames: `-vf blackdetect=d=1:pix_th=0.10` -> expect "no black frames"
   - frozen frames: `-vf freezedetect=n=0.003:d=1` -> expect "no frozen frames"
   - speech present: `-af volumedetect` -> mean_volume around -21 dB, max ~-3 dB
     (proves SAPI voice + ducking produced real audio, not silence)
   - codec/dims: `ffprobe -v error -show_entries stream=codec_name,width,height`

## 3) Push protocol (user said "push the correct part of the code")

- Stage EXPLICITLY: `git add <file1> <file2> ...`. Never `git add -A` — there
  are untracked junk artifacts (`$null`, `venv_install.log`) at repo root that
  are gitignored, so they won't stage, but don't risk it.
- It's normal for a feature to span BOTH pre-existing uncommitted WIP and your
  new files (e.g. P1#3: `lib/visual-fetcher/provider-health.ts` was an untracked
  WIP, `agentic-modular.ts`/`search.ts` were modified-but-uncommitted, and
  `adapters/cli/provider-health.ts` was your new wrapper). If they form ONE
  coherent feature and all typecheck/lint clean, commit + push them TOGETHER.
- Commit message should list the feature IDs (P1#4, P2#3, P2#1) and state
  "Verified: npm run typecheck clean, npm run lint 0 errors."
- Push to `origin/main` (the user's own repo). Branch is `main`.
