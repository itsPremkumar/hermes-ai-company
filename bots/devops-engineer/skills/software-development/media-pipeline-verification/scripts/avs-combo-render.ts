// avs-combo-render.ts — deterministic "many new combinations" render + verify.
//
// USAGE (from repo root, after `npm i`):
//   npx tsx <skill>/scripts/avs-combo-render.ts [--no-run] [--sample 47]
//
// WHAT IT DOES
//   1. Generates a combinatorial agentic-scripts.json batch:
//        perspectives(10) x orientations(3) x captions(3) x music(round-robin)
//        + a multi-language all-tags STRESS job + a control-surface dryRun job.
//   2. Backs up the current input/scripts/agentic-scripts.json to .bak first.
//   3. Runs `npm run generate:agentic` end-to-end (real local-asset render).
//   4. Asserts, for every rendered output, that ffprobe WxH matches the
//      requested orientation (portrait 720x1280 / landscape 1280x720 / square 1080x1080).
//   5. Extracts a late frame per orientation for a manual vision spot-check.
//
// RE-VERIFY RULE (see references/avs-visual-reverify.md):
//   If you JUST fixed a render bug, the PRE-fix batch is STALE evidence. Run this
//   script AFTER the fix lands so the same matrix exercises the fixed code.
//
// NOTE: this script writes input/scripts/agentic-scripts.json — restore it from
// the .bak afterwards (or `git checkout -- input/scripts/agentic-scripts.json`).

import * as fs from 'fs';
import { execFileSync, spawnSync } from 'child_process';

const ROOT = process.cwd();
const SCRIPT_PATH = 'input/scripts/agentic-scripts.json';
const EXPECT: Record<string, string> = { portrait: '720,1280', landscape: '1280,720', square: '1080,1080' };

const PERSP = ['persp_aerial','persp_closeup','persp_wide','persp_angle','persp_top','persp_night','persp_warm','persp_cool','persp_urban','persp_nature'];
const ORIENTS = ['portrait','landscape','square'] as const;
const CAPTIONS = ['burned','karaoke','none'] as const;
const MUSIC = ['lofi_chill.mp3','cinematic_drone.mp3','upbeat_electronic.mp3','ambient_piano.mp3'];
const GRADES = ['warm','cool','cinematic','vivid','neutral'];
const TRANS = ['fade','slide','zoomblur','wipe'];

const args = process.argv.slice(2);
const NO_RUN = args.includes('--no-run');
const sampleArg = args.find((a) => a.startsWith('--sample='));
const SAMPLE = sampleArg ? Math.max(1, parseInt(sampleArg.split('=')[1], 10)) : 47;

// 1) backup + generate batch
fs.copyFileSync(SCRIPT_PATH, SCRIPT_PATH + '.bak');
let n = 0; const jobs: any[] = [];
for (const p of PERSP) for (const o of ORIENTS) for (const c of CAPTIONS) {
  n++;
  const mus = MUSIC[n % MUSIC.length];
  const capTheme = c === 'none' ? undefined : (['neon','bold','minimal','vivid'] as const)[n % 4];
  const grade = GRADES[n % GRADES.length];
  const trans = TRANS[n % TRANS.length];
  const la = [p + '.png', PERSP[(n + 3) % PERSP.length] + '.png'];
  jobs.push({
    id: `broad_${String(n).padStart(3,'0')}_${p.replace('persp_','')}_${o}_${c}`,
    title: `Broad ${p.replace('persp_','')} ${o} ${c}`,
    topic: `perspective ${p}`,
    script: `Scene one from ${p.replace('persp_','')} view. [Visual: ${la[0]}] [Grade: ${grade}] [Transition: ${trans}]\nScene two continues. [Visual: ${la[1]}] [CaptionTheme: ${capTheme ?? 'neon'}] [Kinetic: on]`,
    orientation: o, voice: 'en-US-GuyNeural', language: 'english', backend: 'heuristic',
    candidatesPerAsset: 1, captions: c, captionTheme: capTheme, vignette: n % 2 === 0,
    kineticText: c !== 'none', musicIntensity: (['calm','mid','energetic'] as const)[n % 3],
    sfx: n % 3 === 0, preset: o === 'square' ? 'square' : o === 'landscape' ? 'cinematic' : 'reels',
    localAssets: la, backgroundMusic: mus, musicVolume: 0.15,
  });
}
jobs.push({
  id: 'broad_stress_alltags', title: 'Broad Stress All Tags', topic: 'stress test',
  script: 'Stress one. [Visual: persp_wide.png] [Grade: cinematic] [Transition: wipe] [CaptionTheme: bold] [Kinetic: on] [Vignette: on] [Color: cyan] [KenBurns: on]\nStress two. [Visual: persp_nature.png] [Style: center] [SFX: on] [Transition: slide]',
  orientation: 'portrait', voice: 'en-IN-NeerjaNeural', language: 'hindi', backend: 'heuristic',
  candidatesPerAsset: 1, captions: 'burned', captionTheme: 'neon', vignette: true, kineticText: true,
  musicIntensity: 'energetic', sfx: true, preset: 'reels', localAssets: ['persp_wide.png','persp_nature.png'],
  backgroundMusic: 'upbeat_electronic.mp3', musicVolume: 0.15,
});
jobs.push({
  id: 'broad_control_dry', title: 'Broad Control DryRun', topic: 'control surface',
  script: 'Control scene. [Visual: persp_aerial.png]',
  orientation: 'landscape', voice: 'en-US-GuyNeural', language: 'english', backend: 'agent',
  aiVerify: false, brain: false, pruneWorkspaces: false, agent: 'off', defaultVisual: 'search',
  candidatesPerAsset: 1, captions: 'burned', captionTheme: 'minimal', vignette: true, kineticText: false,
  musicIntensity: 'calm', sfx: false, preset: 'cinematic', dryRun: true,
  localAssets: ['persp_aerial.png'], backgroundMusic: 'lofi_chill.mp3', musicVolume: 0.15,
});

