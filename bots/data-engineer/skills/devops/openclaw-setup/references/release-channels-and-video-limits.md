# OpenClaw release channels & the video-generation reality (verified 2026-07-31)

## Release channels (npm dist-tags, queried 2026-07-31)

```bash
npm view openclaw dist-tags --json
```

| Channel | Version | Meaning |
|---|---|---|
| `alpha` | 2026.5.19-alpha.1 | experimental |
| `beta` | 2026.7.2-beta.5 | pre-release |
| `latest` | 2026.7.1-2 | **default install; what this host runs** |
| `extended-stable` | 2026.6.33 | long-lived, monthly-cut channel (YYYY.M.33 base + backports) |

### Extended-stable (announced 2026-07-30 blog: "On the Road to LTS")
- Long-lived channel with backported security/reliability fixes; one cut per
  month; supported ≥1 month until the next cut. First: 2026.6.33 (based on
  2026.6.11). Stepping stone toward official LTS.
- **It is a DOWNGRADE in feature terms** — built on an OLD base line with
  fixes backported. `latest` (2026.7.1-2) is newer AND contains those fixes.
- For a solo dev on a personal box, `latest` is correct. Pin to
  `extended-stable` ONLY if `latest` breaks a 24/7 production workload:
  ```bash
  npm install -g openclaw@extended-stable
  openclaw update --channel extended-stable
  ```
- Maturity scorecard: public feature inventory scored on quality+completeness
  (GitHub issues, service comparisons, human judgment). Mature features get a
  priority label + >90% E2E test coverage goal. Treat scores as directional —
  "human judgment" is in the formula.

## Video generation: OpenClaw CANNOT do it without a provider key

- `openclaw capability list` advertises `video.generate`, `video.describe`,
  `video.providers` — but there is NO `openclaw video` CLI subcommand
  ("Unknown command: openclaw video"). Video is agent-tool-only.
- With no video provider key configured (Runway/Replicate-class), the agent
  replies honestly: `VIDEO_GEN_UNAVAILABLE — No video generation skill or tool
  is configured in the current environment.`
- **Division of labor (honest):** OpenClaw = reasoning + Telegram delivery;
  Hermes = actual media production + persistence. Do not promise the user an
  OpenClaw-generated video; generate it with Hermes/ffmpeg instead.

### Local ffmpeg sample-video recipe that works on this 6GB-RAM box
Use `h264_mf` (not libx264) — RAM-safe on this host (see memory notes).
```bash
ffmpeg -y -f lavfi -i "testsrc2=size=640x360:rate=24:duration=6" \
  -f lavfi -i "sine=frequency=440:duration=6" \
  -vf "drawtext=text='OpenClaw Sample Video - generated via Hermes':fontsize=20:fontcolor=white:x=(w-text_w)/2:y=h-40" \
  -c:v h264_mf -preset veryfast -b:v 800k -c:a aac -shortest sample_video.mp4
# verify: ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height
```
