/**
 * batch_combo_harness.mts — reusable continuous-combination verification harness
 * for the Remotion mixed-source pipeline (user's standing "prove everything works"
 * ask). Re-run per round with a different round name to get a DIFFERENT set of
 * orderings each time, and accumulate per-segment frame checks.
 *
 * Usage:
 *   node --import tsx scripts/batch_combo_harness.mts R1
 *   node --import tsx scripts/batch_combo_harness.mts R2   # different seed -> new orderings
 *
 * Prereqs (assets already in input/visuals from a prior Pexels+Remotion batch):
 *   v0/v1/v2.mp4  (downloaded Pexels videos)
 *   i0/i1/i2.jpg  (downloaded Pexels images)
 *   batch_remotion_0_s0.mp4 / _1_ / _2_  (3 autonomous Remotion clips:
 *     infographic, HUD, kinetic)
 *
 * What it does:
 *   1. Defines 9 segments (3 video + 3 image + 3 Remotion) with metadata.
 *   2. Builds 5 orderings (video-led, Remotion-led, interleaved[seeded shuffle],
 *      Remotion-adjacent, mixed-pairs[seeded shuffle]).
 *   3. Composes each to output/batch/round_<R>/combo_<name>.mp4 (1920x1080,
 *      image->ken-burns zoompan, video normalized, Remotion as-is).
 *   4. Extracts ONE frame from EVERY segment of EVERY combo and ffprobe-checks
 *      it (frame size > 2KB => not black/corrupt).
 *   5. Writes workspace/batch_report_<R>.txt:  R|combo|seg|tag|type|desc|frame=OK
 *
 * Verification bar: ffprobe-level per-segment (catches black/corrupt); spot-check
 * Remotion segments with vision_analyze separately (see mixed-source-pipeline.md).
 * NOTE: a 3-scene TransitionSeries w/ 2 transitions takes ~2-3 min headless —
 * run foreground w/ >=280s timeout; a 60s background clamp kills it and looks
 * like a bug. See SKILL.md "Headless-GPU trap" + "Background-render error-swallowing".
 */
import * as fs from 'fs';
import * as path from 'path';
import { spawn } from 'child_process';

const ROUND = process.argv[2] || 'R1';
const log = (m: string) => fs.appendFileSync('workspace/_harness.log', m + '\n');
fs.writeFileSync('workspace/_harness.log', `harness round ${ROUND}\n`);

const FF = path.resolve('node_modules/ffmpeg-static/ffmpeg.exe');
const VIS = path.resolve('input/visuals');
const OUT = path.resolve(`output/batch/round_${ROUND}`);
fs.mkdirSync(OUT, { recursive: true });
const FRAME = path.resolve(`workspace/batch_frames/${ROUND}`);
fs.mkdirSync(FRAME, { recursive: true });

const run = (args: string[]) => new Promise<number>((res) => {
  const cp = spawn(FF, args);
  cp.on('close', (c: number) => res(c));
});

type T = 'v' | 'i' | 'r';
interface Seg { tag: string; type: T; file: string; dur: number; desc: string; }
const SEGS: Record<string, Seg> = {
  v0: { tag: 'v0', type: 'v', file: 'v0.mp4', dur: 4, desc: 'city traffic timelapse' },
  v1: { tag: 'v1', type: 'v', file: 'v1.mp4', dur: 4, desc: 'ocean waves drone' },
  v2: { tag: 'v2', type: 'v', file: 'v2.mp4', dur: 4, desc: 'coding screen' },
  i0: { tag: 'i0', type: 'i', file: 'i0.jpg', dur: 3, desc: 'mountain landscape' },
  i1: { tag: 'i1', type: 'i', file: 'i1.jpg', dur: 3, desc: 'coffee shop interior' },
  i2: { tag: 'i2', type: 'i', file: 'i2.jpg', dur: 3, desc: 'abstract geometry' },
  r0: { tag: 'r0', type: 'r', file: 'batch_remotion_0_s0.mp4', dur: 4, desc: 'Remotion infographic Market Growth' },
  r1: { tag: 'r1', type: 'r', file: 'batch_remotion_1_s0.mp4', dur: 4, desc: 'Remotion HUD radar' },
  r2: { tag: 'r2', type: 'r', file: 'batch_remotion_2_s0.mp4', dur: 4, desc: 'Remotion kinetic Powered by AI' },
};
const V = ['v0', 'v1', 'v2'], I = ['i0', 'i1', 'i2'], R = ['r0', 'r1', 'r2'];

