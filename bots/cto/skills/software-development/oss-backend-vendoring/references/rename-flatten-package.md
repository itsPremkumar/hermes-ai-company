# Rename / flatten a vendored Python package — the ref-name trap

When you move a vendored backend from `src/adapters/<name>/backend/` (package `backend`)
into a flattened `src/<name>/` (package `<name>`), the import graph only *partially*
updates by itself. Several references are hardcoded and break **at runtime**, not
import time — so a plain `from backend.app import app` check passes while the server
dies on `python -m <name>.main`.

## Which references to change (package refs only)

| Location | Bad (old) | Good (new) | Why |
|---|---|---|---|
| `main.py` | `uvicorn.run("backend.main:app", ...)` | `uvicorn.run("<name>.main:app", ...)` | uvicorn target string, resolved only when server starts |
| `server.py` (PyInstaller entry) | `from backend import config` / `from backend.main import app` | `from <name> import config` / `from <name>.main import app` | absolute top-level package import |
| `routes/health.py` | `from backend.server import disable_watchdog` | `from ..server import disable_watchdog` | relative import (package renamed) |

## Which references to KEEP (module-name coincidence)

`services/tts.py` is a **file** (the TTS service module). These are NOT package refs —
do NOT rename them:
- `from .services import tts`
- `from ..services import tts, transcribe, llm`
- `from . import tts`

These refer to the file `services/tts.py`, which keeps its name. Only `from tts import ...`
(no leading dot) and `"tts.main:app"` are package refs.

## How to find them safely
```bash
# package refs to rename (top-level `tts` / `backend`, no leading dot before it):
grep -rn -E "tts\.main|from tts import|import tts\b|\"backend\.main\"|from backend\." --include=*.py src/<name>
# then READ each hit — confirm it's a package ref, not the services/tts.py module,
# before patching. Blind replace-all will corrupt the services import.
```

## Symptom of getting it wrong
- Instant `ModuleNotFoundError: No module named 'backend'` on `python -m <name>.main`
  -> a hardcoded `backend.` ref survived (Step 7b background boot catches this; a bare
  import check does NOT).
- A 30s+ hang (server stays up, client times out) -> actually STARTED fine; not a bug.
