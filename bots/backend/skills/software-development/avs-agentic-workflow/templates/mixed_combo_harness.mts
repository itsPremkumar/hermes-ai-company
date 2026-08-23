// Mixed-media combination stress-test harness.
// Generates several different orderings of the FOUR source types
// (downloaded video v0/v1/v2, downloaded image i0/i2, Remotion r0/r1/r2,
// website screenshot s0/s1/s2), composes each, and ffprobe-checks every segment.
// Reusable: change ROUND (argv[2]) to vary the seed (different orderings each run).
//
// Run:  export CHROME_EXECUTABLE="/c/Program Files/Google/Chrome/Application/chrome.exe"
//        node --import tsx templates/mixed_combo_harness.mts R3
//
// Prereqs: input/visuals must contain v0..v2.mp4, i0.jpg, i2.jpg,
//          batch_remotion_0_s0.mp4, batch_remotion_1_s0.mp4, batch_remotion_2_s0.mp4,
//          s0.png, s1.png, s2.png (produced by the acquisition steps in
//          references/mixed-media-verification.md).

import * as fs from 'fs';
import * as path from 'path';
import { spawn } from 'child_process';

const ROUND = process.argv[2] ?? 'R?';
const log = (m: string) => fs.appendFileSync('workspace/_harness.log', m + '\n');
fs.writeFileSync('workspace/_harness.log', `combo harness ${ROUND}\n`);

const FF = path.resolve('node_modules/ffmpeg-static/ffmpeg.exe');
const VIS = path.resolve('input/visuals');
const OUT = path.resolve(`output/batch/round_${ROUND}`);
fs.mkdirSync(OUT, { recursive: true });

const run = (args: string[]) =>
  new Promise<number>((res) => { const cp = spawn(FF, args); cp.on('close', (c: number) => res(c)); });

interface Seg { type: 'v' | 'i' | 'r' | 's'; file: string; dur: number; desc: string; }
const S: Record<string, Seg> = {
  v0: { type: 'v', file: 'v0.mp4', dur: 4, desc: 'city traffic' },
  v1: { type: 'v', file: 'v1.mp4', dur: 4, desc: 'ocean waves' },
  v2: { type: 'v', file: 'v2.mp4', dur: 4, desc: 'coding screen' },
  i0: { type: 'i', file: 'i0.jpg', dur: 3, desc: 'mountain' },
  i2: { type: 'i', file: 'i2.jpg', dur: 3, desc: 'abstract geometry' },
  r0: { type: 'r', file: 'batch_remotion_0_s0.mp4', dur: 4, desc: 'Remotion infographic' },
  r1: { type: 'r', file: 'batch_remotion_1_s0.mp4', dur: 4, desc: 'Remotion HUD' },
  r2: { type: 'r', file: 'batch_remotion_2_s0.mp4', dur: 4, desc: 'Remotion kinetic' },
  s0: { type: 's', file: 's0.png', dur: 4, desc: 'SCREENSHOT sproutern home' },
  s1: { type: 's', file: 's1.png', dur: 4, desc: 'SCREENSHOT github repo' },
  s2: { type: 's', file: 's2.png', dur: 4, desc: 'SCREENSHOT sproutern tools' },
};

// Deterministic seeded shuffle so each ROUND yields different orderings.
function seeded(seedStr: string) {
  let h = 2166136261;
  for (const c of seedStr) h = (h ^ c.charCodeAt(0)) * 16777619 >>> 0;
  return () => { h = (h * 1103515245 + 12345) >>> 0; return h / 4294967296; };
}
function shuffle<T>(arr: T[], rnd: () => number): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}

const prep = async (tag: string, tmp: string) => {
  const g = S[tag]; const src = path.join(VIS, g.file);
  if (g.type === 's') {
    await run(['-y', '-loop', '1', '-i', src, '-t', String(g.dur),
      '-vf', `scale=1920:-2,crop=1920:1080:0:'min(t*60,ih-1080)',fps=30`,
      '-r', '30', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', tmp]);
  } else if (g.type === 'i') {
    await run(['-y', '-loop', '1', '-i', src, '-t', String(g.dur),
      '-vf', `scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,zoompan=z='min(zoom+0.0008,1.25)':d=${Math.round(g.dur * 30)}:s=1920x1080:fps=30`,
      '-r', '30', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', tmp]);
  } else {
    await run(['-y', '-i', src, '-t', String(g.dur),
      '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',
      '-r', '30', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-an', tmp]);
  }
};

const combos: { name: string; order: string[] }[] = [
  { name: 'shot_promo', order: ['s0', 'r2', 'v0', 's2', 'r0', 'i2'] },
  { name: 'all_types_interleaved', order: ['v1', 's1', 'r1', 'i0', 's0', 'v2', 'r2', 's2'] },
  { name: 'shot_sandwich', order: ['s1', 'v2', 'r0', 'r1', 'v0', 's0'] },
  // add more orderings as needed; or generate via shuffle(tags, seeded(ROUND))
];

async function main() {
  const report: string[] = [];
  for (const combo of combos) {
    log(`Build ${combo.name} (${combo.order.length} segs)`);
    const tmps: string[] = []; let n = 0;
    for (const tag of combo.order) { const t = path.join(OUT, `_${combo.name}_${n++}.mp4`); await prep(tag, t); tmps.push(t); }
    const list = path.join(OUT, `_${combo.name}.txt`);
    fs.writeFileSync(list, tmps.map((x) => `file '${x.replace(/\\/g, '/')}'`).join('\n'));
    const final = path.join(OUT, `combo_${combo.name}.mp4`);
    const c = await run(['-y', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', final]);
    log(`  concat=${c} size=${fs.existsSync(final) ? fs.statSync(final).size : 'MISSING'}`);
    let t0 = 0;
    for (let i = 0; i < combo.order.length; i++) {
      const g = S[combo.order[i]]; const at = t0 + g.dur / 2; t0 += g.dur;
      const fr = path.join(OUT, `frame_${combo.name}_${i}_${g.type}.png`);
      await run(['-y', '-ss', String(at), '-i', final, '-frames:v', '1', fr]);
      const ok = fs.existsSync(fr) && fs.statSync(fr).size > 2000;
      report.push(`SHOT|${combo.name}|seg${i}|${combo.order[i]}|${g.type}|${g.desc}|frame=${ok ? 'OK' : 'MISSING'}`);
    }
    for (const x of tmps) { try { fs.unlinkSync(x); } catch {} }
    try { fs.unlinkSync(list); } catch {}
  }
  fs.writeFileSync(path.resolve(`workspace/batch_report_${ROUND}.txt`), report.join('\n') + '\n');
  log(`DONE -> ${report.length} segments`);
}
main().catch((e) => log('ERROR ' + (e instanceof Error ? e.stack || e.message : String(e))));
