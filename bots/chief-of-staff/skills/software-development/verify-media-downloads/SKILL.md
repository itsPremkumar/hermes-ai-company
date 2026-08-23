---
name: verify-media-downloads
description: Verify/fix media download sources; prove real defects.
---

# verify-media-downloads

## When to use
- A user reports "downloads not working", "X source is broken", or asks you to verify media sources in a video/asset pipeline.
- You must confirm image/video/music/SFX sources actually fetch and persist real files.
- Before claiming a source works (or fails), produce **empirical proof** — not static reading and not a bare `curl`.

## CORE RULE: don't hand-wave failures as "environmental"
Trace the code path first. Real defects hide behind "it's just throttled":
- no retry on 429/5xx/timeout
- a 30s **total** axios timeout that kills slow-but-alive large files
- missing source failover (chosen source 429s → no fallback to next candidate)
- retry retrying permanent 4xx (404/403) forever
Only call it "throttling" after proving the URL returns HTTP 200 AND the result flips PASS↔FAIL across runs.

## The method: empirical download probe
Write a throwaway `tsx` script that calls the project's REAL fetch/download functions per source, asserts a file landed with `>0` bytes, and prints a PASS/FAIL table. Template: `scripts/verify-download-sources.ts` (copy into the project's `scripts/`; run `npx tsx scripts/verify-download-sources.ts`).

### Harness pitfalls that masquerade as pipeline bugs
1. **tsx does NOT auto-load `.env`.** Import `dotenv` and call `config()` at the top or keyed providers silently skip (logs "No API key set"). Looks like a pipeline bug, is a harness bug.
2. **Return-shape mismatches are harness bugs.** In AVS: `fetchVisualsForScene(q, preferVideo, orientation)` returns a single `MediaAsset | MediaAsset[] | null` (don't call `.length`); `ImageResult`/`VideoResult` carry `.downloadUrl` (not `.url`); `MediaAsset` carries `.url`; `downloadMedia(url, dir, name)` returns a `DownloadResult { path }` object, not a string.
3. **Per-source timeout** via `Promise.race` (60–120s) so a slow free-CC host can't hang the suite. A timeout alone is NOT proof of failure.

## Distinguishing a real defect from transient rate-limiting
- `curl -s -o /dev/null -w "%{http_code}" <url>` (or HEAD) to confirm 200 vs 404/blocked.
- Log actual returned `downloadUrl`s — if 200, the source works.
- Re-run; if it flips PASS↔FAIL, it's throttling, not code.
- A genuine defect is *consistent*: instant throw on first 429, total-timeout killing large files, no failover, retry-on-permanent-4xx.

## The download ladder (AVS)
```
KEYED (if configured): Pexels → Pixabay → Openverse
FREE CC: Wikimedia Commons → Internet Archive → (NASA/Met images) → Flickr/Coverr
LOCAL: input/visuals/ + input/bgm/ + procedural
```
Make every tier equally robust — don't leave the "recommended" keyed path weaker than the free path.

## Common real defects to hunt & fix
1. **No retry + total `timeout` on the streaming downloader.** A 30s `axios timeout` is TOTAL, not a stall guard — a slow 66MB video dies at 30s. Fix: wrap stream in `withRetry` (3× exp backoff, `shouldRetry` on 429/5xx/timeout/network) + a CHUNK-stall timer (resets on every `data` chunk) + HTTP Range resume so a partial `.part` continues.
2. **Missing source failover on free-image path.** If chosen Wikimedia image 429s, fall through to Archive. Mirror the free-VIDEO adapter's `searchAndDownloadFirst` (tries each ranked candidate in order).
3. **Stall window too short** on free-video manager (30s kills slow streams) → raise to 60–90s.
4. **Retry retrying permanent 4xx** (404/403) → add `shouldRetry` skipping `>=400 && <500 && !=429`.

## Verification gate (before you say "fixed")
- `tsc --noEmit` clean (0 errors). In AVS run `npm run typecheck` (exit 0 = clean; ignore the bogus `TS6053` the patch-tool lint prints for every edited TS file).
- Re-run the probe: keyed image + large video PASS; free-image PASS via failover.
- Run the project's existing unit suite. Confirm "failures" are environmental (e.g. `ModuleNotFoundError: No module named 'fastapi'` in a Python venv, `# SKIP host unreachable` network skips), NOT your change. Run suspicious tests in ISOLATION to prove flakiness vs regression.
- Do NOT re-edit files just to satisfy a runtime "changed" flag (AVS re-flags committed files) — clear via `git status --porcelain` + `git diff HEAD`.
- **This fix is committed**: the `downloadMedia` retry+resume+stall + free-image failover hardening shipped in commit `2636edc` (pushed to `origin/main`). Before re-investigating "downloads broken", `git log --oneline | grep 2636edc` / `git show 2636edc` to confirm it's present — don't re-derive a fix that's already landed.

## Harness timeout nuance (critical — don't misread a PASS↔FAIL flip)
The probe wraps EACH source in `Promise.race([p, timeout(120000)])`. A per-source
timeout means ONLY that the download exceeded the test's wall-clock budget — it is
NOT proof the code is broken. The hardened `downloadMedia` retries + resumes, so a
slow-but-alive 31MB video that times out at 120s in one run will often SUCCEED in
another run when the host isn't throttled. To call a source "broken", you must ALSO:
1. `curl -s -o /dev/null -w "%{http_code}" <returned downloadUrl>` → must be 200 (not 404/blocked).
2. Re-run 2–3×; a real defect is *consistent* (instant throw on first 429, total-timeout killing large files every time), throttling *flips* PASS↔FAIL.
Only declare "fixed" when the keyed path (the recommended primary) reliably yields real bytes.

## Support files
- `references/avs-download-bugs.md` — concrete AVS defects + fixes + reproduction recipe.
- `scripts/verify-download-sources.ts` — ready-to-run empirical probe (AVS-shaped; adapt imports).
