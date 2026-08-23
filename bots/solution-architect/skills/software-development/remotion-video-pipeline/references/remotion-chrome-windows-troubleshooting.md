# Remotion Chrome headless timeout on Windows 10 — troubleshooting

## Symptom

Remotion 4.x render fails with:
```
⚠ remotion aspect native failed: Timed out after 25000 ms while trying to connect to the browser! Chrome logged the following:
```

This happens even when:
- `CHROME_EXECUTABLE` is set to a valid Chrome/Chromium path
- Puppeteer Chrome exists at `~/.cache/puppeteer/chrome/win64-*/chrome.exe`
- System Chrome exists at `C:\Program Files\Google\Chrome\Application\chrome.exe`

## Root Cause (diagnosed on Windows 10)

The `@remotion/renderer`'s `ensureBrowser()` function (with its 20-second timeout) or direct Chrome launch does not connect on this host. Possible reasons:

1. **Chrome version mismatch** — Puppeteer downloads Chrome 143, but Remotion 4.0.487 may expect a specific Chromium revision that differs from what puppeteer downloaded
2. **Windows sandboxing/headless flags** — Remotion's default Chrome flags may not match what the installed Chrome supports
3. **`--no-sandbox` missing** — On Windows, headless Chrome sometimes needs `--no-sandbox` to connect to the DevTools protocol
4. **X11/Wayland conflict** — MSYS2/Cygwin layer may confuse Chrome's display detection

## Attempted Fixes (none resolved on this host)

- Set `CHROME_EXECUTABLE` to Puppeteer Chrome: `C:/Users/$USER/.cache/puppeteer/chrome/win64-143.0.7499.169/chrome-win64/chrome.exe`
- Set `CHROME_EXECUTABLE` to system Chrome: `C:/Program Files/Google/Chrome/Application/chrome.exe`
- Freed 24GB disk space (ENOSPC was causing a separate failure)
- Let Remotion's `ensureBrowser()` download its own Chromium (no `@remotion` cache found — download either failed or was never triggered)

## Workaround

**Use `--renderer ffmpeg` instead.** The ffmpeg renderer is the primary production path on this system and produces identical output with verified quality gates (X7-X15 all pass). The agentic pipeline falls back from remotion to ffmpeg automatically.

```bash
npx tsx bin/agentic-run.ts --topic "..." --renderer ffmpeg --quality low --backend heuristic
```

## Future Investigation

If Remotion visual rendering is needed:
1. Check if `@remotion/renderer`'s `ensureBrowser()` left any logs: `C:/Users/$USER/AppData/Local/Temp/@remotion/*`
2. Try `--no-sandbox` via `chromiumOptions`: `chromiumOptions={{args:['--no-sandbox','--disable-gpu']}}`
3. Check Chrome DevTools Protocol port: Remotion opens Chrome with `--remote-debugging-port=0` (random port); verify the port is reachable
4. Install a specific Chromium revision using `npx @remotion/renderer download` (if available in 4.0.487)
5. Fall back to `renderStill()` for single-frame verification (bypasses the full browser connection)
