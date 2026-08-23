// Reusable AVS bug-hunt harness (class-level technique, 2026-07-28).
// Renders a job end-to-end via the REAL agentic-modular pipeline and emits a
// 4-frame vision grid into workspace/bug-hunt/grids/<name>.jpg.
//
// Contract it enforces (the gotchas that cost real iterations):
//   - job file is a BARE JSON array of jobs (not {jobs:[...]})
//   - each job has `script` (narration string, one [Visual: file] line per scene)
//   - [Visual: x.mp4] tags are BARE filenames resolvable under input/visuals/
//     (this harness copies workspace/bug-hunt/assets/<x> -> input/visuals/<x>)
//   - set hookFirst:false to preserve authored scene order
//
// Usage:  node scripts/bug-hunt-harness.mjs <jobFile.json> <outName>
// Reusable assets live next to this script: workspace/bug-hunt/assets/{a,b,c,d}.mp4
// Kokoro voice is serialised across parallel runs via a .voice.lock file so
// multiple subagents don't collide on the port or blow ~800MB RAM.
import { execSync } from 'node:child_process';
import * as fs from 'node:fs';
import * as path from 'node:path';
import ffprobeStatic from 'ffprobe-static';

const repo = process.cwd();
const FF = path.join(repo, 'node_modules', 'ffmpeg-static', 'ffmpeg.exe');
const FFPROBE = ffprobeStatic.path;
const assets = path.join(repo, 'workspace', 'bug-hunt', 'assets');
const [jobFile, outName] = process.argv.slice(2);
if (!jobFile || !outName) { console.error('usage: bug-hunt-harness.mjs <job> <outName>'); process.exit(2); }

const PORT = process.env.VOICEBOX_PORT || '17493';
process.env.VOICEBOX_PORT = PORT;
process.env.VOICEBOX_API_URL = `http://127.0.0.1:${PORT}`;

// [Visual: x.mp4] -> copy workspace/bug-hunt/assets/x.mp4 into input/visuals/x.mp4,
// keep the tag a BARE filename (parser/--no-acquire contract).
let raw = fs.readFileSync(jobFile, 'utf-8');
const mapped = raw.replace(/\[Visual:\s*([^\]]+)\]/g, (m, f) => {
  const name = f.trim();
  const candidate = path.join(assets, name);
  if (fs.existsSync(candidate)) {
    const dest = path.join(repo, 'input', 'visuals', name);
    fs.copyFileSync(candidate, dest);
    return `[Visual: ${name}]`;
  }
  return m;
});
const tmp = path.join(repo, 'workspace', 'bug-hunt', `_${outName}.json`);
fs.writeFileSync(tmp, mapped);

// Voice-backend lock: only one Kokoro at a time (RAM + port safety).
const LOCK = path.join(repo, 'workspace', 'bug-hunt', '.voice.lock');
function sleepSync(ms) { const end = Date.now() + ms; while (Date.now() < end) {} }
function acquireLock() {
  for (let i = 0; i < 120; i++) {
    try {
      const fd = fs.openSync(LOCK, 'wx');
      fs.writeSync(fd, String(process.pid));
      fs.closeSync(fd);
      return () => { try { fs.unlinkSync(LOCK); } catch {} };
    } catch { sleepSync(2000); }
  }
  throw new Error('could not acquire voice lock after 120s');
}

function run(stage) {
  const cmd = `set VOICEBOX_PORT=${PORT}&& npx tsx src/adapters/cli/agentic-modular.ts ${stage} --file ${tmp}`;
  console.log(`\n=== ${stage} (port ${PORT}) ===`);
  try { execSync(cmd, { stdio: 'inherit', timeout: 300000, shell: true }); }
  catch (e) { console.error(`STAGE ${stage} FAILED: ${e.message}`); throw e; }
}

let release;
try {
  run('plan');
  release = acquireLock();
  run('voice');
} catch (e) {
  console.error('PLAN/VOICE stage error:', e.message);
  process.exit(1);
} finally {
  if (release) release();
}
run('visuals --no-acquire');
run('render');

// Find rendered mp4 — render names the file by TITLE (with spaces), not job id,
// so scan the job's output dir for any .mp4 rather than matching outName.
const outDir = path.join(repo, 'output');
let mp4 = null;
const candidates = [];
if (fs.existsSync(outDir)) {
  for (const d of fs.readdirSync(outDir)) {
    const dd = path.join(outDir, d);
    if (fs.statSync(dd).isDirectory()) {
      for (const f of fs.readdirSync(dd)) {
        if (f.endsWith('.mp4')) candidates.push(path.join(dd, f));
      }
    }
  }
}
mp4 = candidates.find(c => path.basename(path.dirname(c)) === outName)
    || candidates.sort((a, b) => fs.statSync(b).size - fs.statSync(a).size)[0]
    || null;
if (!mp4) { console.error('NO OUTPUT MP4 (candidates: ' + candidates.length + ')'); process.exit(3); }
console.log(`\nRENDERED: ${mp4} (${fs.statSync(mp4).size} bytes)`);

// Emit a 4-frame vision grid.
const gridDir = path.join(repo, 'workspace', 'bug-hunt', 'grids');
fs.mkdirSync(gridDir, { recursive: true });
const probe = JSON.parse(execSync(`"${FFPROBE}" -v quiet -print_format json -show_format "${mp4}"`).toString());
const dur = parseFloat(probe.format.duration);
const pts = [0.1, 0.4, 0.65, 0.9].map(p => Math.round(dur * p * 100) / 100);
const fr = pts.map((t, i) => path.join(gridDir, `${outName}_f${i}.jpg`));
fr.forEach((f, i) => execSync(`"${FF}" -y -i "${mp4}" -ss ${pts[i]} -frames:v 1 -vf scale=640:-1 "${f}"`, { stdio: 'ignore' }));
execSync(`"${FF}" -y -i "${fr[0]}" -i "${fr[1]}" -i "${fr[2]}" -i "${fr[3]}" -filter_complex "[0][1]hstack=inputs=2[t];[2][3]hstack=inputs=2[b];[t][b]vstack=inputs=2[v]" -map "[v]" -frames:v 1 "${gridDir}/${outName}.jpg"`, { stdio: 'ignore' });
console.log(`GRID: ${gridDir}/${outName}.jpg`);
