# Wiring the GitHub MCP server into Hermes (repo-scoped agent powers)

Pattern from the Automated-Video-Generator session: the user granted full GitHub
permission on a public OSS repo so the agentic swarm could use Issues / PRs /
Releases / Actions via the official GitHub MCP server instead of just committing
to `main`.

## Why
- Makes swarm output auditable: subagents push branches -> open PRs -> CI auto-checks
  -> agent merges only green PRs. Issues mirror the todo list publicly.
- No token in any file: the MCP server reads credentials from the `gh` CLI session
  (token lives in the OS keyring), never from a written secret.

## Auth (USER does this — agent must NOT type the token)
1. Install `gh` if absent. On this Windows box `winget` was unavailable in the MSYS
   shell; `npm i -g gh` worked (`gh 2.8.9`). Official zip is also fine.
2. User runs `gh auth login` INTERACTIVELY (browser device-code). Scopes: `repo` +
   `workflow` (for Actions). Agent cannot do this step — it needs the user's identity.
3. Confirm: `gh auth status` -> "Logged in to github.com as <user>".

## Register the MCP server (agent does this AFTER auth confirmed)
Hermes `config.yaml` already has an `mcp_servers:` block. Add:
```yaml
mcp_servers:
  github:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GH_TOKEN}"   # gh provides this from keyring
```
Then VERIFY per this skill's handshake steps (tools/list, a live tools/call such as
get_repository) — must return real data, not an auth error.

## Guardrails (non-negotiable)
- Token is a SECRET: never echoed, never written to a repo file, never committed.
  Prefer the `gh`-backed path so the token never touches a process-env we construct.
- Only act on repos the user explicitly granted. Never other accounts.
- Legal lines hold regardless of GitHub perms: no famous-person voice cloning,
  free-stack only.
- GPU work (Voicebox clone/render) stays LOCAL — GitHub Actions runners have no GPU,
  so `ci.yml` must exclude GPU/ffmpeg-heavy render tests.

## Gotcha
- If the user hasn't completed `gh auth login` yet, the MCP server won't connect.
  Don't guess at tokens or edit config prematurely — wait for the user's "done".
- `gh` via `npm i -g gh` may need a fresh terminal session to be on PATH; verify
  with `gh --version` before proceeding.