// sample down to keep the run bounded but keep full axis coverage
const special = jobs.filter((j) => j.id.includes('stress') || j.id.includes('control'));
let core = jobs.filter((j) => !j.id.includes('stress') && !j.id.includes('control'));
core = core.filter((_, i) => i % 2 === 0).slice(0, Math.max(1, SAMPLE - special.length));
const out = [...core, ...special];
fs.writeFileSync(SCRIPT_PATH, JSON.stringify(out, null, 2));
console.log(`[combo] wrote ${out.length} jobs (core ${core.length} + special ${special.length}); backup at ${SCRIPT_PATH}.bak`);

if (NO_RUN) { console.log('[combo] --no-run: batch written, skipping render.'); process.exit(0); }

// 2) run the real pipeline
console.log('[combo] running npm run generate:agentic ...');
const r = spawnSync('npx', ['tsx', 'src/adapters/cli/agentic-cli.ts'], { cwd: ROOT, stdio: 'inherit' });
if (r.status !== 0) { console.error(`[combo] pipeline exited ${r.status}`); process.exit(r.status ?? 1); }

// 3) assert dimensions per orientation
let total = 0, valid = 0, broken = 0, dimMismatch = 0; const issues: string[] = [];
const ffprobe = require('ffprobe-static').path;
const ffmpeg = require('ffmpeg-static').path;
const dirs = fs.readdirSync('output').filter((d) => d.startsWith('broad_'));
fs.mkdirSync('workspace/tmp/frames', { recursive: true });
for (const d of dirs) {
  const files = fs.readdirSync('output/' + d).filter((x) => x.endsWith('.mp4') && !x.includes('_1x1') && !x.includes('_16x9'));
  if (!files.length) continue; // dryRun produces none
  const f = 'output/' + d + '/' + files[0];
  const sz = fs.statSync(f).size; total++;
  if (sz < 1000) { broken++; issues.push(`${d}: too small (${sz}B)`); continue; }
  try {
    const dim = execFileSync(ffprobe, ['-v','error','-show_entries','stream=width,height','-of','csv=p=0',f], { encoding: 'utf8' }).trim().replace(/\r/g,'').split('\n')[0];
    const orient = d.includes('portrait') ? 'portrait' : d.includes('landscape') ? 'landscape' : d.includes('square') ? 'square' : '';
    if (orient && EXPECT[orient] && dim !== EXPECT[orient]) { dimMismatch++; issues.push(`${d}: dim ${dim} expected ${EXPECT[orient]}`); }
    valid++;
    if (d.includes('_portrait_') || d.includes('_landscape_') || d.includes('_square_')) {
      const outp = 'workspace/tmp/frames/' + d.replace(/[^a-zA-Z0-9]/g,'_') + '_late.png';
      try { execFileSync(ffmpeg, ['-y','-ss','3.0','-i',f,'-frames:v','1','-vf','scale=480:-1',outp], { stdio: 'ignore' }); } catch {}
    }
  } catch (e: any) { broken++; issues.push(`${d}: ffprobe err ${String(e.message).slice(0,40)}`); }
}
console.log(`[combo] outputs: ${total} | valid: ${valid} | broken: ${broken} | dim-mismatch: ${dimMismatch}`);
if (issues.length) { console.log('ISSUES:\n' + issues.join('\n')); process.exit(1); }
console.log('[combo] OK — all dimensions match requested orientation. Spot-check frames in workspace/tmp/frames/.');
