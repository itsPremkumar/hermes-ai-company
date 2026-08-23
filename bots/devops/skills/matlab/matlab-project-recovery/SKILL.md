---
name: matlab-project-recovery
description: "Recover 'lost' MATLAB projects on Windows when the obvious folder (Documents/MATLAB) is empty — mine MATLAB's editor-state/history XML for the real .m paths, and use a bounded find to avoid whole-drive timeouts. Also covers organizing + documenting + pushing a recovered .m project to GitHub."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [MATLAB, Windows, file-recovery, digital-image-processing, GitHub]
    related_skills: [github-repo-management, git-credential-manager-windows]
---

# MATLAB Project Recovery (Windows)

When the user says "I did MATLAB projects before, check if they're still available" and
`Documents\MATLAB` is **empty**, the files are usually NOT gone — they're in an old Windows
account folder or a non-default save path. Don't brute-force the whole drive (it times out
on this machine). Use MATLAB's own MRU (most-recently-used) metadata instead.

## Trigger / When to use
- User asks to find/check/recover old `.m` MATLAB files.
- `Documents\MATLAB` (current user) is empty but the user insists projects existed.
- You need to locate where MATLAB actually saved things.

## Step 1 — Confirm MATLAB is installed (and which release)
```bash
timeout 30 find "/c/Program Files" -maxdepth 2 -iname '*matlab*' 2>/dev/null
which matlab
```
Path looks like `C:\Program Files\MATLAB\R2023b\bin\matlab.exe`.

## Step 2 — Mine the editor-state XML (the key trick)
MATLAB records every file it ever opened in:
```
C:\Users\<user>\AppData\Roaming\MathWorks\MATLAB\R20xx\MATLAB_Editor_State.xml
```
Each `<File absPath="C:\..." name="foo.m"/>` element is a real past project file.
Extract the distinct folders:
```bash
grep -oE 'absPath="[^"]+"' "$APPDATA/MathWorks/MATLAB/R2023b/MATLAB_Editor_State.xml" \
  | sed -E 's/absPath="//; s/"$//' | sort -u
```
Also useful:
- `History.xml` in the same folder (commands run, with `error=` flags).
- `MATLAB\R20xx\` may show multiple releases (e.g. R2021a + R2023b) — check all.

For THIS user the real projects lived in the **old `admin` account**:
`C:\Users\admin\Documents\MATLAB` (current account is `PREM KUMAR`). The editor-state XML
revealed it; `Documents\MATLAB` under `PREM KUMAR` was empty.

## Step 3 — Bounded find (avoid whole-drive timeout)
A naive `find /c -iname '*.m'` times out (~60s+) on this machine. Prune heavy dirs:
```bash
timeout 200 find /c -type d \( -path '*/Program Files/MATLAB*' \
    -o -name node_modules -o -name '.git' \) -prune -o -iname '*.m' -print 2>/dev/null
```
Or scope to known accounts: `find /c/Users -maxdepth 4 -iname '*.m' -not -path '*/node_modules/*'`.

## Step 4 — Organize, document, push (the deliverable)
Once found, turn the loose `.m` pile into a clean repo:
1. Group by role: `src/pipeline/` (driver scripts), `src/operations/` (reusable
   functions), `src/demos/` (standalone technique showcases).
2. Read each file and write an **accurate** README + a `docs/MODULE_REFERENCE.md` table
   (signature + one-line description per function). Don't guess — the code is the source
   of truth.
3. Add `LICENSE` (MIT for this user), `.gitignore` (`*.asv *.mat` + generated image
   folders), and a `sample_images/.gitkeep`.
4. Commit, create the GitHub repo via the **no-`gh` GCM-token flow** (see
   `github-repo-management` → "No `gh` AND empty `~/.git-credentials`"), push, and verify
   via the recursive-tree API call.

## Verified example (2026-07-14)
Recovered 30 `.m` files (a waste-material image classifier + Canny/Haar/watermark demos)
from `C:\Users\admin\Documents\MATLAB`, reorganized into
`itsPremkumar/digital-image-processing-matlab`, pushed and API-verified.

## Pitfalls
- **Don't trust `Documents\MATLAB` being empty** — it's just the current account's default,
  not proof the projects are gone. The editor-state XML is the real map.
- Some driver scripts hardcode absolute paths (`C:\Users\admin\...` or old
  `/MATLAB Drive/...` from MATLAB Online). Document them; prefer the argument-taking
  `operations/` functions which need no path edits.
- `restoreImages.m`'s `selectiveDeconvolution` was a **stub** (returns image unchanged) in
  the recovered project — note such stubs honestly in the README rather than implying they
  work.
- MATLAB **won't launch** on this laptop for headless `-batch` verification (exit
  `0x00000001`, ~900MB free RAM). So you can't run `checkcode`/execute here — verify the
  push via GitHub API instead, and tell the user to run MATLAB checks on a capable machine.
  (This is a machine-state limitation, not a code defect.)

## References (this skill's `references/` folder)
- `editor-state-xml.md` — exact XML shape + extraction snippets for `MATLAB_Editor_State.xml` / `History.xml`.
- `gcm-token-create-push.md` — the no-`gh`, empty-`~/.git-credentials` recipe to create + push + API-verify a GitHub repo for a recovered project (GCM supplies the token).

See `references/editor-state-xml.md` for the exact XML shape and extraction snippets.
