# Remotion missing-asset render crash — root cause + fix recipe

## Symptom
A `remotion render`/`renderMedia` of a comp whose scene `localPath` points at a
file NOT in `public/` **aborts the entire render** (not just that scene) with:

```
EncodingError: The source image cannot be decoded.
http://localhost:3000/public/THIS_FILE.png  Failed to load resource: 404
```

## Why it happens (the trap)
1. `staticFile(name)` does NOT throw — it returns a URL like
   `/public/THIS_FILE.png`. So any `try/catch` you wrap around `staticFile`
   inside the comp catches nothing.
2. The 404 only surfaces later, when `<Img>`/`<Video>` tries to **decode** the
   response during encoding -> `EncodingError` -> whole composition dies.
3. You cannot fix it *inside* the `.tsx` comp by importing `fs` to pre-check:
   the Remotion webpack bundle **cannot resolve Node's `fs`**
   (`Module not found: Can't resolve 'fs'`). The comp must stay browser-clean.

## Correct fix — Node pipeline layer
Do the check + substitution where `fs` works: the `renderMedia` caller
(orchestrate.ts / render.ts), BEFORE the comp mounts. For every image|video
asset, if the source doesn't exist (or copy/transcode failed), write a branded
placeholder PNG into `public/` and point `localPath` at it.

```ts
const makePlaceholder = async (destPath: string, accent: string) => {
  // async ffmpeg runner — NEVER execFileSync (blocks event loop on small box)
  const code = await runFfmpeg([
    '-f', 'lavfi',
    '-i', `color=c=${accent.replace('#', '0x')}:s=720x1280`,
    '-frames:v', '1', '-y', destPath,
  ]);
  if (code !== 0) {
    // last-resort 1x1 so the frame still decodes
    fs.writeFileSync(destPath, Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQDJ/pLvAAAAAElFTkSuQmCC',
      'base64'));
  }
};

// in the per-asset loop:
let copied = false;
try {
  if (a.kind === 'video' && /\.(mp4|webm|mov|m4v)$/i.test(src) && fs.existsSync(src)) {
    const code = await runFfmpeg([... scale/normalize ...]);
    copied = code === 0;
  } else if (fs.existsSync(src)) {
    fs.copyFileSync(src, dest);
    copied = true;
  }
} catch { copied = false; }
// A10 — missing/broken image|video => branded placeholder, not a hard crash
if (!copied && a.kind !== 'music') {
  await makePlaceholder(dest, opts.brand?.accentColor ?? '#FF6B35');
  copied = fs.existsSync(dest);
}
if (!copied) continue;
```

Music assets: leave silent (acceptable) — do NOT generate a placeholder.

## Regress test (must pass after fix)
Render a comp whose scene `localPath` = `'THIS_FILE_DOES_NOT_EXIST.png'`.
Requirement: render **completes (exit 0)** and shows the placeholder, instead
of throwing `EncodingError`. (If you only test via `npx remotion render` with a
manually-missing asset, note the production path goes through the Node layer
above, which is where the placeholder substitution happens.)

## Related
- `renderStill` black-frame trap: `remotion still` re-copies `public/` and ad-hoc
  placeholders often aren't served -> use `renderMedia` for scene verification.
- Keep the comp free of `fs`/`path` imports (webpack can't bundle them).
