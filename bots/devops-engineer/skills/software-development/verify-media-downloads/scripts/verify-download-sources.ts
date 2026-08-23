/**
 * verify-download-sources.ts  (AVS-shaped empirical probe)
 * Copy into your project's scripts/ and run:  npx tsx scripts/verify-download-sources.ts
 *
 * Calls each media source's REAL fetcher, downloads 1 image + 1 video per source,
 * prints a PASS/FAIL table with byte counts. Loads .env so keyed providers are used.
 *
 * ADAPT the import paths to your project layout before running.
 */
import { config as loadEnv } from 'dotenv';
loadEnv();

import * as fs from 'fs';
import * as path from 'path';
import { downloadMedia } from '../src/lib/visual-fetcher/download.js';
import { searchPexelsImages, searchPexelsVideos } from '../src/lib/pexels.js';
import { searchImages, fetchVisualsForScene } from '../src/lib/visual-fetcher/index.js';
import { freeImageAdapter } from '../src/lib/free-image/index.js';
import { FreeVideoAdapter } from '../src/lib/free-video/adapter.js';

const OUT = path.resolve('workspace', 'verify-downloads');
const withTimeout = <T,>(p: Promise<T>, ms: number): Promise<T> =>
  Promise.race([p, new Promise<T>((_, rej) => setTimeout(() => rej(new Error('timeout ' + ms + 'ms')), ms))]);

type Row = { source: string; media: string; status: 'PASS' | 'FAIL' | 'ERROR'; bytes: number; note: string };
const rows: Row[] = [];

async function rec(source: string, media: string, fn: () => Promise<{ file: string | null; note?: string } | null>) {
  try {
    const r = await withTimeout(fn(), 120000);
    const fp = r?.file;
    const ok = !!fp && fs.existsSync(fp) && fs.statSync(fp).size > 0;
    rows.push({ source, media, status: ok ? 'PASS' : 'FAIL', bytes: ok ? fs.statSync(fp).size : 0, note: r?.note || (ok ? '' : 'no file') });
  } catch (e: any) {
    rows.push({ source, media, status: 'ERROR', bytes: 0, note: e?.message || String(e) });
  }
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const dl = async (url: string, dir: string, name: string): Promise<string | null> => {
    try { const r = await downloadMedia(url, dir, name); return r.path ?? null; } catch { return null; }
  };

  // KEYED (Pexels/Pixabay/Openverse) — needs .env keys
  await rec('pexels(image/keyed)', 'image', async () => {
    const r = await searchPexelsImages('ocean', 1);
    if (!r.length) return { note: 'empty' };
    const dir = path.join(OUT, 'pexels-img'); fs.mkdirSync(dir, { recursive: true });
    return { file: await dl(r[0].downloadUrl, dir, 'p.jpg'), note: 'p.jpg' };
  });
  await rec('pexels(video/keyed)', 'video', async () => {
    const r = await searchPexelsVideos('waterfall', 1);
    if (!r.length) return { note: 'empty' };
    const dir = path.join(OUT, 'pexels-vid'); fs.mkdirSync(dir, { recursive: true });
    return { file: await dl(r[0].downloadUrl, dir, 'p.mp4'), note: 'p.mp4' };
  });
  await rec('searchImages(openverse/pexels)', 'image', async () => {
    const r = await searchImages('city', 5, { preferVideo: false });
    if (!r.length) return { note: 'empty' };
    const dir = path.join(OUT, 'search'); fs.mkdirSync(dir, { recursive: true });
    return { file: await dl(r[0].url, dir, 's.jpg'), note: r[0].provider };
  });
  await rec('fetchVisualsForScene(video)', 'video', async () => {
    const r: any = await fetchVisualsForScene(['waterfall nature'], true, 'portrait');
    if (!r) return { note: 'null' };
    const url = Array.isArray(r) ? r[0]?.downloadUrl || r[0]?.url : (r.downloadUrl || r.url);
    if (!url) return { note: 'no url' };
    const dir = path.join(OUT, 'fvs'); fs.mkdirSync(dir, { recursive: true });
    return { file: await dl(url, dir, 'fvs.mp4'), note: r.title || '' };
  });

  // FREE CC
  await rec('free-image(wiki/archive/nasa/met)', 'image', async () => {
    const r = await freeImageAdapter.searchBest('city', { count: 5 });
    if (!r || !r.downloadUrl) return { note: 'empty' };
    const dir = path.join(OUT, 'free-img'); fs.mkdirSync(dir, { recursive: true });
    return { file: await dl(r.downloadUrl, dir, 'free.jpg'), note: r.provider };
  });
  await rec('free-video(wiki/archive)', 'video', async () => {
    const a = new FreeVideoAdapter();
    const r = await a.searchAndDownloadFirst('nature forest', path.join(OUT, 'free-vid'), 'portrait');
    return r && r.localPath ? { file: r.localPath, note: r.title || '' } : { file: null, note: 'no file' };
  });

  // TABLE
  console.log('\n=== DOWNLOAD SOURCE TEST RESULTS ===');
  console.log('source                         media   status  bytes      note');
  for (const row of rows) {
    console.log(row.source.padEnd(30), row.media.padEnd(7), row.status.padEnd(7), String(row.bytes).padEnd(10), row.note);
  }
  const pass = rows.filter((r) => r.status === 'PASS').length;
  console.log(`\nPASS: ${pass}/${rows.length}`);
})();
