// make_grid.mjs — build a 2x2 (or NxN) vision grid from a rendered MP4.
// Usage: node workspace/bug-hunt/make_grid.mjs <video.mp4> <out.jpg> [frames=4] [w=640]
// Requires: node, ffmpeg-static (./node_modules/ffmpeg-static/ffmpeg.exe)
import * as fs from 'fs';
import * as path from 'path';
import { spawnSync } from 'child_process';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const ff = require('ffmpeg-static');

const video = process.argv[2];
const out = process.argv[3] || 'workspace/bug-hunt/grids/grid.jpg';
const frames = parseInt(process.argv[4] || '4', 10);
const w = parseInt(process.argv[5] || '640', 10);
if (!video || !fs.existsSync(video)) { console.error('video not found:', video); process.exit(1); }

const tmp = fs.mkdtempSync(path.join(require('os').tmpdir(), 'avs-grid-'));
// even spacing across duration
const durRaw = spawnSync(require('ffprobe-static').path, ['-v','error','-show_entries','format=duration','-of','csv=p=0', video]).stdout.toString().trim();
const dur = parseFloat(durRaw) || 4;
const step = dur / (frames + 1);
for (let i = 0; i < frames; i++) {
  const t = (step * (i + 1)).toFixed(2);
  spawnSync(ff, ['-y','-ss',t,'-i',video,'-vframes','1','-vf',`scale=${w}:-2`, path.join(tmp, `f${i}.png`)], { stdio: 'ignore' });
}
// stitch 2x2 (rows of 2)
const cols = 2;
const rowImgs = [];
for (let r = 0; r < frames; r += cols) {
  const rowFiles = Array.from({length: cols}, (_,c) => path.join(tmp, `f${r+c}.png`)).filter(f=>fs.existsSync(f));
  const rowOut = path.join(tmp, `row${r}.png`);
  spawnSync(ff, ['-y', ...rowFiles.flatMap(f=>['-i',f]), '-filter_complex', `hstack=inputs=${rowFiles.length}`, rowOut], { stdio: 'ignore' });
  rowImgs.push(rowOut);
}
fs.mkdirSync(path.dirname(out), { recursive: true });
spawnSync(ff, ['-y', ...rowImgs.flatMap(f=>['-i',f]), '-filter_complex', `vstack=inputs=${rowImgs.length}`, out], { stdio: 'ignore' });
console.log('grid ->', out);
