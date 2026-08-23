# Provider Registry Pattern — Reference

Full worked example from the music-system architecture built for
`itsPremkumar/Automated-Video-Generator`.

## Architecture sketch

```
Engine → Registry → [Provider, Provider, ...]
                        ↓
                  search(query) in parallel
                        ↓
                  best result → download → process → resolve
```

## Registry

```typescript
class ProviderRegistry {
    private providers = new Map<string, MusicProvider>();

    register(provider: MusicProvider): void {
        this.providers.set(provider.name, provider);
    }

    /** Return providers sorted by priority (lowest number = highest priority) */
    getAll(): MusicProvider[] {
        return [...this.providers.values()].sort((a, b) => a.priority - b.priority);
    }

    listNames(): string[] { return [...this.providers.keys()]; }

    get size(): number { return this.providers.size; }
}

export const globalRegistry = new ProviderRegistry();
```

## Provider interface

```typescript
interface MusicProvider {
    readonly name: string;
    readonly label: string;
    readonly priority: number;       // 1 = highest, 99 = lowest
    readonly requiresNetwork: boolean;

    search(query: MusicQuery, count?: number): Promise<MusicTrack[]>;
    download(track: MusicTrack, destPath: string): Promise<string>;
}
```

## Engine (orchestrator)

```typescript
async resolveBackground(opts: { topic: string }): Promise<ResolvedMusic | null> {
    const query = buildMusicQuery(opts);
    const allProviders = this.registry.getAll();

    // Fire all providers in parallel
    const results = await Promise.allSettled(
        allProviders.map(p => this.searchProvider(p, query))
    );

    // Pick the best result (highest priority that returned tracks)
    for (const provider of allProviders) {
        const tracks = this.cache.get(provider.name, query);
        if (tracks.length > 0) {
            return this.downloadAndProcess(tracks[0], provider, query);
        }
    }
    return null;  // fallback to procedural
}
```

## ccMixter API quirks (free CC-licensed music, no key)

### Search
- **Endpoint:** `GET https://ccmixter.org/api/query?limit=N&tags=TAGS&f=json`
- **Tags use AND semantics** — comma-separated tags must ALL match.
  Too many tags (5+) returns empty `[]`. Limit to **2-3 broad tags**.
- **Mood-to-tag mapping** (broad, not specific):
  | Mood | Tags |
  |------|------|
  | calm | `ambient` |
  | upbeat | `dance` |
  | dramatic | `cinematic` |
  | professional | `ambient` |
  | nostalgic | `jazz,lofi` |
  | dark | `ambient,dark` |
- Optional: add ONE topic keyword if length > 3 and not already in tags.

### Download
- **Requires `Referer: https://ccmixter.org/` header.** Without it the server
  returns 403 Forbidden (Apache hotlink protection).
- Also set `Accept: audio/mpeg,*/*` for clean content negotiation.
- **Timeout:** ccMixter is slow (3-6s per request). Set 15s timeout.
- Download URL pattern: `https://ccmixter.org/content/{USER}/{FILENAME}`

### Response format
```json
[{
    "upload_id": 71027,
    "upload_name": "New Age Whale",
    "user_name": "ArtistName",
    "license_url": "https://creativecommons.org/licenses/by-nc/4.0/",
    "files": [{
        "download_url": "https://ccmixter.org/content/User/Song.mp3",
        "file_format_info": { "ps": "5:52" },
        "file_filesize": " (13.43MB)"
    }]
}]
```

### Pitfalls
- First `files[0]` is usually the main mix. Additional files at indexes 1+
  are stems (individual tracks).
- Some tracks are CC-NC (non-commercial) — read `license_url` before using in
  commercial contexts. Prefer `license_url` containing `/by/` (no NC clause).
- The API returns JSON with `,` after last element (non-standard) — axios
  parses it fine but it can trip strict JSON parsers.

## Pixabay API note

Pixabay (`https://pixabay.com/api/docs/`) provides **images and videos only**.
There is NO audio endpoint — `/api/audio/` returns 403. The npm package
`dderevjanik/pixabay-api` wraps `searchImages` and `searchVideos` (not audio).
Do not use Pixabay as a music source.

## Processing pipeline

After download, audio goes through:
1. **Trim** — cut to target duration via `ffmpeg -t` (uses `-c copy`)
2. **Fade** — intro/outto fade via `afade`
3. **Normalize** — EBU R128 loudness via `loudnorm`
4. **Loop** — if source is shorter than target, concatenate copy

**Output format:** Default `.wav` produces 5MB+ files. Switch to `.mp3` for
~80% space savings. When doing so, update ALL processing steps that hardcode
`-c:a pcm_s16le` to conditionally use `libmp3lame` for `.mp3` paths:

```typescript
const args: string[] = [
    '-i', inputPath,
    '-af', filter,
    '-c:a', outputPath.endsWith('.mp3') ? 'libmp3lame' : 'pcm_s16le',
    '-y',
    outputPath,
];
if (outputPath.endsWith('.mp3')) {
    args.splice(6, 0, '-b:a', '192k');  // insert bitrate arg
}
```

Also update engine's cache path from `_processed.wav` → `_processed.mp3`.

## InternetArchive API (public domain audio, free, no key)