function makeCombos(round: string): { name: string; order: string[] }[] {
  const seed = round.charCodeAt(round.length - 1) + round.length;
  const shuf = (a: string[]) => {
    const r = [...a];
    for (let i = r.length - 1; i > 0; i--) { const j = (seed * (i + 7) + 3) % (i + 1); [r[i], r[j]] = [r[j], r[i]]; }
    return r;
  };
  return [
    { name: 'vid_img_remotion', order: [...V, ...I, ...R] },
    { name: 'remotion_vid_img', order: [...R, ...V, ...I] },
    { name: 'interleaved', order: shuf([...V, ...I, ...R]) },
    { name: 'remotion_adjacent', order: ['r0', 'v0', 'i0', 'r1', 'v1', 'i1', 'r2', 'v2', 'i2'] },
    { name: 'mixed_pairs', order: shuf(['v0', 'r2', 'i1', 'v1', 'r0', 'i2', 'v2', 'r1', 'i0']) },
  ];
}

const durOf = (tag: string) => SEGS[tag].dur;
const prep = async (tag: string, tmp: string) => {
  const s = SEGS[tag]; const src = path.join(VIS, s.file);
  if (s.type === 'i') {
    await run(['-y', '-loop', '1', '-i', src, '-t', String(s.dur), '-vf', `scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,zoompan=z='min(zoom+0.0008,1.25)':d=${Math.round(s.dur * 30)}:s=1920x1080:fps=30`, '-r', '30', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', tmp]);
  } else {
    await run(['-y', '-i', src, '-t', String(s.dur), '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2', '-r', '30', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-an', tmp]);
  }
};

async function main() {
  const combos = makeCombos(ROUND);
  const report: string[] = [];
  for (const combo of combos) {
    log(`Build ${combo.name} (${combo.order.length} segs)`);
    const tmps: string[] = [];
    let t = 0;
    for (const tag of combo.order) { const tmp = path.join(OUT, `_${combo.name}_${t++}.mp4`); await prep(tag, tmp); tmps.push(tmp); }
    const list = path.join(OUT, `_${combo.name}.txt`);
    fs.writeFileSync(list, tmps.map((x) => `file '${x.replace(/\\/g, '/')}'`).join('\n'));
    const final = path.join(OUT, `combo_${combo.name}.mp4`);
    const c = await run(['-y', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', final]);
    const ok = fs.existsSync(final);
    log(`  concat=${c} size=${ok ? fs.statSync(final).size : 'MISSING'}`);
    for (let i = 0; i < combo.order.length; i++) {
      const tag = combo.order[i]; const s = SEGS[tag];
      const at = (i === 0 ? 0.5 : combo.order.slice(0, i).reduce((a, x) => a + durOf(x), 0) + s.dur / 2);
      const fr = path.join(FRAME, `${combo.name}_${i}.png`);
      await run(['-y', '-ss', String(at), '-i', final, '-frames:v', '1', fr]);
      const frOk = fs.existsSync(fr) && fs.statSync(fr).size > 2000;
      report.push(`${ROUND}|${combo.name}|seg${i}|${tag}|${s.type}|${s.desc}|frame=${frOk ? 'OK' : 'MISSING'}`);
    }
    for (const x of tmps) { try { fs.unlinkSync(x); } catch {} }
    try { fs.unlinkSync(list); } catch {}
  }
  fs.writeFileSync(path.resolve(`workspace/batch_report_${ROUND}.txt`), report.join('\n') + '\n');
  log('DONE ' + ROUND + ' -> ' + report.length + ' segments verified');
}
main().catch((e) => log('ERROR ' + (e instanceof Error ? e.stack || e.message : String(e))));
