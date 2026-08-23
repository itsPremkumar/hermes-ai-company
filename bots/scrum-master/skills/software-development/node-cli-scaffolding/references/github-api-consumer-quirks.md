# GitHub public-API quirks for repo-audit / stats CLI tools

Verified 2026-07-31 building `gh-repo-health` (zero-dependency Node 18+ CLI using built-in fetch). Applies to any tool that consumes the public GitHub API.

## Rate limits (unauthenticated)
- 60 req/hr per IP — shared across EVERYTHING on that IP. Read the `x-ratelimit-remaining` response header and surface it in output.
- Mitigate: disk cache with TTL (JSON under `~/.cache/<tool>/`, `mkdirSync(recursive)` before write) + a `--no-cache` flag. A stale cache entry can mask the very bug you just fixed — always re-verify with `--no-cache` after code changes.
- 403 on `/repos/{o}/{r}/actions/runs` = Actions DISABLED on that repo (not an error) — score it as "no CI", don't fail.
- 404 = repo/readme not found; 429 = rate limited.

## README endpoint (GET /repos/{o}/{r}/readme)
- Returns `{ content: <base64>, encoding: "base64", ... }`.
- `content` is **line-wrapped at 60 chars** (`\n` inside the base64) — strip `/\s+/g` BEFORE decoding or your round-trip validation fails on real repos.
- Node `Buffer.from(x, 'base64')` is **lenient**: garbage decodes to mojibake without throwing. Validate by re-encoding and comparing (`replace(/=+$/, '')` both sides); mismatch → return null.

## Redirects & renames
- Renamed repos (facebook/react → react/react): API returns 301, fetch() follows, `full_name` reflects the NEW owner. Display `meta.full_name`, not the input string.
- Old usernames after account rename → API 404 (web redirects still work; only the API loses the name).

## User-Agent header is mandatory
- GitHub API rejects requests without a User-Agent (403). Always set one, e.g. `User-Agent: <tool>/<version>`.
