# License-clean Remotion template integration (this project)

User mandate: zero license issues, can be used commercially, "use only the main
code in our project, don't use unwanted pieces." Verified method used in-session.

## Step-by-step
1. Fetch each candidate repo's LICENSE + package.json `license` field DIRECTLY
   from GitHub raw (don't trust third-party "stars" tables):
   - `https://raw.githubusercontent.com/OWNER/REPO/main/LICENSE` (retry `master`)
   - `https://raw.githubusercontent.com/OWNER/REPO/main/package.json` → grep `"license"`
   - If neither, hit `https://api.github.com/repos/OWNER/REPO/license` → `spdx_id`.
2. KEEP only repos whose LICENSE is **MIT** (or clearly permissive). EXCLUDE any
   with no LICENSE / UNLICENSED / `private:true`.
3. Clone keepers into `remotion/_study/` (depth-1). Add `remotion/_study/` to
   BOTH `.gitignore` AND tsconfig `exclude` (study clones have broken `React` UMD
   imports that break `tsc`).
4. STUDY only. RE-IMPLEMENT as our own components using installed `@remotion/*`.
   Never `import` from `remotion/_study/` in main code. Grep to confirm.

## Findings (verified this session)
- ❌ **Official `remotion-dev/*` templates** (template-tiktok, template-audiogram,
  template-code-hike, template-three, template-music-visualization,
  template-github-unwrapped, template-trailer, template-prompt-to-video, etc.):
  all `private:true` + `"license":"UNLICENSED"`. NOT open-source. DO NOT CLONE/COPY.
- ✅ **MIT (safe to study+reimplement, commercial-OK):**
  - `lifeprompt-team/remotion-scenes` — 201 scenes (Text/Shape/Transition/Data)
  - `degueba/onda` — 70 components + 18 transitions
  - `ahgsql/remotion-subtitles` — 17 caption styles (neon/glow/fire/glitch/...)
  - `ahgsql/remotion-animation` — 80+ animate.css effects
  - `stefanwittwer/remotion-animated` — declarative `<Animated>` chaining
- ⚠️ **UNVERIFIED/unlicensed — excluded:** `av/remotion-bits`,
  `marcusstenbeck/remotion-audio-visualizers`, `pskd73/remotion-animate-text`,
  `reactvideoeditor/remotion-templates`, `locomotion-pro/locomotion` (no LICENSE
  found at root; treat as unsafe until proven MIT).

## Remotion CORE license (node_modules/remotion/LICENSE.md)
- FREE for: individual, for-profit ≤3 employees, non-profit, evaluation.
  Commercial video creation is fine.
- FORBIDDEN: sell/rent/license/relicense a Remotion derivative.
- Watch: if this becomes a >3-employee company product, a Company License is
  required. User is a solo fresher → Free applies now.
