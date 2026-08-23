# AVG: caption/format presets, config-override ordering, ffmpeg drawtext escaping, CI action bumps

Session-tested learnings from extending the Automated-Video-Generator (AVG) with
creator templates + finishing a Tier-2..Tier-4 hardening list. All verified with
`npm run typecheck` (0) + `npm run lint` (0) + `npm run test:unit` on the real repo.

## 1. Adding caption-theme + video-format presets (a clean, low-risk feature)
The high-ROI "more templates / better subtitle styling" roadmap item is best shipped
as **typed preset registries + config fields + resolver functions + tests**, NOT by
first rewriting the render path. Pattern that worked in `src/agentic/config.ts`:

- `CAPTION_THEME_PRESETS: Record<string, CaptionTheme>` where `CaptionTheme` =
  `{ fontScale, color(#hex), bg(rgba|null), outline, bold, position('bottom'|'center'|'top') }`.
  Add `resolveCaptionTheme(name?)` (falls back to a `minimal` default) + `listCaptionThemes()`.
- `VIDEO_FORMAT_PRESETS: Record<string, {orientation, aspect}>` for shorts/reels/tiktok
  (9:16), square (1:1), landscape/explainer (16:9), promo. Add `listFormats()`.
- New optional `AgenticConfig` fields: `captionTheme?: string`, `format?: string`.
- Tests assert: format preset applies, unknown name falls back, listers count all presets.

## 2. PITFALL — preset-vs-user-override ORDERING in resolveConfig (real bug found)
A named preset (format/caption/video-type) must be applied as a **baseline in the spread
chain BEFORE the user's explicit overrides**, not in a post-merge `if` block. The first
attempt did:
```
const merged = { ...preset, ...tpl, ...stripUndefined(input) };
if (fmt) { merged.orientation = fmt.orientation; merged.aspect = fmt.aspect; }  // WRONG
```
This clobbers an explicit `orientation:'landscape'` the user passed alongside `format:'shorts'`.
Fix — fold the format preset into the spread chain so `stripUndefined(input)` wins last:
```
const fmt = input.format ? VIDEO_FORMAT_PRESETS[input.format] : {};
const merged = { ...preset, ...tpl, ...fmt, ...stripUndefined(input) };  // user override wins
```
Always add a test: `resolveConfig({format:'shorts', orientation:'landscape'})` must keep landscape.

## 3. PITFALL — ffmpeg drawtext `enable=` escaping is destroyed by the patch tool
The AVG burns captions with `drawtext ... :enable='between(t\,START\,END)'`. In the **TS
source string** this is written `between(t\\,${start}\\,${end})` (two backslashes → one
literal `\` in the runtime string → ffmpeg's required `\,`).

When you `patch`/replace a drawtext line, the tool can DOUBLE the backslashes, turning
`\\,` into `\\\\,` in the file — which emits `\\,` to ffmpeg and breaks the filtergraph.
- After any patch touching a drawtext `enable=`/filter string, RE-READ the exact line and
  confirm it has exactly `\\,` in source (matching the sibling karaoke drawtext line), not `\\\\,`.
- Fix by patching the 4-backslash fragment back to 2 backslashes.
- This is the same class of failure as `deterministic-file-edits` (backslash/regex literals);
  for heavy escaping, prefer a node `.cjs` rewrite script over fuzzy replace.

## 4. Wiring a caption theme into the render path (contained + backward-compatible)
To make the preset actually functional without risking existing renders:
- Add `captionTheme?: string` to `renderAgenticSlideshow` opts; forward it from
  `configToRequest().render`.
- Resolve ONCE before the caption loop: `const theme = resolveCaptionTheme(opts.captionTheme)`.
- Map to drawtext args: hex→ffmpeg color `#RRGGBB`→`0xRRGGBB`; `fontsize = round(30*fontScale)`;
  box only when `theme.bg` set (parse rgba alpha for `boxcolor=black@<alpha>`); y-position from
  `position` (`bottom`→`h-text_h-120`, `center`→`(h-text_h)/2`, `top`→`120`).
- Default (unset theme) must reproduce the historical look so old renders are unchanged.

## 5. CI action-version deprecation cleanup (clears Node-20 / CodeQL-v3 warnings)
Non-blocking annotations ("Node 20 deprecated", "CodeQL v3 deprecated") are cleared by
bumping action refs across ALL workflow files (`.github/workflows/*.yml`), via one sed pass:
- `actions/checkout@v4`→`@v5`, `actions/setup-node@v4`→`@v5`
- `github/codeql-action/<init|autobuild|analyze>@v3`→`@v4`
- `docker/setup-buildx-action@v3`→`@v4`, `docker/login-action@v3`→`@v4`
- drop EOL `node-version` matrix entries (e.g. `[18,20,22]`→`[20,22]`); check `engines.node`.
- `gitleaks/gitleaks-action` has no v4 — leave at v3.
Validate: these are pure `uses:`/`node-version` token swaps → confirm the diff touches only
those lines (`git diff | grep -E 'uses:|node-version'`). No yaml/python may exist on the box
to lint; token-level swaps keep YAML structure intact.

## 6. Voice-clone onboarding = discoverability, not new code
A "dormant" feature was often already built. `scripts/setup-voicebox-clone.mjs` fully
registers a cloned profile from a sample + writes `.env`; it was just not referenced by any
`npm` script. Fix: add `"voicebox:clone": "node scripts/setup-voicebox-clone.mjs"` to
package.json so it is callable as `npm run voicebox:clone <clip> "<transcript>"`. The only
remaining blocker is the USER supplying a real voice clip — state that and stop, don't fake it.

## 7. Honest deferral > fake completion (standing user bar)
When a plan item's premise is false or the fix is high-risk/low-value, mark it CANCELLED with
a reason rather than inventing a change. Real examples this session:
- L5 "504 TODO/FIXME debt" → `grep` found ZERO markers → non-action, claim false.
- L2 reduce `any` in MCP dispatch → the `any`s are legitimately dynamic JSON tool args.
- L4 sub-project drift → nested `free-*`/`asset-creator` are intentional independent tools
  with pinned deps; a workspaces migration is out of scope and risks re-resolving the tree.
- L7 Swagger → optional; adds runtime dep; API already documented.
Report false-plan corrections explicitly (the user independently verifies second-AI reviews).

## 8. Flaky env-dependent test → guard, don't delete
`ollama-bootstrap.test.ts` asserted "throws when Ollama unreachable" but Ollama WAS running
on the box (curl 127.0.0.1:11434 → 200), so it failed. This was NOT a regression (the diff
never touched ollama). Fix = make the test self-skip when the service is actually reachable
(probe with a short `createConnection` timeout), not delete the assertion. Prove non-regression
first: `git diff <before>..<after> --name-only | grep <file>` = empty.
