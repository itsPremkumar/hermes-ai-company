---
name: agent-ade-integration
description: Integrate Hermes with Orca and install Orca on Windows.
---

# Agent ADE Integration (Hermes ↔ Orca and friends)

**Trigger:** User says "make Hermes work in Orca", "install Orca", "wire Hermes into my agent IDE", or wants to run a CLI coding agent (Hermes / OpenHands / OpenCode) inside a third-party orchestrator GUI.

## The one rule that bites everyone
**GUI apps (Orca, Cursor, VS Code) inherit the WINDOWS REGISTRY PATH — NOT the bash / git-bash PATH you use in the terminal tool.**

- Windows PATH = `HKCU\Environment` (User) + `HKLM\...\Environment` (System), read at process launch.
- `which hermes` succeeding in bash does NOT prove Orca can find it.
- Verify with `REG QUERY "HKCU\Environment" /v Path` and confirm the agent's `Scripts`/bin dir is present. Or `cmd /c "where hermes > C:\tmp.txt 2>&1"` then read the file (a custom cmd prompt banner hides stdout, so always redirect to a file).
- If the agent dir is missing from the registry PATH, add it there (System Properties GUI or `setx`), not just `export PATH=` in bash. The dir must contain the bare executable name Orca's `detectCmd` expects.

## How Orca detects agents (verified against stablyai/orca main)
- Agent UI list: `src/renderer/src/lib/agent-catalog.tsx`. Launch/detect config: `src/shared/tui-agent-config.ts`.
- Each agent: `detectCmd` (binary Orca looks for on PATH), `launchCmd` (started inside Orca's terminal pane), `promptInjectionMode`.
- **Hermes is a FIRST-CLASS, built-in agent — no plugin or config file needed.** Verified:
  - `src/renderer/src/lib/agent-catalog.tsx` ~L274: `{ id: 'hermes', label: 'Hermes', cmd: 'hermes', faviconDomain: 'nousresearch.com' }`
  - `src/shared/tui-agent-config.ts` ~L257: `hermes: { detectCmd: 'hermes', launchCmd: 'hermes --tui', expectedProcess: 'hermes', promptInjectionMode: 'hermes-query' }`
- Consequence: if `hermes` resolves on the Windows PATH, Orca auto-offers it in the agent picker (`+` tab → agent list). No manual registration.
- Other agents (OpenHands/OpenCode/Qwen Code) integrate identically — just be on the Windows PATH with the expected binary name.

## Installing Orca on Windows (verified 2026-07-28)
1. Download latest (Nullsoft installer, ~180 MB):
   `curl -fL -o orca-windows-setup.exe "https://github.com/stablyai/orca/releases/latest/download/orca-windows-setup.exe"`
2. Silent install (no prompts): `orca-windows-setup.exe /S`
   - Install dir: `C:\Users\<user>\AppData\Local\Programs\orca` (binary `Orca.exe`)
   - Start Menu: `AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Orca.lnk`
3. Verify: list install dir for `Orca.exe`; launch it (it boots a GUI — there is no `--version` flag, passing one actually starts the app). Confirm `Orca.lnk` exists.

## Verification checklist (do these, don't assume)
- [ ] `hermes` on Windows USER PATH (`REG QUERY HKCU\Environment /v Path`)
- [ ] `hermes --tui` launches cleanly (full-screen TUI; no stdout — a timeout-kill is a valid liveness test)
- [ ] In Orca, click `+` tab → Hermes appears in the agent picker

## Pitfalls
- **`hermes --version` vs `hermes --tui`**: Orca launches `hermes --tui` (full-screen agent UI it hosts). Bare `hermes` opens the classic REPL. Don't confuse them.
- **RAM**: Orca is a heavy Electron app (~711 MB on disk, large resident RAM). On RAM-constrained machines, don't leave it idle — close when not orchestrating. This matters for the "keep only Hermes + AVS alive" discipline.
- **`spawn codex ENOENT`** at Orca launch is harmless — Orca probing for a Codex binary you don't have. Ignore.
- **Don't patch `app.asar`** (packed). Agent wiring is PATH/data-driven, not file-editing.

## References
- `references/orca-hermes-verified.md` — exact file:line citations, URLs, and empirical command outputs from the verification session.