### Search
- **Endpoint:** `https://archive.org/advancedsearch.php?q=...&fl[]=identifier&fl[]=title&fl[]=creator&fl[]=licenseurl&fl[]=downloads&sort[]=downloads+desc&rows=N&output=json`
- **Query format:** URL-encoded, spaces as `+`. Add `AND mediatype:audio AND (licenseurl:*)` to filter for licensed audio.
- Returns `response.docs[]` with identifiers and metadata.

### Download URL resolution (CRITICAL)
The naive pattern `https://archive.org/download/{ID}/{ID}.mp3` **often fails**
because IA stores files with arbitrary filenames (not matching the identifier).
**Always resolve via the metadata API:**

```typescript
async function resolveDownloadUrl(identifier: string): Promise<string | null> {
    const meta = await axios.get(`https://archive.org/metadata/${identifier}`);
    const files = meta.data?.files || [];
    const audioFile = files.find((f: any) =>
        (f.name.endsWith('.mp3') || f.name.endsWith('.ogg')) &&
        !f.name.includes('spectrogram') &&
        f.source !== 'original'
    );
    if (audioFile?.name) {
        return `https://archive.org/download/${identifier}/${audioFile.name}`;
    }
    return `https://archive.org/download/${identifier}/${identifier}.mp3`; // fallback
}
```

This adds one extra API call per track (metadata fetch). Acceptable for a
priority-6 fallback that seldom fires.

## OpenLofi (deprecated — all tracks removed upstream)

The `btahir/open-lofi` GitHub repo **deleted all audio files** from the
repository. The `catalog.json` lists 166 track entries but zero MP3/WAV files
exist in the repo tree.

**Verification:**
```
GET https://api.github.com/repos/btahir/open-lofi/git/trees/main?recursive=1
→ 0 audio files (checked via .mp3/wav/ogg/flac/aac extension filter)
```

The provider was removed from the default registry. If the upstream repo
restores tracks in the future, re-add with updated download URL patterns.
The source file `src/music-system/providers/open-lofi.ts` is preserved for
reference but excluded from the build.

## Black frame detection + trim (fixes X10 gate)

Pexels videos frequently have a 0.5-1s fade-in from black. This triggers the
X10 gate check (`blackframe=0.1:30` detecting >0.5s of black). Fix at the
**download stage** (not the gate, which is read-only):

```typescript
function trimBlackFrames(videoPath: string): string {
    // Detect: ffprobe blackframe filter, extract first non-black timestamp
    const detectCmd = `${ffprobe} -v quiet -f lavfi -i "movie=${videoPath},blackframe=0.1:30" -show_entries frame=pkt_pts_time -of csv=p=0`;
    const out = execSync(detectCmd, { timeout: 15000 });
    const times = out.trim().split('\n').map(Number).filter(n => !isNaN(n));
    const firstNonBlack = Math.min(...times) || 0;
    
    if (firstNonBlack > 0.3) {
        // Trim with -ss from first non-black frame, -c copy for speed
        const trimCmd = `${ffmpeg} -i "${videoPath}" -ss ${firstNonBlack.toFixed(2)} -c copy -avoid_negative_ts 1 -y "${trimmedPath}"`;
        execSync(trimCmd, { timeout: 30000 });
        fs.unlinkSync(videoPath);
        fs.renameSync(trimmedPath, videoPath);
    }
    return videoPath;
}
```

Called after every video download succeeds (wrapped in try/catch — non-critical).

## Environment documentation pattern

After changing providers or the system architecture, update both `.env` and
`.env.example` with the current provider chain and any env vars the music
system reads. Document the priority order so operators understand the
fallback chain at a glance. Example section:

```ini
# 🎵 MUSIC SYSTEM (free, no API keys needed)
# ------------------------------------------------------------------------------
# Priority chain:
#   1. bundled    — 5 ambient MP3s shipped with the repo (always works offline)
#   2. local      — tracks you drop in input/bgm/
#   3. ccmixter   — real CC-licensed music, free, no key needed
#   4. internet-archive — public domain audio (free, no key)
#   5. procedural — ffmpeg-generated tones (always works)
#
# Enable/disable (default: true): MUSIC_ENABLED=true
# Cache dir: MUSIC_CACHE_DIR=workspace/cache/free-music
# Provider timeout: MUSIC_PROVIDER_TIMEOUT=15000
# Parallel search: MUSIC_PARALLEL=true
```

## Runtime verification command library

After making code changes, run these to prove the system still works:

```bash
# TypeScript compilation
npm run typecheck

# Full test suite
npm run test:unit            # 506 tests, 0 failures (Wikimedia network tests may fail)

# Specific provider smoke tests
npx tsx -e "
const {CcMixterProvider} = require('./src/music-system/providers/ccmixter');
const p = new CcMixterProvider();
p.search({mood:'calm',topic:'ambient',targetDurationSec:60,minDurationSec:10,role:'background'}).then(t => {
    console.log('ccMixter tracks:', t.length, t.map(x=>x.title));
});
"

# Bundled provider (offline verification)
ls -la input/bgm/__bundled__/

# Full pipeline smoke test
npx tsx bin/agentic-run.ts --topic "test" --title "Test" --orientation landscape --renderer ffmpeg --quality medium --backend agent 2>&1 | tail -20
```
