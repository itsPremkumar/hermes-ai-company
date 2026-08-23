# Debugging White / Blank Frames in Auto-Generated Videos

When the generated video has **white frames** (blank/empty scenes) for some
scenes but not others, the root cause is usually **wrong search keywords**
that fail to return valid visual assets from Pexels (or whichever image
provider the pipeline uses).

## Diagnostic flow

### 1. Identify which scenes are affected

From the user's description, determine the pattern:
- First scene white, middle scene fine, last scene white → **keyword rotation issue** (different scenes use different keywords, some work, some don't).
- ALL scenes white → **provider failure / network down / API key missing**.
- Intro/outro cards wrong color → **makeCard ffmpeg filter failure**.

### 2. Extract frame thumbnails at scene midpoints

```bash
FF=$(node -e "console.log(require('ffmpeg-static'))")
"$FF" -y -ss <timestamp> -i output/<job>/<video>.mp4 -vframes 1 -q:v 2 -update 1 frame.jpg
```

Check average pixel color with Python PIL:
```python
from PIL import Image
img = Image.open('frame.jpg')
avg = img.resize((1,1)).getpixel((0,0))
print(f'RGB{avg}')  # White = (255,255,255)
```

### 3. Check the scene plan keywords

```bash
cat workspace/jobs/<job_id>/plan.json
```

Inspect `searchKeywords` per scene. If they're **unrelated to the topic**
(e.g. "espresso", "machine" for a Solar System video), this is the root cause.

### 4. Verify downloaded assets

```bash
ls -la workspace/jobs/<job_id>/assets/images/scene_0*/
```

Small files (<10KB) may indicate corrupted images. Valid JPEG starts with
`ffd8` hex header.

### 5. Check the render manifest

```bash
cat workspace/jobs/<job_id>/render-manifest.json
```

`source: "placeholder"` means the Pexels fetch failed. `"pexels"` means a real
image was downloaded (even if it appears white).

## Known root causes

### Hardcoded coffee/espresso keywords in writeScriptHeuristic

**File:** `src/agentic/ai/agent.ts`, `writeScriptHeuristic()` → `angles` array

```typescript
// BAD — hardcoded coffee terms regardless of topic:
const angles = [
    `${kw} cup`,         // "solar cup" — irrelevant
    `espresso machine`,  // ALWAYS espresso
    `barista cafe`,      // ALWAYS barista
    `${kw} beans roast`, // "solar beans roast"
    `latte art`,         // ALWAYS latte
    `${kw} pour over`,   // "solar pour over"
];
```

**Fix:** Generate topic-derived angles:

```typescript
const topicParts = topic.toLowerCase()
    .replace(/[^a-z0-9 ]/g, ' ').split(/\s+/)
    .filter((w) => w.length > 2).slice(0, 4);
const fallback = topicParts.length > 1 ? topicParts : [kw || 'nature'];
const angles = [
    fallback.join(' '),
    `${fallback[0]} ${fallback[fallback.length - 1]}`,
    `${fallback[0]} close up`,
    `${fallback[fallback.length - 1]} nature`,
    `${fallback[0]} cinematic`,
    `beautiful ${fallback[0]}`,
];
```

**Why:** Searching "espresso machine" on a space topic returns coffee photos
(which appear as near-white blanks) or empty results (triggering placeholders).

### Placeholder generation failure

`makePlaceholder()` in `ffmpeg.ts` creates a dark-teal card when Pexels fails.
If ffmpeg itself fails, the card won't exist and the scene renders blank.

Watch pipeline logs for: `⚠ placeholder copy failed for ...`

## Prevention checklist

- [ ] Scene keywords in `plan.json` are topic-relevant
- [ ] Downloaded asset files exist with reasonable sizes
- [ ] Placeholder generation produces colored cards, not white
- [ ] All ffmpeg command args are present (check `render.ts`)
