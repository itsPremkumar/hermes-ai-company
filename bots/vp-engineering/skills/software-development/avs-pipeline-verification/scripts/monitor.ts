// monitor.ts — parse combo_matrix.log and report progress + real errors.
// Run: npx tsx monitor.ts   (after launching the matrix in background)
import * as fs from 'fs';
const log = 'workspace/tmp/combo_matrix.log';
if (!fs.existsSync(log)) { console.log('no log yet'); process.exit(0); }
const s = fs.readFileSync(log, 'utf8');
const outputs = (s.match(/Output:/g) || []).length;
const fails = (s.match(/Job failed/g) || []).length;
const summary = s.match(/Summary:.*/);
const lastJob = (s.match(/Workspace:.*combo_\d+/g) || []).pop() || 'n/a';
// Real unhandled errors = anything fatal that is NOT the two known fallbacks.
const unhandled = s.split('\n').filter(l =>
  /TypeError|ReferenceError|is not a function|Cannot read|undefined is not|ENOENT|throw new/.test(l) &&
  !/ModuleNotFoundError/.test(l));
console.log(JSON.stringify({ outputs, fails, summary: summary ? summary[0] : null, lastJob, unhandledErrors: unhandled.slice(-5) }, null, 2));

// validate-outputs.ts — ffprobe every generated mp4; report invalid/tiny.
// Run: npx tsx validate-outputs.ts
import { execFileSync } from 'child_process';
const ffprobe = require('ffprobe-static').path;
const dirs = fs.readdirSync('output').filter(d => d.startsWith('combo_'));
let ok = 0, tiny = 0, corrupt = 0;
for (const d of dirs) {
  const base = 'output/' + d;
  for (const f of fs.readdirSync(base).filter(x => x.endsWith('.mp4'))) {
    const fp = base + '/' + f, sz = fs.statSync(fp).size;
    if (sz < 1000) { tiny++; console.log('TINY:', d + '/' + f, sz); continue; }
    try { execFileSync(ffprobe, ['-v', 'error', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', fp], { encoding: 'utf8' }); ok++; }
    catch { corrupt++; console.log('CORRUPT:', d + '/' + f); }
  }
}
console.log(`VALID:${ok} TINY:${tiny} CORRUPT:${corrupt} DIRS:${dirs.length}`);
