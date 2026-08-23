# Orca ↔ Hermes — Verified Detail (session 2026-07-28)

## What was done
- Installed Orca latest Windows build: `orca-windows-setup.exe` (Nullsoft, 188,581,112 bytes), silent `/S` install.
- Orca path: `C:\Users\PREM KUMAR\AppData\Local\Programs\orca\Orca.exe` (225 MB), Start Menu `Orca.lnk`.
- Confirmed Hermes is ALREADY a first-class agent in Orca's catalog — no manual registration.

## Exact source citations (stablyai/orca @ main, read 2026-07-28)
- Agent UI catalog: `src/renderer/src/lib/agent-catalog.tsx` ~L274
  ```ts
  { id: 'hermes', label: translate('auto.lib.agent.catalog.8a9ba743cc','Hermes'), cmd: 'hermes', faviconDomain: 'nousresearch.com', homepageUrl: 'https://hermes-agent.nousresearch.com/docs/' }
  ```
- Launch/detect config: `src/shared/tui-agent-config.ts` ~L257
  ```ts
  hermes: { detectCmd: 'hermes', launchCmd: 'hermes --tui', expectedProcess: 'hermes', promptInjectionMode: 'hermes-query' }
  ```
- `AgentPromptInjectionMode` union includes `'hermes-query'` (L9) — Hermes delivers prompt via startup-query contract.

## Empirical outputs
- `hermes` resolves on Windows USER PATH:
  `C:\Users\PREM KUMAR\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes` (PE32+ x86-64).
- `hermes --version` → `Hermes Agent v0.19.0 (2026.7.20) · upstream f228e145`.
- `hermes --tui` launches a full-screen TUI (no stdout; a timeout-kill is a valid liveness test).
- Hermes also ships `hermes-acp.exe` (ACP stdio server) and `hermes-agent.exe` in the same Scripts dir.

## Windows PATH gotcha (the real lesson)
- GUI app (Orca) inherits `HKCU\Environment` Path + `HKLM\...\Environment` Path — NOT the git-bash PATH.
- The user's Windows USER Path already contained:
  `C:\Users\PREM KUMAR\AppData\Local\hermes\hermes-agent\venv\Scripts;C:\Users\PREM KUMAR\AppData\Local\hermes\bin`
- `cmd /c "where hermes"` output was masked by a custom cmd prompt banner; redirect to a file (`> C:\tmp.txt`) to read it reliably.

## Orca GUI state observed
- Opened against project `C:\one\Automated-Video-Generator`, branches `main` + several `audit/*`.
- Onboarding completed popup shown; left sidebar lists Projects/Tasks/Automations/Orca Mobile + "Run Grok to refresh" (Grok was detected because it's on PATH — same mechanism Hermes uses).

## Notes / cautions
- Don't edit `resources/app.asar` (packed) — agent wiring is PATH/data-driven.
- `spawn codex ENOENT` at Orca launch = harmless probe for absent Codex binary.
- RAM: Orca is heavy Electron (~711 MB disk, large RAM). Close when not orchestrating.
