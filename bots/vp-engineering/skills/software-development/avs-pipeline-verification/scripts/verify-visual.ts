/**
 * Reusable VISUAL verification for AVS agentic renders.
 *
 * Scans every output/<job>/*.mp4 (main + _16x9/_1x1/_9x16 variants), checks
 * dimensions against the orientation, extracts a late frame for manual
 * vision_analyze inspection, and reports any broken/zero-byte/mis-dimensioned
 * files. Codec/typecheck/unit-tests CANNOT catch the real defects (orientation
 * ignored, watermark black-box, untranslated multilingual captions) — only
 * looking at the actual frames can. Run this after any combinatorial batch.
 *
 * Usage: npx tsx scripts/verify-visual.ts
 */
import * as fs from 'fs';
import { execFileSync } from 'child_process';
const ffprobe = require('ffprobe-static').path;
const ffmpeg = require('ffmpeg-static').path;

const OUT = 'output';
const FRAME_DIR = 'workspace/tmp/frames';
const EXPECT_DIM: Record<string, string> = { portrait: '720,1280', landscape: '1280,720', square: '1080,1080' };
const VARIANT_DIM: Record<string, string> = { '_16x9': '1280,720', '_1x1': '1080,1080', '_9x16': '720,1280' };

function probeDim(file: string): string {
  return execFileSync(ffprobe, ['-v', 'error', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', file], { encoding: 'utf8' })
    .trim().replace(/\r/g, '').split('\n')[0];
}
function orientOf(dir: string): string {
  return dir.includes('landscape') ? 'landscape' : dir.includes('square') ? 'square' : dir.includes('portrait') ? 'portrait' : '';
}

const dirs = fs.readdirSync(OUT).filter((d) => fs.statSync(`${OUT}/${d}`).isDirectory());
let total = 0, valid = 0, broken = 0, dimBad = 0;
const issues: string[] = [];
fs.mkdirSync(FRAME_DIR, { recursive: true });

for (const d of dirs) {
  const files = fs.readdirSync(`${OUT}/${d}`).filter((x) => x.endsWith('.mp4'));
  // main file dimension check
  const main = files.find((x) => !x.includes('_1x1') && !x.includes('_16x9') && !x.includes('_9x16'));
  for (const f of files) {
    const path = `${OUT}/${d}/${f}`;
    const sz = fs.statSync(path).size;
    total++;
    if (sz < 1000) { broken++; issues.push(`${d}/${f}: too small (${sz}B)`); continue; }
    let dim = '';
    try { dim = probeDim(path); } catch (e: any) { broken++; issues.push(`${d}/${f}: ffprobe err ${e.message.slice(0, 40)}`); continue; }
    // variant expectations
    for (const suf of Object.keys(VARIANT_DIM)) {
      if (f.includes(suf) && dim !== VARIANT_DIM[suf]) { dimBad++; issues.push(`${d}/${f}: ${dim} expected ${VARIANT_DIM[suf]}`); }
    }
    // main file follows job orientation
    if (main === f) {
      const o = orientOf(d);
      if (o && EXPECT_DIM[o] && dim !== EXPECT_DIM[o]) { dimBad++; issues.push(`${d}: main ${dim} expected ${EXPECT_DIM[o]}`); }
    }
    valid++;
  }
  // extract one late frame for visual spot-check (skip the scale filter; it can
  // crash on some frames with status 4294967274 — extract raw instead)
  if (main) {
    const out = `${FRAME_DIR}/${d.replace(/[^a-zA-Z0-9]/g, '_')}_late.png`;
    try { execFileSync(ffmpeg, ['-y', '-ss', '2.0', '-i', `${OUT}/${d}/${main}`, '-frames:v', '1', out], { stdio: 'ignore' }); } catch { /* optional */ }
  }
}

console.log(`outputs: ${total} | valid: ${valid} | broken: ${broken} | dim-mismatch: ${dimBad}`);
if (issues.length) console.log('ISSUES:\n' + issues.join('\n')); else console.log('NO ISSUES — all dimensions correct');
console.log(`frames extracted to ${FRAME_DIR} for vision_analyze spot-check`);
