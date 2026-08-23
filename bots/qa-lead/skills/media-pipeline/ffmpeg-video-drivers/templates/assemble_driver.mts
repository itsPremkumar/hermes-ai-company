// Known-good top-level-await driver: builds N normalized scenes (image / video /
// tall-screenshot aware) from an asset+voice list, then concats via the demuxer
// with BARE filenames (P1 fix). Copy + modify for any one-by-one AVS build.
//
// Run:  node --import tsx thisfile.mts </dev/null
import * as fs from 'fs';
import { execFileSync } from 'child_process';

const FF = 'node_modules/ffmpeg-static/ffmpeg.exe';
const V = 'input/visuals';

function dims(p: string): [number, number] {
  let out = '';
  try { out = execFileSync(FF, ['-i', p], { encoding: 'utf8', stdio: ['ignore', 'ignore', 'pipe'] }); }
  catch (e: any) { out = e.stderr || ''; }
  const m = out.match(/(\d+)x(\d+)/);
  return m ? [+m[1], +m[2]] : [0, 0];
}

function buildScene(i: number, pic: string, aud: string) {
  const isImg = /\.(png|jpg|jpeg)$/i.test(pic);
  if (isImg) {
    const [w, h] = dims(pic);
    const vf = h > w * 1.3
      ? "scale=1920:-2,crop=1920:1080:0:'min((ih-oh)*t/4,ih-oh)'"            // tall -> scroll-pan (P4)
      : 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,zoompan=z=\'min(zoom+0.0008,1.12)\':d=120:s=1920x1080:fps=30';
    execFileSync(FF, ['-y', '-loop', '1', '-framerate', '30', '-i', pic, '-t', '4', '-vf', vf, // P3: -framerate before -i
      '-r', '30', '-s', '1920x1080', '-pix_fmt', 'yuv420p', '-c:v', 'libx264',
      '-c:a', 'aac', '-ar', '44100', '-ac', '1', '-shortest', `${V}/build_scene_${i}.mp4`]);
  } else {
    execFileSync(FF, ['-y', '-i', pic, '-t', '4',
      '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',
      '-r', '30', '-s', '1920x1080', '-pix_fmt', 'yuv420p', '-c:v', 'libx264',
      '-c:a', 'aac', '-ar', '44100', '-ac', '1', '-shortest', `${V}/build_scene_${i}.mp4`]);
  }
  console.log(`scene${i} ok bytes=${fs.statSync(`${V}/build_scene_${i}.mp4`).size}`);
}

// asset (video/img) + narration wav, one per scene
const scenes: [string, string][] = [
  [`${V}/build_onebyone_s0.mp4`, `${V}/build_voice/scene_1_voice.wav`],
  [`${V}/build_onebyone_s1.mp4`, `${V}/build_voice/scene_2_voice.wav`],
  [`${V}/build_vid_edited.mp4`,  `${V}/build_voice/scene_3_voice.wav`],
  [`${V}/build_hud2_s0.mp4`,     `${V}/build_voice/scene_4_voice.wav`],
  [`${V}/s2.png`,                `${V}/build_voice/scene_5_voice.wav`],
  [`${V}/build_img_edited.jpg`,  `${V}/build_voice/scene_6_voice.wav`],
];

for (let i = 0; i < scenes.length; i++) buildScene(i + 1, scenes[i][0], scenes[i][1]);

// P1 fix: bare filenames relative to the list file's directory (V)
const list = `${V}/build_list.txt`;
fs.writeFileSync(list, scenes.map((_, i) => `file 'build_scene_${i + 1}.mp4'`).join('\n'));
execFileSync(FF, ['-y', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', `${V}/build_final.mp4`]);
console.log('CONCAT OK final bytes=' + fs.statSync(`${V}/build_final.mp4`).size);

// optional: duck music under voiceover
// ffmpeg -i build_final.mp4 -i build_music.mp3 -filter_complex "[1:a]volume=0.25[bg];[0:a][bg]amix=inputs=2:duration=longest:dropout_transition=0[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -shortest build_final_music.mp4

for (let i = 1; i <= scenes.length; i++) { try { fs.unlinkSync(`${V}/build_scene_${i}.mp4`); } catch {} }
try { fs.unlinkSync(list); } catch {}
