# Prompt & Documentation Verification Technique

## Goal
Verify that every claim in an agent system prompt, README, or documentation file matches the actual codebase exactly.

## Procedure

### Step 1: Extract claims
Identify every empirical claim in the document:
- npm script names (`npm run agentic:plan`, `npm run agentic:batch`, etc.)
- CLI command names and flags (`trim --input --start --end`, `--no-acquire`, `--gpu`)
- Config values (transitions: `fade|slide|zoomblur|cut|mixed`, grades, caption themes)
- Function names (`runRemotionController()`, `renderStillClip()`)
- File paths (`src/agentic/media/hermes-remotion-controller.ts`)
- JSON field names (`id`, `title`, `script`, `videoType`, `aiVerify`)
- Enum values (video types, orientations, providers)

### Step 2: Source-of-truth grep
| Claim type | Source of truth | Command |
|---|---|---|
| npm scripts | `package.json` | `grep -n '"agentic:|"qa:' package.json` |
| CLI commands | Source file (e.g. `agentic-editor.ts`) | `head -40 src/adapters/cli/agentic-editor.ts` |
| Config types | `src/agentic/config.ts` | `grep -n "export type" src/agentic/config.ts` |
| Config interface fields | `src/agentic/config.ts` | `sed -n '/AgenticConfig/,/^}/p' src/agentic/config.ts` |
| Caption themes | `src/agentic/config.ts` | `grep -A30 "CAPTION_THEME_PRESETS" src/agentic/config.ts` |
| Video type templates | `src/agentic/config.ts` | `grep -A12 "VIDEO_TYPE_PROFILES" src/agentic/config.ts` |
| Media providers | `src/lib/visual-fetcher/search.ts` | `grep "import.*from" src/lib/visual-fetcher/search.ts` |
| Function exports | Source files | `grep -n "export.*function\|export.*async" src/agentic/media/*.ts` |

### Step 3: Build verification matrix
| Claim | Source of Truth | Expected | Actual | Match | Fix |
|---|---|---|---|---|---|
| `npm run agentic:editor trim` | `package.json` | `agentic:editor` | `agentic:editor` exists | ✅ | — |
| "neon" caption theme | `CAPTION_THEME_PRESETS` | Not in the presets | Not present | ❌ | Remove from doc |
| `renderStillClip()` location | `grep -rn "renderStillClip" src/` | `remotion-sequence.ts:158` | `remotion-sequence.ts:158` | ❌ | Fix ref in doc |

### Step 4: Fix
- Fix the **document** to match the codebase — never fix the codebase to match documentation.
- Make one commit per logical fix group.

## Prompt Library Organization
```
prompts/
├── README.md                    # Index with file, role, use case, numbering convention
├── 01-system-prompt-master.txt  # Plan / Orchestrate
├── 02-script-writing.txt        # Script
├── 03-asset-acquisition.txt     # Acquire
├── 04-image-processing.txt      # Process
├── 05-audio-production.txt      # Audio
├── 06-video-editing.txt         # Edit
├── 07-end-to-end-production.txt # Deploy
├── 08-batch-production.txt      # Scale
├── 09-pipeline-configuration.txt# Configure
├── 10-quality-assurance.txt     # QA
└── 11-troubleshooting.txt       # Debug
```
- Numbered `NN-` prefix in workflow order
- Clean names without redundant `prompt-` prefix
- README.md file index documenting each file
