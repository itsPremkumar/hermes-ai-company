# Internet Archive Audio Provider Integration

## Search API

```
GET https://archive.org/advancedsearch.php
  ?q=ambient AND mediatype:audio AND (licenseurl:*)
  &fl[]=identifier&fl[]=title&fl[]=creator&fl[]=licenseurl&fl[]=downloads
  &sort[]=downloads+desc&rows=5&output=json
```

## Download URL Resolution (Two-Step)

**Step 1:** Get metadata for an identifier:
```
GET https://archive.org/metadata/{identifier}
```

**Step 2:** Find the first playable audio file from the `files` array:
```json
{
  "files": [
    { "name": "some-track-listen.mp3", "format": "VBR MP3", "source": "original" },
    { "name": "some-track_spectrogram.png", "format": "PNG" }
  ]
}
```

Filter rules:
- Extension must be `.mp3` or `.ogg`
- Exclude `source: "original"` (raw upload, often huge)
- Exclude filenames with `spectrogram` / `_spectrogram`
- Exclude `.zip` archives

## Download URL Pattern

```
https://archive.org/download/{identifier}/{actual-filename.mp3}
```

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| No results | License filter too restrictive | Drop `(licenseurl:*)` condition |
| 404 download | Wrong filename pattern | Must use metadata API to resolve |
| Slow responses | IA servers can be slow | Use 15s timeout |
