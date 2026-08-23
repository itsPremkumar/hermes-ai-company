# Fixture generator — varied-input matrix for media/ffmpeg dogfooding

Copy this into a scratch `.ts` and run with `npx tsx <file>.ts`. Generates a matrix
of clips + multi-scene masters (no network; ffmpeg-static only), then you call your
function against each.

```ts
import * as fs from 'fs';
import * as path from 'path';
import { execFileSync } from 'child_process';
const FF = 'C:/one/Automated-Video-Generator/node_modules/ffmpeg-static/ffmpeg.exe';
const OUT = 'C:/one/_dogfood';
fs.rmSync(OUT, { recursive: true, force: true }); fs.mkdirSync(OUT, { recursive: true });

type V = { name: string; w: number; h: number; dur: number; audio: boolean };
const variants: V[] = [
  { name: 'portrait_4s_audio',  w: 720,  h: 1280, dur: 4, audio: true },
  { name: 'landscape_6s_audio', w: 1280, h: 720,  dur: 6, audio: true },
  { name: 'square_3s_audio',    w: 1080, h: 1080, dur: 3, audio: true },
  { name: 'portrait_2s_noa',    w: 720,  h: 1280, dur: 2, audio: false },
  { name: 'landscape_10s_audio',w: 1920, h: 1080, dur: 10,audio: true },
  { name: 'portrait_1s_audio',  w: 720,  h: 1280, dur: 1, audio: true },
];

function mk(p: string, v: V) {
  const a = v.audio ? ['-f','lavfi','-i',`sine=frequency=440:duration=${v.dur}`,'-ac','1'] : ['-an'];
  execFileSync(FF, ['-f','lavfi','-i',`color=c=${'red'}:s=${v.w}x${v.h}:d=${v.dur}`, ...a,
    '-t',String(v.dur),'-r','25','-c:v','libx264','-pix_fmt','yuv420p',
    ...(v.audio?['-c:a','aac','-b:a','128k']:[]),'-y',p], { stdio:'ignore' });
}

// Multi-scene master via concat so plan total == master duration.
function master(v: V) {
  const n = Math.max(1, Math.floor(v.dur));        // 1s scenes
  const sd = 1;
  const sub = path.join(OUT, v.name+'_scenes'); fs.mkdirSync(sub, { recursive: true });
  const lines: string[] = [];
  for (let i=0;i<n;i++){
    const c = path.join(sub,`s${i}.mp4`);
    const a = v.audio ? ['-f','lavfi','-i',`sine=frequency=${440+i*50}:duration=${sd}`,'-ac','1'] : ['-an'];
    execFileSync(FF, ['-f','lavfi','-i',`color=c=red:s=${v.w}x${v.h}:d=${sd}`,...a,'-t',String(sd),'-r','25','-c:v','libx264','-pix_fmt','yuv420p',...(v.audio?['-c:a','aac','-b:a','128k']:[]),'-y',c],{stdio:'ignore'});
    lines.push(`file '${c.replace(/\\/g,'/')}'`);
  }
  fs.writeFileSync(path.join(sub,'list.txt'), lines.join('\n'));
  const m = path.join(OUT, v.name+'_master.mp4');
  execFileSync(FF, ['-y','-f','concat','-safe','0','-i',path.join(sub,'list.txt'),'-c','copy',m], { stdio:'ignore' });
  const plan = { scenes: Array.from({length:n},()=>({durationSec:sd})) };
  fs.writeFileSync(path.join(OUT, v.name+'_plan.json'), JSON.stringify(plan));
  return { master: m, planPath: path.join(OUT, v.name+'_plan.json') };
}

for (const v of variants) {
  mk(path.join(OUT, v.name+'.mp4'), v);
  const { master: m, planPath } = master(v);
  // const { restitchMaster } = await import('.../restitch.js');
  // await restitchMaster(m, path.join(OUT,v.name+'.mp4'), planPath, 2, path.join(OUT,v.name+'_out.mp4'));
}
```

Notes:
- Authoritative duration = ffmpeg `-i` "Duration:" line, NOT a ceil()'d wrapper.
- A `try/catch` returning `{ok:false,detail}` can MASK the real cause — temporarily
  print `e.stderr` or run the exact ffmpeg concat command standalone to see the true
  error (e.g. "matches no streams", "dimension mismatch").
- Concats built with `-c copy` pad ~1s; derive restitch cut points from the PLAN,
  not the master file duration.
