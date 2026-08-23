#!/usr/bin/env node
// check_render.js — verify a rendered video artifact (PHASE 4 gate).
// Usage: node check_render.js "<path-to>.mp4"
// Probes: container/streams (via ffmpeg -i), black frames (blackdetect).
// NOTE: project ships ffmpeg-static (ffmpeg.exe), NOT ffprobe. Parse ffmpeg -i.
const { execFileSync } = require('child_process');
const ffmpeg = require('ffmpeg-static');
const mp4 = process.argv[2];
if (!mp4) { console.error('usage: node check_render.js <file.mp4>'); process.exit(2); }

function run(args, captureStderr) {
  try {
    return execFileSync(ffmpeg, args, captureStderr ? { stderr: true } : {}).toString();
  } catch (e) {
    return (e.stderr || e.stdout || e.message || '').toString();
  }
}

// 1. streams + duration
const info = run(['-i', mp4], true);
const streams = info.split('\n').filter(l => /Stream #/.test(l));
console.log('=== STREAMS ===');
console.log(streams.join('\n'));
const dur = (info.match(/Duration:\s*([\d:.]+)/) || [])[1];
console.log('Duration:', dur);

// 2. black frames
const black = run(['-v', 'error', '-i', mp4, '-vf', 'blackdetect=d=0.3:pix_th=0.15', '-f', 'null', '-'], true);
if (/blackdetect/.test(black)) {
  console.log('\n❌ BLACK FRAMES DETECTED:\n' + black.trim());
  process.exit(1);
} else {
  console.log('\n✅ NO black frames (blackdetect d=0.3 pix_th=0.15)');
}

// 3. verdict
const hasVideo = streams.some(l => /Video:/.test(l));
const hasAudio = streams.some(l => /Audio:/.test(l));
if (hasVideo && hasAudio && dur && dur !== '00:00:00.00') {
  console.log('✅ RENDER GATE PASSED: video+audio present, non-zero duration, no black frames');
  process.exit(0);
} else {
  console.log('❌ RENDER GATE FAILED: missing video/audio or zero duration');
  process.exit(1);
}
