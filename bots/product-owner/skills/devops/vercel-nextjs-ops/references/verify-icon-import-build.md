# Verify an icon/component import build-survives (Next.js + icon libs)

## The trap (real case: sproutern-oss, 2026-08-08)
Task: add a **GitHub** social button next to Instagram/LinkedIn in the site footer
(`src/components/shared/footer.tsx`). Natural edit: import `{ Github } from 'lucide-react'`.

First sanity check installed `lucide-react@latest` (1.30.0) and probed:
```
node -e "const l=require('lucide-react'); console.log('Github' in l)"  →  NO
```
That looks like the import is broken — but it was a **false alarm caused by checking the
wrong version**. The repo pins `^0.539.0`. Re-installing the pinned range and re-probing:
```
npm install lucide-react@0.539.0 --no-audit --no-fund
node -e "const l=require('lucide-react'); console.log('Github' in l)"  →  true
# also: Github, GithubIcon, LucideGithub all present
```
**Root cause:** lucide-react ≥1.0 removed ALL brand/logo icons (GitHub, X, Facebook,
LinkedIn, YouTube, …). They exist only in 0.x. Checking `@latest` (1.x) makes a valid
0.x-pinned import look broken.

## The authoritative proof: fresh full clone + repo's own tsc
A grep or single-file parse is not enough. Prove the edit against the real dependency tree:
```bash
rm -rf /tmp/spr-verify && mkdir -p /tmp/spr-verify && cd /tmp/spr-verify
gh repo clone <owner>/<repo> . -- --depth=1
npm install --no-audit --no-fund          # installs EXACT pinned tree from package-lock
npx tsc --noEmit                          # the build's own type gate
```
For sproutern (2514 packages): `npm install` ~1min, `tsc --noEmit` ~20s — finished
**under** the 60s foreground clamp, so background was NOT needed.

### Reading the result correctly
- My two edited files (`footer.tsx`, `enhanced-footer.tsx`) → **zero** tsc errors. Import valid.
- tsc ALSO reported ONE pre-existing, unrelated error:
  `src/app/blog/[slug]/page.tsx(198,5): error TS2345 ...` (a `toIsoDateTime()` arg-type
  mismatch). This file was NOT touched by the task.
- Confirm with `git status --short`: only `yarn.lock` modified (by `npm install` generating it);
  my source files are unchanged from the committed state. So the blog error is latent, not mine.

## If the icon truly doesn't exist at the pinned version
- Use a plain `<a href=...>` wrapping an inline `<svg>` (copy the brand's official SVG path), or
- reference an `/public/*.svg` via `<img>`, or
- pick a non-brand icon from the same lib that you've confirmed exists at the pinned version.
NEVER swap to an icon name you haven't verified is exported at the pinned version.

## Decision rule
1. Probe the import at the **pinned** version (not `latest`). If present → safe to use.
2. If absent at pinned version → use SVG/`<a>` fallback; do not force a 1.x-only name.
3. Final gate: fresh-clone `tsc --noEmit`, and separate pre-existing errors from yours via
   `git status --short`.
