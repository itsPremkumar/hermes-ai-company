# Brand-strip decision matrix (vendored backend renames)

When the user says "remove the [upstream] name / voicebox from the project",
apply this matrix. Derived from 3 explicit demands in one AVS session.

## What to rename (kill the brand in project source)
| Layer | Example | Tool |
|---|---|---|
| File / folder | `voicebox-lifecycle.ts` -> `speech-backend.ts` | `git mv` (tracked rename) |
| Internal constant | `VOICEBOX_DEFAULT_PORT` -> `SPEECH_DEFAULT_PORT` | edit + update usages |
| Log tag | `[VOICEBOX-LIFECYCLE]` -> `[SPEECH-BACKEND]` | edit |
| Doc comment header | "Voicebox is a SEPARATE Python process" -> "speech backend is..." | edit |
| Committed .env.example block | remove active `VOICEBOX_*` lines, keep a zero-config note | edit (real committed change) |

## What to KEEP as-is (external config contract)
| Layer | Why |
|---|---|
| `process.env.VOICEBOX_*` reads | user's `.env` keys; renaming breaks their config |
| `TTS_PROVIDER === 'voicebox'` literal | it's the provider value in `.env`, a config key |
| Filesystem path `C:/one/voicebox/.venv/...` | real path to the venv; not a "name" |
| `src/speech/` vendored package | already renamed off `voicebox` before this step |

Pattern: **rename internal identifiers, keep env-var reads as aliases.** Expose a
clean internal name; read the brand env var. This is the split the user accepted
("rename VOICEBOX_* constants to SPEECH_* but keep env reads so .env works").

## Scope control (avoid over-blasting)
- "source code only" => rename files/identifiers/log tags, leave docs. Stop.
- "also docs" => scrub .env.example, ENVIRONMENT.md, ADRs, FILE_STRUCTURE.md,
  cli-reference.md. Safe to edit (no config contract).
- "aggressive / rename env reads too" => only if user explicitly wants to touch
  the config contract; then ALSO update .env + .env.example keys.

## Stale-doc trap
A pre-existing `docs/VOICEBOX_SETUP.md` describing the OLD clone-based
(`git clone jamiepine/voicebox`, `setup-voicebox-clone.mjs`) flow is now
MISLEADING once you vendored `src/speech/` as zero-config. Flag for
deletion/rewrite; do not leave it contradicting the new design.

## Verify after rename
- `grep -rni voicebox src/ tests/ --include=*.ts` (excluding node_modules,
  src/speech vendored, dist) should show ONLY `process.env.VOICEBOX_*` reads.
- `npm run typecheck` exit 0 (all imports resolved to new name).
- Re-run the integration test -> real asset still generated (e.g. WAV > 1 KB).
- `git status --porcelain | grep speech-backend` shows `RM old -> new`.
