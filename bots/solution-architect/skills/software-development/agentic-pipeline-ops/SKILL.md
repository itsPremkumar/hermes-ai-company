---
name: agentic-pipeline-ops
description: Decompose a monolithic agentic/video-generation pipeline into discrete, independently-callable operations behind an intent router; and investigate a large codebase's REAL command surface before claiming what it can/can't do. Use when a user asks "can the system do X partial task?" (merge two videos, generate voiceover only, trim a clip, extract audio) or wants per-operation granularity from an agentic pipeline instead of only the full generate.
---

# Agentic Pipeline Operations — discrete ops + intent router

## When to use
- A user asks whether their agentic/system can do a PARTIAL task (e.g. "merge two videos", "generate the voiceover only", "just trim this clip", "extract the audio") versus only the full end-to-end pipeline.
- A user wants to extend an agentic pipeline so it can run one step in isolation and return only that artifact.
- You must answer an architecture question about a large existing codebase ACCURATELY (no guessing).

## Step 1 — Map the REAL command surface (never guess)
Grep the actual source for the entry points an agent/user can call:
- MCP tool registrations: `grep -rniE "server\.(registerTool|tool)\(" src --include=*.ts`
- bin entrypoints: `ls bin/*.ts` and read their `--flags` in the file head.
- Exported functions: `grep -nE "export (async )?function" src/agentic/<module>.ts`

CRITICAL — distinguish TWO different capabilities:
1. **Stage-based tools** (plan / acquire / verify / decide / gate / render) let an agent STOP BETWEEN stages, but every path still requires the WHOLE pipeline to eventually run to produce a deliverable.
2. **Discrete operations** (mergeVideos, makeVoiceover, trimVideo, extractAudio) are standalone deliverables — they take user files + params and return ONLY that artifact.

A pipeline with only (1) CANNOT satisfy "do only this part". Confirm which exists before answering, and say so explicitly.

TOOLING NOTE: `search_files` can intermittently fail on Windows/MSYS paths with `rg: ... The system cannot find the path specified. (os error 3)` even when the directory exists. Fall back to `terminal` with `grep -rniE "pattern" <path> --include=*.ts` — it is more reliable for code inspection on this host.

