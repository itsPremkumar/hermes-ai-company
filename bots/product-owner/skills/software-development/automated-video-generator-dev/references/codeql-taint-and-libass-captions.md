# CodeQL taint-at-sink fixes + libass Indic-caption rendering

## CodeQL: sanitizers must be AT THE SINK
CodeQL's `js/log-injection`, `js/path-injection`, etc. queries do **NOT** trust a
custom wrapper function (e.g. a `safeLog()` helper that strips control chars).
The recognized sanitizer pattern must appear **inline at the sink**:
- log-injection: `console.error(('...' + x).replace(/[\x00-\x1F\x7F]/g, ' '))`
- path-injection: `const r = path.resolve(root, file); if (r !== root && !r.startsWith(root + path.sep)) return false;`
- request-forgery / http-to-file-access: validate URLs with the existing
  `isSafeUrl()` in `src/lib/net-safety.ts` (http/https only, blocks
  private/loopback/cloud-metadata hosts) BEFORE `axios.get`. Don't skip it.
- file-system-race: `openSync` the fd first, then `fstatSync(fd)` — never
  `statSync` then `openSync`, and never `existsSync` then `writeFileSync`.
- polynomial-redos: replace `.*?` with `[^\]]*` inside `[Tag: ...]` regexes
  (no nested quantifiers).
- loop-bound-injection: cap the input length before a loop driven by
  external input (e.g. `hashText` slices to 4096 chars).

### ESLint conflict (real, will fail CI)
ESLint's `no-control-regex` (enabled in this repo) **flags control-character
regex literals** like `/[\x00-\x1F\x7F]/g`. So the CodeQL-approved log
sanitizer trips the lint gate. Resolution (pick one):
- Add `/* eslint-disable no-control-regex -- intentional: strip control chars from logged ffmpeg args (log-injection defense) */`
  at the top of the file (used in render.ts), OR
- Build the regex via `new RegExp('[\\u0000-\\u001f\\u007f]', 'g')` — `no-control-regex`
  only inspects regex *literals*, not `new RegExp()` string args.

A custom `safeLog()` wrapper that does `.split(cr).join('')` also fails BOTH
CodeQL (not a recognized sink sanitizer) AND is verbose — don't use it.

## libass for Indic / Arabic captions (drawtext cannot shape them)
ffmpeg's `drawtext` uses libfreetype, which cannot shape complex scripts
(Tamil/Devanagari/Arabic/Myanmar). Even with a font that has the correct
glyphs (verified via fontTools), `drawtext` emits empty boxes (tofu). ffmpeg-static
HAS `--enable-libharfbuzz` but drawtext still can't drive it for these scripts.
The fix: render complex-script captions with **libass** (the `subtitles`
filter), which bundles HarfBuzz and shapes correctly.

Implementation pattern (see `src/agentic/operations/compose.ts`
`buildLibassCaptionFilter` + `needsComplexScriptShaping`, and the render.ts-local
`libassCaption`):
1. `needsComplexScriptShaping(text)` → true for Tamil/Devanagari/Arabic (BMP
   ranges). Latin + CJK need NO shaping → keep them on the lighter `drawtext`
   path (CJK is not complex-shaped).
2. For complex text, write a timed `.ass` file (PlayResX/Y 1280x720, a `Cap`
   style, a `Dialogue` line with `Start`/`End` timestamps) into a per-job
   `caps/` dir (e.g. `path.resolve(AGENTIC_OUTPUT_DIR, jobId, 'caps')`).
3. Return `subtitles='<ass>':fontsdir='<bundled-fonts-dir>':force_style='...'`.
   `fontsdir` must point at `assets/fonts` so headless Linux boxes use the
   bundled Noto fonts (NOT system fontconfig/DirectWrite — on Windows libass
   would otherwise grab `Nirmala UI` via DirectWrite, which is absent headless).
4. Font filename for `force_style` is the basename without `.ttf`
   (`path.basename(fontFile, '.ttf')`).

### CRITICAL pitfall — surrogate-pair range in the shaping regex
`needsComplexScriptShaping` originally included a Myanmar/Burmese range written
as a surrogate pair (astral range). This triggers BOTH
ESLint `no-misleading-character-class` AND a TS "Unterminated regular expression
literal" parse error (render.ts ~line 437). **Fix:** drop astral/surrogate-pair
ranges from the character class, OR add the `u` flag to the regex. Keep only BMP
ranges: Tamil `[\u0B80-\u0BFF]`, Devanagari `[\u0900-\u097F]`, Arabic
`[\u0600-\u06FF]`, Myanmar `[\u1000-\u109F]`, Khmer `[\u1780-\u17E9]`.

Verified: libass rendered Tamil ("நீர் அருந்துவது நல்லது") correctly via the
`subtitles` filter with `fontsdir` pointed at the bundled Noto Tamil font.
