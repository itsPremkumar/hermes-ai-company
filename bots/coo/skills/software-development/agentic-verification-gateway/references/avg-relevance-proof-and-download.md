# Proving the FreeImageAdapter relevance gate + surviving throttled downloads

Context: AVG's `src/lib/free-image/adapter.ts` carries the "lion bug" fix (commit
`4e02900`). Two independent guards, both must be proven when a user says "download N
real X images and prove none are off-topic":

1. **Provider domain-gate** (`shouldQuery`): Wikimedia + Internet Archive are ALWAYS
   queried; NASA (space) and MetMuseum (art) are only queried when the keyword matches
   space/astronomy or art/museum regexes. So for a generic query like `"lion"`, NASA and
   MetMuseum are **never called** — no "Lion nebula" / "sea lion" art can leak in.
2. **Relevance filter** (`isOnTopic`): drops off-topic compounds that still contain the
   query token — for `lion`: `stone lion | sea lion | lion king | lioness | lion's |
   mountain lion | city lion`. Whole-word `\blion\b` required; generic topics (nature,
   city, background, texture, abstract) bypass the filter.

## The two-layer proof (do BOTH)

**Metadata-level proof (primary, network-independent).** Call
`adapter.searchAll('lion', { count: 20 })`, flatten every returned title, and assert:
- ZERO titles match the off-topic compound regex.
- The provider source list contains NO `nasa` / `metmuseum` entry.
- Count of `\blion\b` on-topic titles == total returned.

This proof holds even if EVERY download fails (rate-limit/403), because it inspects the
adapter's output, not the bytes. Print it always — it's the actual proof the fix works.

**Download-level proof (secondary, confirms real bytes).** Download each distinct
`downloadUrl`, then validate with the `file` utility (git-bash has `/usr/bin/file`; there
is NO `ffprobe` on this box for images). Accept only when `file -b` reports
`JPEG|PNG image|image data`. Record filename + source + title + real-lion flag per file.

## Download resilience (Wikimedia throttles hard)

`upload.wikimedia.org` rate-limits per-IP: the first ~2 rapid requests return 200, then a
burst of **429** (and sometimes **403** if you use an unusual User-Agent). Observed live:
a 9-result set gave 2×200 then 7×429 within one run.

Techniques that worked:
- **User-Agent matters.** `Mozilla/5.0 (compatible; AVG/1.0)` got 200/429 (recoverable).
  A "polite" custom UA (`AutomatedVideoGenerator/1.0 (https://...; contact: ...)` ) got a
  hard **403** on every request. Use the simple Mozilla-compatible UA for Wikimedia.
- **axios `arraybuffer` + `Buffer.from(res.data)`** to write; check `statSync(size) > 1000`.
- **Backoff + retry** on 429/403: `2000 * 2**attempt` ms, ~3 attempts.
- **Throttle** ~1s between requests and an initial cooldown; still, the per-IP window may
  not clear within a run budget. Accept a partial download count (e.g. 2–7/10) and lean on
  the metadata proof for the "none are off-topic" claim.
- **Resume-aware, non-destructive filenames.** Key each output file by a stable hash of the
  download URL: `lion_<md5(url)[:8]>_<title-slug>.jpg`. Re-runs then SKIP files already on
  disk (verify they're valid images) and only fill gaps — so repeated runs accumulate toward
  N across successive rate-limit windows instead of overwriting/clobbering.
- **Shuffle candidates** each run so successive runs attack a different subset first.

## Archive.org download quirks
- Search works reliably: `https://archive.org/advancedsearch.php?q=lion+AND+mediatype%3Aimage&...&output=json`.
- Download URLs (`https://archive.org/download/<id>/<file>`) **302-redirect** to a node host —
  you MUST follow redirects (`curl -L` / axios `maxRedirects`). Some items return **401**
  (access-restricted) — skip and move to the next candidate rather than treating it as a bug.

## Multi-subagent collision hazard (cost real iterations this session)
When parallel subagents (`delegate_task`) run in the SAME repo:
- A sibling **overwrote a shared script** (`bin/fetch-lion-proof.ts`) with a different
  (video+image e2e) version between my read and write — my content kept "reverting". The
  `patch`/`write_file` results even carried a `modified by sibling subagent` warning.
- A sibling's run **wiped the shared output dir** (`lion-proof/`), deleting already-downloaded
  images. My own `rm -rf lion-proof` cleanup ALSO destroyed 7 good files earlier — never
  `rm -rf` a shared/accumulating output dir.
- **Mitigations:** (1) give your script a UNIQUE name (`bin/lion-proof-fetch.ts`) so it isn't
  clobbered; (2) write to an ISOLATED output dir (`lion-proof-images/`) that no sibling touches;
  (3) treat on-disk state as ground truth via `find` after each run, not the in-memory counter;
  (4) never destructively clean a dir that other agents or prior runs contribute to.

## Tooling note (reconfirms agentic-pipeline-ops)
`search_files` intermittently threw `rg: ... The system cannot find the path specified.
(os error 3)` and a regex parse error on `sleep(` this session, on a path that existed.
Fall back to `terminal` `grep`/`wc`/`head` and `read_file` for ground truth.
