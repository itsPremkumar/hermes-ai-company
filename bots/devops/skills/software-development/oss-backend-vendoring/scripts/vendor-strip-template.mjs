#!/usr/bin/env node
/**
 * vendor-strip-template.mjs — re-runnable copy + strip + patch + license.
 *
 * Usage: node vendor-strip-template.mjs
 * Edit SRC (upstream clone), ROOT (target), REMOVE (files/dirs), and the
 * patch steps to match the upstream you are vendoring.
 *
 * This template embeds the Voicebox-specific strip as a worked example.
 * It is intentionally explicit so you can see every deletion + patch.
 */
import fs from 'node:fs';
import path from 'node:path';

const SRC = 'C:/one/voicebox/backend';                 // upstream clone (never modified)
const ROOT = path.resolve('src/adapters/real-voice-backend');
const DST = path.join(ROOT, 'backend');

const log = (...a) => console.log('[VENDOR]', ...a);
const warn = (...a) => console.warn('[VENDOR][warn]', ...a);

function rmrf(p) {
  if (!fs.existsSync(p)) return false;
  fs.rmSync(p, { recursive: true, force: true });
  return true;
}
function copyDir(src, dst) {
  fs.mkdirSync(dst, { recursive: true });
  for (const e of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, e.name), d = path.join(dst, e.name);
    if (e.isDirectory()) { if (e.name === '__pycache__') continue; copyDir(s, d); }
    else fs.copyFileSync(s, d);
  }
}
function patchFile(p, find, repl) {
  if (!fs.existsSync(p)) { warn('patch target missing:', p); return; }
  const before = fs.readFileSync(p, 'utf8');
  const after = before.replace(find, repl);
  if (after !== before) { fs.writeFileSync(p, after); log('patched:', path.relative(DST, p)); }
  else warn('no change (verify manually):', path.relative(DST, p));
}

// 1. clean target
if (fs.existsSync(ROOT)) rmrf(ROOT);
fs.mkdirSync(DST, { recursive: true });
// 2. copy whole backend
copyDir(SRC, DST);
// 3. remove unwanted (paid/cloud/bloat)
for (const rel of ['routes/cloud.py','services/cloud.py','backends/hume_backend.py',
  'routes/rocm.py','services/rocm.py','routes/cuda.py','services/cuda.py','tests']) {
  rmrf(path.join(DST, rel)) && log('removed:', rel);
}
// 4. PATCH registration graph (deleting modules breaks boot otherwise)
patchFile(path.join(DST,'routes/__init__.py'),
  /    from \.cuda import router as cuda_router\n.*?from \.rocm import router as rocm_router\n/,
  '');
patchFile(path.join(DST,'routes/__init__.py'),
  /app\.include_router\(cuda_router\)\n.*?app\.include_router\(rocm_router\)\n/,
  '');
// 5. retain LICENSE
if (fs.existsSync(path.join(SRC,'..','LICENSE'))) {
  fs.copyFileSync(path.join(SRC,'..','LICENSE'), path.join(ROOT,'LICENSE'));
  log('retained LICENSE');
}
log('DONE. Verify: cd', ROOT, '&& python _boot.py  (import backend.app)');
