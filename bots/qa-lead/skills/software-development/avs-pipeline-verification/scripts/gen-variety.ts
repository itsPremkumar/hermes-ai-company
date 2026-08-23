/**
 * gen-variety.ts — Generate a VARIETY of videos by driving the REAL
 * renderAgenticSlideshow() across aspect ratios + scene counts, using the
 * local assets in input/visuals/. Music is added but NO voiceover, so every
 * render exercises the audit fixes (A3 slim-shape guard, D1 music-mux on
 * audio-less silent, E1 genpts concat).
 *
 * WHY THIS PATH (not agentic-batch / agentic-cli): those run the full
 * plan→visuals→voice→render pipeline which FETCHES stock visuals and TIMES OUT
 * on this offline box. Calling renderAgenticSlideshow directly with a
 * hand-built PipelineResult + local assets is the fastest offline way to
 * produce real mp4s — and it hits exactly the code the audio-less/concat audit
 * hardened.
 *
 * Run from project root:  npx tsx scripts/gen-variety.ts
 * Output: output/variety/<id>.mp4  — each call ALSO auto-spawns
 *         <id>_16x9.mp4 / <id>_1x1.mp4 / <id>_9x16.mp4 (renderVariant).
 *
 * RAM GOTCHA (G15): at <~400MB free the gyan.dev ffmpeg build SEGFAULTS
 * (exit 3221225794 = 0xC0000005) on sequential renders. If several variants
 * fail with that code, run them in ISOLATION (one variant per process) or free
 * RAM / kill stray ffmpeg.exe first. See references/avs-variety-generation.md.
 */
import * as fs from 'fs';
import * as path from 'path';
import { renderAgenticSlideshow } from '../src/agentic/orchestrator/render.js';

const ROOT = path.resolve(process.cwd());
const VIS = path.join(ROOT, 'input', 'visuals');
const MUSIC = path.join(VIS, 'local_demo_ambient.mp3');
const OUT = path.join(ROOT, 'output', 'variety');
fs.mkdirSync(OUT, { recursive: true });

const CLIPS = ['a.mp4', 'b.mp4', 'c.mp4', 'd.mp4', 'gs.mp4', 'local_s0.mp4', 'local_s1.mp4', 'local_s2.mp4', 'local_s3.mp4'];

function makeRes(jobId: string, clipNames: string[], music: boolean, trulySilent = false) {
  const assets = clipNames.map((name, i) => ({
    kind: 'video' as const,
    sceneIndex: i,
    localPath: path.join(VIS, name),
    durationSec: 4,
    license: 'local',
  }));
  if (music && !trulySilent) assets.push({ kind: 'music' as const, sceneIndex: -1, localPath: MUSIC, license: 'local' });
  return {
    workspace: { root: OUT, jobId },
    plan: { scenes: clipNames.map((_, i) => ({ sceneIndex: i, durationSec: 4, voiceoverText: '' })) },
    manifest: { jobId, title: jobId, assets },
    gate: { pass: true },
  } as any;
}

const variants = [
  { id: 'v1_portrait_9x16_3clip', clips: ['a.mp4', 'b.mp4', 'c.mp4'], aspect: '9:16' as const, music: true },
  { id: 'v2_square_1x1_5clip', clips: ['a.mp4', 'b.mp4', 'c.mp4', 'd.mp4', 'gs.mp4'], aspect: '1:1' as const, music: true },
  { id: 'v3_landscape_16x9_4clip', clips: ['local_s0.mp4', 'local_s1.mp4', 'local_s2.mp4', 'local_s3.mp4'], aspect: '16:9' as const, music: true },
  { id: 'v4_portrait_multi_7clip', clips: CLIPS.slice(0, 7), aspect: '9:16' as const, music: true },
  { id: 'v5_landscape_nomusic_3clip', clips: ['a.mp4', 'b.mp4', 'c.mp4'], aspect: '16:9' as const, music: false },
  { id: 'v6_audioless_silent_3clip', clips: ['a.mp4', 'b.mp4', 'c.mp4'], aspect: '9:16' as const, music: false, trulySilent: true },
];

(async () => {
  const results: { id: string; ok: boolean }[] = [];
  for (const v of variants) {
    const outPath = path.join(OUT, `${v.id}.mp4`);
    try {
      const res = makeRes(v.id, v.clips, v.music, (v as any).trulySilent);
      const got = await renderAgenticSlideshow(res, {
        outPath,
        aspect: v.aspect,
        music: v.music,
        burnCaptions: false,
        kenBurns: true,
        transition: 'fade',
        sfx: false,
      });
      const ok = !!got && fs.existsSync(got) && fs.statSync(got).size > 1000;
      results.push({ id: v.id, ok });
      console.log(`${ok ? '✅' : '❌'} ${v.id} -> ${got}`);
    } catch (e: any) {
      results.push({ id: v.id, ok: false });
      console.log(`❌ ${v.id} -> ERROR: ${(e?.message ?? e).slice(0, 200)}`);
    }
  }
  const pass = results.filter((r) => r.ok).length;
  console.log(`\n=== GENERATED ${pass}/${results.length} VIDEOS ===`);
  process.exit(pass === results.length ? 0 : 1);
})();
