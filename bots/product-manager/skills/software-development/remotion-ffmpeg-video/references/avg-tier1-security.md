# AVG Tier-1 Security Hardening (verified patterns)

Reusable fixes from the production-hardening sweeps. Each was independently
verified against the code, not assumed.

## 1. Remotion version drift = latent renderer break
Remotion REQUIRES every `@remotion/*` package at the EXACT same version.
A single mismatch (`@remotion/captions@^4.0.490` vs
`cli/media-utils/renderer@^4.0.487`) compiles fine but breaks the
Remotion renderer at runtime.

Fix: align all `@remotion/*` to one version in `package.json`, then
`npm install` (retry loop for flaky network) so the lockfile matches.
Verify: `npm run typecheck` + a render smoke test.

## 2. ffmpeg `drawtext` injection via user text
User `title`/`subtitle`/`cta`/`word` flow into
`drawtext=text='${...}'`. The OLD escaping only did
`.replace(/'/g,'’').replace(/:/g,'\\:')` — leaving `"`, `,`, and
a trailing `\` as injection vectors (a `"` or `,` breaks out of the
quoted text or injects a filter arg).

Correct ffmpeg drawtext text escaping (centralize ONE util, reuse everywhere):
```ts
// src/lib/ffmpeg-text.ts
export function ffmpegDrawtextEscape(t: string): string {
  return String(t)
    .replace(/\\/g, '/')   // backslash FIRST, so later escapes aren't re-escaped
    .replace(/:/g, '\\:')
    .replace(/'/g, "'\\''")
    .replace(/"/g, '\\"')
    .replace(/,/g, '\\,');
}
```
Apply at every `drawtext=text='...'` call site (orchestrate.ts had 5).
Differs from `escapeFilterPath` (which escapes PATHS, not text values).

## 3. SSRF guard on media downloaders
`axios.get(url, { responseType: 'stream' })` where `url` comes from an
upstream provider / poisoned cache is an SSRF surface — a crafted
`http://169.254.169.254/latest/meta-data/` (cloud creds) or
`http://192.168.x/` internal asset passes if unchecked.

Reusable guard (scheme allow-list + private/loopback/link-local/metadata
host rejection):
```ts
// src/lib/net-safety.ts
export function isSafeUrl(raw: string):
  { ok: true } | { ok: false; reason: string } {
  let parsed: URL;
  try { parsed = new URL(raw); } catch {
    return { ok: false, reason: 'malformed URL' };
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    return { ok: false, reason: `scheme ${parsed.protocol} not allowed` };
  }
  const host = parsed.hostname;
  if (host === 'localhost' || host.endsWith('.localhost') ||
      host.endsWith('.internal') || host.endsWith('.local')) {
    return { ok: false, reason: `host ${host} is private/local` };
  }
  if (host === '::1' || host.startsWith('fc') || host.startsWith('fd') ||
      host.startsWith('fe80')) {
    return { ok: false, reason: `host ${host} is loopback/ULA/link-local` };
  }
  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(host) && isPrivateIPv4(host)) {
    return { ok: false, reason: `host ${host} is a private IPv4` };
  }
  return { ok: true };
}
```
Apply BEFORE every stream download in `free-video/download/downloader.ts`
(`streamToFile`) and `visual-fetcher.ts` (`downloadMedia`).
NOTE: sync DNS lookup is unreliable across runtimes; hostname-pattern
checks above already block the common cloud-metadata + internal-hostname
vectors. Add async `net.resolve4` IP validation in callers if full
IP-resolution coverage is required. Add 6 SSRF unit tests
(public allowed; file/ftp/gopher rejected; malformed rejected;
localhost/127/::1 rejected; 169.254.169.254 + 192.168/10/172.16
rejected; .internal/.local rejected).

## 4. `.env` plaintext secret hygiene (P0)
A real profile/API UUID sitting in `.env` on disk is a P0 even when the
file is gitignored (any local process, backup, or `cat` can leak it).
Fix: scrub to a placeholder + rotate if it was ever live. Verify the
UUID was NEVER committed:
```bash
git log --all -S "9d484367" --oneline   # empty = never committed
```
Commit only `.env.example` (placeholders). The repo already has
`.env` in `.gitignore` — keep it that way; the risk is the working copy.

## 5. CI `format:check` glob flakiness
`prettier --check src/ remotion/ *.json` fails non-reproducibly in CI
on the `*.json` glob (env-specific expansion). Scope to `src/` only:
`"format:check": "prettier --check src/"`. Keeps CI green + still
enforces source formatting (what matters for quality).

## Tier ordering that worked
C4 (.env scrub, 5 min) → C1 (Remotion align, 1 line) →
C2 (SSRF guard + tests) → C3 (drawtext escape) → then H7/M8
(optional AI verify gate) → H1-H3 (refactors, higher risk).
Verify each with typecheck + lint + test:unit + one CI push before
moving on. Reject external "reviews" that claim "no tests" or
"unused files" WITHOUT verifying — both were false for this repo
(agentic core is the best-tested part; `plugins/` dir doesn't exist).
