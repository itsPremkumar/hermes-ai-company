# GitHub Release Audit — copy-paste recipe

## One-shot parallel fetch (replace <owner>/<repo>)
```bash
OWNER=diegosouzapw; REPO=OmniRoute
echo "=== REPO + LATEST RELEASE ===" && \
  curl -s https://api.github.com/repos/$OWNER/$REPO && \
  echo "=== LATEST RELEASE ===" && \
  curl -s https://api.github.com/repos/$OWNER/$REPO/releases/latest
```

## Decode package.json version (base64 in `content`)
```bash
curl -s "https://api.github.com/repos/$OWNER/$REPO/contents/package.json?ref=main" \
  | python -c "import sys,json,base64; d=json.load(sys.stdin); print(base64.b64decode(d['content']).decode())" \
  | grep '"version"'
```

## Tag ↔ release + main drift
```bash
curl -s "https://api.github.com/repos/$OWNER/$REPO/tags" | python -c "import sys,json;[print(t['name']) for t in json.load(sys.stdin)]"
curl -s "https://api.github.com/repos/$OWNER/$REPO/compare/v3.8.48...main" \
  | python -c "import sys,json;d=json.load(sys.stdin);print('status',d.get('status'),'ahead',d.get('ahead_by'),'behind',d.get('behind_by'))"
```

## Worked example — OmniRoute (2026-07-15)
- Latest tag: `v3.8.48`. Latest release: `v3.8.48`, published 2026-07-13, `draft=false`, `prerelease=false`, `target_commitish=main`.
- package.json (main): `"version": "3.8.48"` → matches tag + release. OK
- `compare/v3.8.48...main` → `ahead_by: 4, behind_by: 0`. EXPECTED. main had 4 post-release CI commits (e.g. "fix(ci): drop Merged batch settings"). Not a defect.
- Assets: full AppImage/dmg/installer matrix + all 4 electron-updater `latest*.yml` manifests present → auto-update wired.
- Verdict: latest version perfectly set and configured.

## Notes
- Unauth GitHub API: ~60 req/hr per IP. Add `Authorization: Bearer <token>` to raise to 5000/hr.
- `releases/latest` 404s if newest is a prerelease/draft — fall back to `/releases?per_page=5`.