## Step 2 — Identify the gap
For each requested partial op, check: is there a standalone function/tool, or only internal pipeline usage?
- Worked example (user's Automated-Video-Generator, 2026-07-18): `generateAgenticVoiceovers` (src/agentic/tts.ts) exists but is only CALLED inside the pipeline — no standalone "voiceover only" tool. `concat` exists only in `bin/normal-gen.ts` to stitch its OWN generated scene clips — no "merge arbitrary user videos" tool. => Partial ops were NOT wired in. Full pipeline (`bin/agentic-run.ts` / `agentic_run` MCP tool) was all-or-nothing.

## Step 3 — Wrap the pipeline in a simple JSON-input CLI bridge

An agentic pipeline is powerful but HARD to use — users need to write TypeScript, call MCP tools, or import functions. The **JSON-input CLI bridge** pattern gives users a dead-simple workflow: edit a JSON file with their script + config, run one command, get video.

### When to add a CLI bridge

- Users keep asking "can I just write my script in a JSON file and run it?"
- The pipeline requires setup boilerplate (config imports, env loading, progress callbacks)
- You want the simplicity of the legacy system but the power of the agentic pipeline

### Bridge design — JSON input format

Create a JSON input file (e.g. `input/agentic-scripts.json`) with this shape:

```json
[{
  "id": "my-video",
  "title": "My Video",
  "script": "Scene one. [Visual: logo.png]\nScene two. [Visual: github-profile.png]\nScene three. [Visual: ai coding developers]",
  "orientation": "portrait",
  "voice": "en-US-GuyNeural",
  "hookFirst": true,
  "variablePacing": true,
  "backend": "agent",
  "candidatesPerAsset": 2
}]
```

Key fields:
- `script` — custom script with `[Visual: filename]` (local asset) and `[Visual: keywords]` (online stock media) tags. When omitted, the pipeline auto-generates from `title`/`topic`.
- `orientation` — `'portrait'` (9:16) or `'landscape'` (16:9).
- `voice` — Edge-TTS voice name (ignored when `TTS_PROVIDER=voicebox`/`kokoro` — those use the server profile's preset voice).

### CLI runner implementation pattern

A minimal CLI runner reads the JSON, calls the pipeline for each job, then renders:

```typescript
import 'dotenv/config';                    // ← CRITICAL: npx tsx doesn't auto-load .env
import { runAgenticPipeline } from '...';
import { renderAgenticSlideshow } from '...';

const jobs = JSON.parse(fs.readFileSync('input/agentic-scripts.json'));
for (const job of jobs) {
    const result = await runAgenticPipeline(
        { script: job.script, title: job.title, ... },
        (progress) => { /* print progress */ },
    );
    if (result.gate.pass) {
        await renderAgenticSlideshow(result, {
            outPath: `output/${jobId}/${job.title}.mp4`,
            burnCaptions: true,
        });
    }
}
```

### Pitfalls — CLI bridge

- **`dotenv` — the #1 silent failure.** `npx tsx src/cli.ts` does NOT load `.env`. Environment variables like `TTS_PROVIDER`, `VOICEBOX_API_URL`, `VIDEO_VOICE` are all undefined unless you explicitly `import 'dotenv/config'` at the entry point. Symptom: the pipeline falls through to Edge-TTS / Windows SAPI fallback even when `.env` has `TTS_PROVIDER=voicebox`. Fix: add `import 'dotenv/config'` as the FIRST import in the runner.
- **Auto-detect must not overwrite explicit `localAsset`.** When the user writes `[Visual: logo.png]` in their script, `parseScript()` sets that scene's `localAsset = 'logo.png'`. If the pipeline later runs an auto-detect loop that cycles ALL files from `input/visuals/` onto ALL scenes, it overwrites the user's choice. Fix: only bind auto-detected assets to scenes WITHOUT an existing `localAsset` — check `if (!s.localAsset)` before assigning.
- **Gate passes but no video is rendered.** `runAgenticPipeline()` completes after Plan→Acquire→Verify→Decide→Gate→Voiceover. It does NOT render the final MP4. The render must be called SEPARATELY with `renderAgenticSlideshow(result, opts)`. See CLI runner pattern above.
- **Keep script files alongside legacy.** When adding agentic JSON input, place it in `input/scripts/` (same folder as legacy `input-scripts.json`), not in `input/` root. Users expect all script configs in one folder.
- **Voicebox/Kokoro wiring: `TTS_PROVIDER=voicebox` (not `kokoro`).** The `kokoro` provider path uses a separate OpenAI-compatible server on port 8880. For the Voicebox server (port 17493) with Kokoro engine, use `TTS_PROVIDER=voicebox` with `VOICEBOX_ENGINE=kokoro` and a Kokoro preset profile ID.

## Modular Stage-Based CLI (the Stage-Based Tools pattern, implemented)

When the pipeline stages (plan → acquire → verify → decide → voice → render) are already **internally separable** (the workspace stores intermediate plan.json, render-manifest.json, voiceover .wav files), expose each as an independent CLI subcommand. This gives users "run only this step" without the cost of building standalone discrete operations.

### Architecture

```
src/adapters/cli/agentic-modular.ts    # one runner, many subcommands
```

| Subcommand | What it does | Prerequisite |
|---|---|---|
| `plan` | Parse script → build Plan → save `plan.json` + `job-meta.json` | — |
| `visuals` | Acquire + download media → save `render-manifest.json` | plan |
| `voice` | Generate TTS for all/selected scenes → save `.wav` in `audio/` | plan |
| `render` | Render video from existing workspace → output MP4 | plan + visuals + voice |
| `edit` | Modify a single scene's properties + selectively re-render | plan |
| `list` | Inspect workspace — show scenes, tags, stage completion | plan |
| `doctor` | System health check — ffmpeg, Voicebox, Node, workspace, deps, env | — |
| `help` | Display all subcommands + edit flags | — |
| `pipeline` | Full end-to-end (plan → visuals → voice → render) | — |

### CLI entry-point design

The runner reads `input/scripts/agentic-scripts.json` (same format as the full pipeline), but only runs the requested stage. Stages read/write to a shared workspace:

```
workspace/jobs/<jobId>/
  plan.json              # Stage 1 output, Stage 2-4 input
  job-meta.json          # job config snapshot (preserves all settings)
  render-manifest.json   # Stage 2 output, Stage 4 input
  audio/                 # Stage 3 output (scene_N_voice.wav)
  assets/                # Stage 2 output (downloaded media)
```

### Scene Editor (`edit` subcommand)

The `edit` subcommand is a unique pattern — it modifies a single scene in an existing workspace and **selectively re-renders only that scene** without touching the rest:

```
npm run agentic:modular edit --scene 3 --visual "rocket launch" --voice en-IN-ValluvarNeural --volume 0.8 --style center --color cyan
```

**What it does:**
1. Loads the existing `plan.json` from workspace
2. Modifies the target scene's properties (visual, voice, volume, style, color, transition, grade, kenBurns, fadeIn, fadeOut, music)
3. If voice changed → regenerates TTS for ONLY that scene (singleton plan)
4. If visual changed → re-downloads media for ONLY that scene
5. Optionally re-renders ONLY that scene's segment as a standalone MP4 (`scene_N_edit.mp4`)
6. Saves updated `plan.json` for full re-render

**Supported edit flags:** `--scene`, `--visual`, `--voice`, `--volume`, `--style`, `--color`, `--music`, `--transition`, `--grade`, `--ken-burns`, `--fade-in`, `--fade-out`, `--trim` (format: `"00:05-00:10"`), `--trim-start`, `--trim-end`, `--render` (set `false` to skip re-render).

**Full CLI reference:** `npm run agentic:modular help` or `npm run agentic:modular -- --help`

### Doctor / System Health Check

The `doctor` subcommand inspects the system and reports status for:
- **FFmpeg** — version detection via `ffmpeg-static` (or PATH fallback)
- **Voicebox** — curl health check to `127.0.0.1:17493`
- **Node.js** — version check
- **Disk** — available space (Linux `df` or Windows `wmic`)
- **Workspace jobs** — per-job stage completion (plan, visuals, voice, render)
- **NPM dependencies** — `ffmpeg-static`, `tsx`, `dotenv`, `axios`
- **Environment** — `TTS_PROVIDER`, `VOICEBOX_API_URL`, `VOICEBOX_ENGINE`

Usage:
```bash
npm run agentic:modular doctor
```

### npm scripts

Add these to `package.json` for each subcommand:

```json
"agentic:plan": "tsx src/adapters/cli/agentic-modular.ts plan",
"agentic:visuals": "tsx src/adapters/cli/agentic-modular.ts visuals",
"agentic:voice": "tsx src/adapters/cli/agentic-modular.ts voice",
"agentic:render": "tsx src/adapters/cli/agentic-modular.ts render",
"agentic:edit": "tsx src/adapters/cli/agentic-modular.ts edit",
"agentic:list": "tsx src/adapters/cli/agentic-modular.ts list",
"agentic:modular": "tsx src/adapters/cli/agentic-modular.ts",
"agentic:editor": "tsx src/adapters/cli/agentic-editor.ts"
```

## 30-Command FFmpeg Video Editor (the Discrete Operations pattern, implemented)

When the partial ops the user asks about are **simple ffmpeg operations** (trim, speed,
extract audio, crop, rotate, add text, GIF, merge, etc.), the fastest path is a
thin `spawnSync` wrapper around `ffmpeg-static`. This gives standalone CLI commands
with zero new dependencies and zero pipeline integration cost.

**File:** `src/adapters/cli/agentic-editor.ts`
**Entry:** `npm run agentic:editor <command> [options]`

### Command list (30 operations)

| Category | Commands |
|---|---|
| **Trim & Split** | `trim`, `split`, `merge`, `split-scenes` |
| **Audio** | `extract-audio`, `replace-audio`, `mute`, `audio-filter`, `noise` |
| **Speed & Time** | `speed`, `reverse`, `loop`, `freeze` |
| **Transform** | `resize`, `crop`, `rotate` |
| **Visual FX** | `enhance`, `blur`, `adjust`, `chroma-key`, `fade` |
| **Overlay** | `overlay-text`, `overlay-image`, `pip` |
| **Export** | `gif`, `thumbnail`, `extract-frame` |
| **Pipeline** | `concat-scene`, `info` |

### Architecture pattern

Every command follows the same pattern:

```typescript
const COMMANDS: Record<string, (args: Record<string, any>) => void> = {
    'command-name': (args) => {
        const input = resolveInput(args.input);
        const output = resolveOutput(args.output, `default_${path.basename(input)}`);
        const ff: string[] = ['-i', input, /* filter args */, output, '-y'];
        runFfmpeg(ff, 'Description');
    }
};
```

Key helpers: `ffmpegPath()`, `ffprobePath()`, `getMediaInfo(file)`, `runFfmpeg(args, desc)`,
`resolveInput(input)`, `resolveOutput(output, fallback)`.

### Pitfalls — ffmpeg editor CLI

- **`--input` is always required** (except `info` which also needs `--input`).
- **Output defaults** to a timestamped name if `--output` is omitted.
- **ffmpeg memory pressure on low-RAM systems** (~800MB free): operations like `enhance`
  (3-filter chain + libx264 re-encode) or `chroma-key` (compositing two streams) can
  OOM. If RAM is tight, prefer `-c copy` operations (trim, split, merge, mute) or
  lower `-preset` to `ultrafast`.
- **MSYS path trap for ffmpeg-static** — see main Pitfalls section below.
- **For full command reference with examples**, see `references/ffmpeg-editor-commands.md`.

## Step 4 — Decompose (Option A, recommended)
Add a discrete-operations module, register as tools, add an intent router:
1. Create `src/agentic/operations/` with pure functions: `mergeVideos(a, b, out)`, `generateVoiceoverOnly(text, voice, out)`, `trimVideo(in, start, end, out)`, `extractAudio(in, out)`. Keep them ZERO-COST: Edge-TTS for voiceover, ffmpeg-static for everything else. NO paid API keys.
2. Register each as an MCP tool (`server.registerTool('merge_videos', ...)`) so Hermes / any MCP client can call just-the-part.
3. Add a lightweight intent router (plain-language request -> op) that falls back to the full pipeline (`agentic_run`) when no partial op matches.
4. Write tests + VERIFY with real ffmpeg concat and a real Edge-TTS voiceover. Compile + self-test, never just announce.

## Pitfalls
- Do NOT confuse "agent can pause between stages" with "agent can deliver only-this-part". Users asking for partial ops mean (2); the two are different capabilities.
- Keep the zero-cost constraint: Edge-TTS + ffmpeg-static only. Never add a paid API for a partial op.
- The classic/legacy workflow must stay UNTOUCHED — additive parallel pipeline only (matches the user's standing AGENTIC pattern: agentic inherits every working legacy capability).
- **MSYS/POSIX temp-path trap (Windows, costs real iteration):** ffmpeg.exe is a native Windows binary and CANNOT open POSIX-style temp paths like `/tmp/xxx` or the `os.tmpdir()` result on MSYS (typically `/tmp`). Symptom is silent + misleading: `color`/lavfi source "Output file is empty", or "Error opening input: No such file or directory", or `extractAudio` → "Output file does not contain any stream". Fix: build fixtures and outputs under a Windows-valid path such as `fs.mkdtempSync('C:/one/_ops-test-')` (note the forward-slash `C:/` form works; bare `/c/one` also works; `/tmp` does NOT). Applies to ANY ffmpeg-static invocation from a git-bash/MSYS terminal.
- **`extractAudio` / `trim -c copy` need real streams:** a synthetic `lavfi color=...:d=N` source has NO audio track, so `-vn` extract yields "does not contain any stream" and `-ss -to -c copy` trim can yield an empty file. When writing fixtures, give the test clip a real audio track: add `-f lavfi -i sine=frequency=440:duration=N -c:a aac` alongside the video input, muxed with `-shortest`. Then copy-trim and extract-audio exercise real streams.
- **Seek order matters:** `trimVideo` should put `-ss` AFTER `-i` (accurate seek) not before — pre-input `-ss` with `-c copy` on streams that can't keyframe-align silently produces an empty output. Accurate seek post-input always yields frames.
- **verify-before-integrate discipline:** after writing the ops layer, PROVE it ran — do not announce "done" on a green tsc alone. Run the per-op tests on REAL ffmpeg (merge duration == sum of inputs; trim timing; crop/resize/rotate produce a non-empty file; extract-audio yields a real .mp3) + the router-classification tests (pure heuristic, offline). Then `npx tsc --noEmit` clean, then run the pre-existing agentic unit tests to confirm NO regression, THEN commit + push. The recipe is in `references/windows-ffmpeg-verify.md`.
- **Windows/MSYS temp-path trap (the #1 silent ffmpeg.exe failure here):** `os.tmpdir()`/`/tmp` paths are POSIX — the native `ffmpeg-static.exe` cannot open them, producing misleading "Output file is empty" / "No such file" errors. Build fixtures/outputs under a Windows-valid path (`fs.mkdtempSync('C:/one/_ops-test-')`). Full detail + per-op assertions + verification sequence in `references/windows-ffmpeg-verify.md`.
- **`write_file` / `patch` SILENTLY DROPS FILES (worse than corruption):** In this environment `write_file`/`patch` sometimes report success but the file is NOT on disk — no error, no corruption, just absent. Symptom: later `grep`/`require`/tsc says "Cannot find module './foo.js'" or `No such file or directory` for a file you "just wrote". The danger is you only notice when a downstream step fails, and you may waste a cycle re-writing the same vanished file. FIX/DISCIPLINE: (1) ALWAYS confirm a just-written file persists — `test -f path && echo OK || echo MISSING` via `terminal` immediately after `write_file`/`patch`; (2) if it vanished, rewrite deterministically with Python `open(p,'w',encoding='utf-8').write(content)` through `terminal` (this path PERSISTS reliably; the `write_file` tool does not); (3) re-verify on disk after the Python write too. This is distinct from the unicode-corruption trap below — here there is no tsc error to localize; the file is simply gone. See `references/git-drift-file-drop.md`.
- **`write_file` / `patch` unicode + backslash corruption (cascading TS1005 trap):** The file-write path in this environment NORMALIZES certain characters when persisting `.ts` files. Observed concretely (2026-07-18 second build pass): a template-literal containing the arrow `→` (U+2192) was stored as a corrupted multibyte sequence that broke the enclosing string, and regex/backslash sequences like `.replace(/\\/g, '/')` were DOUBLED to `/\\\\/g` (invalid regex) or `basename(f))` got an extra `)` injected. Symptom is a misleading cascade: tsc reports `TS1005: '{' expected` / `TS1136` / `TS1128 Declaration or statement expected` far BELOW the real corruption (often at the next tool/function boundary), making the true line hard to find. FIX recipe: (1) avoid non-ASCII chars (use `->` not `→`) and avoid inline regex-with-backslashes inside template literals — precompute to a variable; (2) when a parse error won't localize, do NOT keep hand-patching with `patch` (it can't see the normalized byte) — rewrite the whole file deterministically via a Python `open(p,'w',encoding='utf-8').write(content)` script run through `terminal` (use `python`, not `python3`, on this box), then re-run `npx tsc --noEmit`. Full recipe + the exact failure transcripts in `references/write-file-corruption.md`. Also see `deterministic-file-edits` for the patch-equivalent of this class.
- **Ground-truth via git, not filesystem assumptions:** When a "missing" file is actually committed to a DIFFERENT branch, restore it with `git checkout <branch> -- src/.../foo.ts` rather than recreating it (recreation risks diverging from the committed version). If `git ls-files src/.../foo.ts` is empty, the file was never committed (untracked/lost) — recreate it. After any `git checkout -- file` of a tracked-but-scrubbed file, confirm `git status` shows it clean or intentional, because the restored version may differ from what `main` HEAD expects.
- **Branch-drift trap (commits land on the wrong branch):** A `git checkout <branch>` or a tool-driven branch switch can leave HEAD on a stray local branch (e.g. `feat/agentic-ops`) so subsequent `git commit` + `git push origin main` either pushes nothing ("Everything up-to-date") or creates an unintended branch. After commits, ALWAYS verify with `git status -sb` (shows `## branch...origin/branch`) and `git rev-parse HEAD` vs `git rev-parse origin/main`. If HEAD drifted, `git checkout main && git merge --ff-only <stray-tip>` then `git push origin main`. Never trust "push succeeded" without checking the remote tip moved.
- **Classify-without-execute is a broken path (router integrity):** When extending an intent router (`route.ts` classify rules) you MUST also add the matching executor (`dispatch.ts` `case`), AND the executor must `import` the module. A classify rule with no handler makes `do_task` route to an op that hits `default` and fails — worse than leaving the op unclassified. Discipline: add route rule + dispatch case + import together; if you only have time for one half, leave the op as a granular MCP tool (already tested) and do NOT add the route rule. Verify both halves with the route-classification tests AND a real dispatch run before committing.
- **Batch tool definition is a paren-magnet:** when adding a many-branch `if/else if` tool handler (e.g. batch over a folder calling 8 different ops), paren mismatches hide easily and tsc only reports them at the tool's closing `});`. Prefer a lookup table / `switch` or a small `applyOp(name, file, out, opts)` helper over 8 inline `cropVideo(f, path.join(...)), {preset})` calls — and double-check every `path.basename(f))` has exactly the parens the call needs. (This was the single most expensive debugging loop in the 2026-07-18 second pass.)

## References
- `references/agentic-cli-bridge.md` — Concrete implementation of the JSON-input CLI bridge for Automated-Video-Generator (2026-07-21). Includes the full `agentic-cli.ts` runner pattern, `agentic-scripts.json` format, `.env` loading fix, and localAsset overwrite fix.
- `references/automated-video-generator-state.md` — current architecture of the user's Automated-Video-Generator agentic layer (what is wired vs missing as of 2026-07-18).
- `references/ffmpeg-editor-commands.md` — Full 30-command reference for the `agentic:editor` CLI: trim, speed, extract-audio, chroma-key, freeze, GIF, overlay, stabilize, and more. Every command with exact options and examples.
- `references/windows-ffmpeg-verify.md` — Windows/ffmpeg-static verification recipe + per-op real-ffmpeg assertions.
- `references/write-file-corruption.md` — `write_file`/`patch` unicode+backslash corruption trap and the deterministic Python-rewrite fix (cascading TS1005 errors).
- `references/git-drift-file-drop.md` — `write_file` silently dropping files, untracked-file scrubbing, branch drift, and the classify-without-execute router trap, with recovery commands.
