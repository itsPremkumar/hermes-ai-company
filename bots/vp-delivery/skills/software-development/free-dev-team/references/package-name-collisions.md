# Package name collisions & environment-dependent bug verification

Two recurring failure modes when assembling a free dev/agent stack. Both bit a real
session (2026-07-18) and cost time. Capture so they never bite again.

## 1. PyPI name collision

`pip install <familiar-name>` frequently installs a DIFFERENT, unrelated package that
happens to share the name. The familiar name usually refers to a GitHub project, not
the PyPI distribution.

Concrete case:
- User wanted "Paperclip" — the autonomous agent-company app `paperclipai/paperclip`
  (74.1k★, Docker-deployed, `docker compose` up).
- `pip install paperclip` → installed `paperclip 2.7.4`, a **Django file-attachment
  library** (django-embed-video, easy_thumbnails). Completely unrelated.
- Fix: uninstalled the wrong one; the real app is cloned + run via Docker, NOT pip.

Rule before any `pip install X` for a tool you "know":
1. Check the PyPI package description + owner against the GitHub project you mean.
2. If the real project is a Docker/monorepo app (Paperclip, many agent stacks), the
   install path is `git clone` + `docker compose`, never `pip install`.
3. When in doubt, verify on GitHub first (browser_navigate the repo) before pip.

## 2. Environment-state-dependent bugs — verify the FIX, not a forced crash

Hermes snap-sessions re-export `PYTHONPATH`/env vars non-deterministically between
turns. A crash seen in one turn (e.g. OpenHands dying on a Hermes-venv `pydantic`
via contaminated `PYTHONPATH`) may NOT reproduce in a later turn where the env state
differs. Consequences for honest verification:

- Do NOT claim "I reproduced the crash 100%" if you only saw it once and can't
  reproduce on demand in the current session. That's a fabricated claim.
- DO prove the fix is deterministic + harmless:
  - `env -u PYTHONPATH openhands.exe --version` → always prints the SDK banner, never
    a Traceback, regardless of contamination. That is the real evidence.
  - State plainly: "bug was environment-state-dependent; wrapper neutralizes it in all
    cases; I could not force a deterministic raw repro in this session."
- When writing verification scripts, test the FIX path (always-clean launch) and, if
  you can, a contamination path — but don't mark "FAIL" on a non-reproducible raw crash.
  Report it as INCONCLUSIVE with the honest reason.

## 3. Skill path reality

- gstack lives at `~/.hermes/skills/gstack` (NOT `$APPDATA/hermes/skills`). The
  `$APPDATA` path is empty on this host. Check the real path before declaring a skill
  missing — a wrong path wastes a turn and produces a false "missing" verdict.
