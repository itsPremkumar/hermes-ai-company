# AVG — CI workflow validation traps (GitHub Actions)

These silently block the ENTIRE workflow (every push shows a 0-second
"failure" run named after the workflow file, and NO jobs ever execute).
They are NOT visible in `gh run list` except as that 0s failure, and they
are NOT caught by `tsc`/`eslint`. The only way to see the real error
is the **browser run page** (Actions → the run → red "Invalid workflow
file" annotation) or the checks API annotation.

## 1. `toLower()` does not exist in GitHub Actions expressions
GitHub Actions has NO `toLower` / `toUpper` function (only `toJSON`,
`fromJSON`, `format`, `hashFiles`, `contains`, `startsWith`, `endsWith`).

BAD (workflow never runs — silent 0s failure):
```yaml
env:
  IMAGE: ghcr.io/${{ toLower(github.repository) }}
```
FIX — lowercase in a shell step instead:
```yaml
- name: Compute lowercase image name
  id: img
  run: echo "image=ghcr.io/$(echo '${{ github.repository }}' | tr '[:upper:]' '[:lower:]')" >> "$GITHUB_OUTPUT"
# then: tags: ${{ steps.img.outputs.image }}:latest
```

## 2. Invalid `uses:` action version → whole workflow rejected
If ANY `uses:` points to a non-existent tag, GitHub's pre-merge validator
rejects the file and executes ZERO jobs. Two real culprits seen in AVG:
- `docker/build-push-action@v6` — latest tag is `v7` (v6 does not exist)
- `gitleaks/gitleaks-action@v2` — latest tag is `v3` (v2 does not exist)

To confirm the latest tag before pinning:
```bash
gh api "repos/<owner>/<action>/tags?per_page=5" --jq '.[].name'
```
Never guess major versions. After fixing, the workflow RUNS (run shows
real job sub-runs like `Lint & Format`, `Unit Tests`, `Docker Build`,
not just the 0s validator entry).

## 3. Cross-platform ffmpeg filter tests (Linux CI vs full local ffmpeg)
Ubuntu's `apt` ffmpeg (or stripped static builds) may list a filter in
`ffmpeg -filters` but FAIL at runtime ("Filter not found") when a
dependency is missing (e.g. `drawtext` needs fontconfig/libfreetype;
`xfade`/`zoompan`/`vignette` need GPL+extra flags).

Checking `ffmpeg -filters | grep drawtext` is NOT enough — it returns
true on CI but the op still throws "Filter not found".

FIX — probe with a real 1-frame smoke render and skip gracefully:
```ts
function ffmpegCanRun(vf: string): boolean {
  try {
    const { execFileSync } = require('child_process');
    const out = path.join(os.tmpdir(), `smoke-${Date.now()}.mp4`);
    execFileSync(ffmpeg, ['-f','lavfi','-i','color=c=blue:s=64x64:d=0.1',
      '-vf', vf, '-frames:v','1','-y', out], { stdio: 'ignore' });
    try { fs.unlinkSync(out); } catch {}
    return true;
  } catch { return false; }
}
// in the test: if (!ffmpegCanRun("drawtext=text='x'")) return; // skip
```
This keeps CI green on minimal ffmpeg while still exercising the real
render on full builds (local, Docker).

## 4. `format:check` glob drift between environments
A `format:check` glob like `prettier --check src/ remotion/ *.json`
can fail in CI (env-specific `*.json` expansion) while passing locally,
failing the Lint & Format job even though source is fine. Scope it to the
source that matters: `prettier --check src/`.
