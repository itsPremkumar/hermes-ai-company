# Live end-to-end download proof (Automated-Video-Generator)

Complement to the offline monkeypatch tests in `media-asset-relevance`. Proves
the real chain `searchAll → download → validate` returns ON-TOPIC media, not
just that the filter logic is correct in isolation.

## Canonical script shape (TypeScript, run via `npx tsx bin/<x>.ts`)

```ts
import path from 'node:path';
import fs from 'node:fs';
import { execFileSync } from 'node:child_process';
import axios from 'axios';
// @ts-ignore  // ffprobe-static ships without type declarations
import ffprobePath from 'ffprobe-static';
import { FreeImageAdapter } from '../src/lib/free-image/adapter.js';
import { FreeVideoAdapter } from '../src/lib/free-video/adapter.js';
import { freeVideoDownloader } from '../src/lib/free-video/index.js';

const UA = { 'User-Agent': 'Mozilla/5.0 (compatible; AVG/1.0)' };
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

const OFF_TOPIC = /(stone\s+lion|sea\s+lion|lion\s+king|lion\s+dance|lioness|nebula|nasa|galaxy|space)/i;
const REAL = /\blion\b/i;
const isRealLion = (t: string) => REAL.test(t) && !OFF_TOPIC.test(t);

const FF = (ffprobePath as any).path || (ffprobePath as unknown as string);
function probe(file: string): { valid: boolean; info: string } {
  try {
    const out = execFileSync(FF, ['-v','error','-show_entries','stream=codec_type,codec_name,width,height,duration','-of','default=noprint_wrappers=1', file], { encoding: 'utf8', timeout: 30000 });
    return { valid: out.trim().length > 0, info: out.trim().replace(/\s+/g,' ') };
  } catch (e: any) { return { valid: false, info: String(e.message).slice(0,100) }; }
}

// Wikimedia throttles shared-IP GET bursts (429/403). Backoff + retry.
async function get(url: string, dest: string): Promise<string> {
  for (let a = 0; a < 4; a++) {
    try {
      const r = await axios.get(url, { responseType: 'arraybuffer', timeout: 60000, headers: UA });
      fs.writeFileSync(dest, Buffer.from(r.data));
      return fs.statSync(dest).size > 500 ? '' : 'too small';
    } catch (e: any) {
      const s = e?.response?.status;
      if ((s === 429 || s === 403) && a < 3) { await sleep(2500 * 2 ** a); continue; }
      return String(s || e.message).slice(0, 80);
    }
  }
  return 'retries exhausted';
}
```

Run, then assert: every returned title is `isRealLion` (metadata gate), and each
downloaded file `probe().valid === true` (byte gate). `offTopic === 0` is the
primary acceptance criterion.

## Findings from the lion run
- `searchAll('lion',{count:10})` returned 7 on-topic IMAGE titles (all
  Wikimedia, all whole-word "lion", zero off-topic compounds) and 4 VIDEO titles
  (2 Wikimedia + 2 Archive). NASA/MetMuseum were NOT queried → domain gate works.
- **ZERO off-topic leakage** at both download and metadata level — filter proven.
- Downloads: Archive.org (lion MyLink animation, ライオン CM) succeeded reliably
  (h264 360p/1080p). Wikimedia images mostly 429'd under sibling-agent shared-IP
  load; two landed (1280×960, 2000×1333 mjpeg). The 429 was a rate-limit, NOT a
  relevance failure — extend throttle/backoff if a higher valid-count is needed.
