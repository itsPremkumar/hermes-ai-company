# Procedural ffmpeg Audio Recipes

Generated audio via ffmpeg `-f lavfi` for always-available fallback music.

## Profile 1: Ambient Pad (calm, relaxing)

Layers: C major chord (3 sine waves + octave) → mix → lowpass → tremolo → phaser → echo → limiter

```bash
ffmpeg \
  -f lavfi -i "sine=f=261.63:d=60" \     # C4
  -f lavfi -i "sine=f=329.63:d=60" \     # E4
  -f lavfi -i "sine=f=392.00:d=60" \     # G4
  -f lavfi -i "sine=f=523.25:d=60,volume=0.3" \  # C5
  -filter_complex "
    [0:a][1:a][2:a][3:a]amix=inputs=4:duration=longest:normalize=0[mixed];
    [mixed]volume=0.12[quiet];
    [quiet]lowpass=f=800[low];
    [low]tremolo=f=0.3:d=0.6[trem];
    [trem]aphaser=type=triangular:decay=0.7:delay=5[phased];
    [phased]aecho=0.8:0.7:40|120:0.4|0.2[echo];
    [echo]alimiter=limit=0.5:asc=1:level=disabled[out]
  " -map "[out]" -ac 1 -ar 44100 output.wav
```

## Profile 2: Upbeat (energetic, workout)

Layers: Sawtooth bass → C major chord → lowpass → compressor → mix → limiter

```bash
ffmpeg \
  -f lavfi -i "sawtooth=f=130.81:d=60" \           # C3 bass
  -f lavfi -i "sine=f=261.63:d=60" \               # C4
  -f lavfi -i "sine=f=329.63:d=60,volume=0.5" \    # E4
  -f lavfi -i "sine=f=392.00:d=60,volume=0.5" \    # G4
  -filter_complex "
    [0:a]volume=0.08,lowpass=f=200[bass];
    [1:a][2:a][3:a]amix=inputs=3:duration=longest:normalize=0[chord];
    [chord]volume=0.1,lowpass=f=4000[chordf];
    [chordf]acompressor=threshold=0.1:ratio=4:attack=5:release=50[chordc];
    [bass][chordc]amix=inputs=2:duration=longest:normalize=0[mix];
    [mix]alimiter=limit=0.6:asc=1:level=disabled[out]
  " -map "[out]" -ac 1 -ar 44100 output.wav
```

## Profile 3: Cinematic (emotional, epic)

Layers: Sub-bass + octave → string pad with echo → volume swell (4s fade-in) → pink noise texture → limiter

```bash
ffmpeg \
  -f lavfi -i "sine=f=65.41:d=60,volume=0.15" \    # C2 sub-bass
  -f lavfi -i "sine=f=261.63:d=60" \               # C4
  -f lavfi -i "sine=f=329.63:d=60" \               # E4
  -f lavfi -i "sine=f=392.00:d=60" \               # G4
  -f lavfi -i "anoisesrc=color=pink:duration=60,volume=0.03" \  # pink texture
  -filter_complex "
    [2:a][3:a]amix=inputs=2:duration=longest:normalize=0[strings];
    [strings]volume=0.08,aecho=0.8:0.7:60:0.3[stringspad];
    [0:a][1:a]amix=inputs=2:duration=longest:normalize=0[base];
    [base]volume=0.06[basev];
    [basev][stringspad]amix=inputs=2:duration=longest:normalize=0[mix];
    [mix]volume=0.15:eval=frame:enable='gte(t,0)',volume=0.15*min(t/4,1):eval=frame:enable='lt(t,4)'[swell];
    [swell][4:a]amix=inputs=2:duration=longest:normalize=1[noise];
    [noise]alimiter=limit=0.55:asc=1:level=disabled[out]
  " -map "[out]" -ac 1 -ar 44100 output.wav
```

## Utility Commands

### Audio Probe
```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 input.mp3
```

### Audio Trim
```bash
ffmpeg -i input.mp3 -t 30 -c copy output.mp3
```

### EBU R128 Loudness Normalization
```bash
ffmpeg -i input.mp3 -af "loudnorm=I=-23:LRA=7:TP=-2" output.wav
```

### Intro/Outro Fade
```bash
ffmpeg -i input.mp3 -af "afade=t=in:st=0:d=2,afade=t=out:st=28:d=2" output.wav
```

### Seamless Loop
```bash
# Loop entire input 3 times, trim to 120s
ffmpeg -i input.mp3 -filter_complex "aloop=loop=3:size=0,atrim=0:120" output.wav
```

## ffmpeg Audio Filter Reference

| Filter | Purpose | Example |
|--------|---------|---------|
| `sine=f=261.63:d=60` | Generate sine wave (frequency Hz, duration s) | `sine=f=440:d=10` = 440Hz A4 for 10s |
| `sawtooth=f=130.81:d=60` | Sawtooth wave (rich harmonics) | Good for bass |
| `anoisesrc=color=pink:d=60` | Colored noise (pink/white/brown) | Texture layer |
| `volume=0.12` | Adjust gain | `volume=-6dB` or `volume=0.5` (linear) |
| `lowpass=f=800` | High-frequency cut | Smoothing |
| `highpass=f=80` | Low-frequency rumble removal | Clean bass |
| `tremolo=f=0.3:d=0.6` | Amplitude modulation (f=rate Hz, d=depth 0-1) | Gentle movement |
| `aphaser=type=triangular:decay=0.7:delay=5` | Phaser effect | Space/wobble |
| `aecho=0.8:0.7:40:0.4` | Echo (delay ms, decay) | Multi-tap: `40\|120:0.4\|0.2` |
| `acompressor=threshold=0.1:ratio=4` | Dynamic range compression | Smoothing peaks |
| `alimiter=limit=0.5:asc=1:level=disabled` | Brickwall limiter | Prevent clipping |
| `amix=inputs=4:duration=longest:normalize=0` | Mix multiple audio streams | Layering |
| `afade=t=in:st=0:d=2` | Fade in/out | `t=in` or `t=out` |
| `loudnorm=I=-23:LRA=7:TP=-2` | EBU R128 loudness normalization | Broadcast standard |
| `aloop=loop=3:size=0` | Loop audio N times | `size=0` = loop entire input |
| `atrim=0:30` | Trim to duration | First 30 seconds |

## Mood → Profile Mapping

| Mood | Profile | Musical Character |
|------|---------|-------------------|
| `calm` | ambient | Soft C major pad, lowpass, tremolo |
| `upbeat` | upbeat | Sawtooth bass, compressed chord |
| `dramatic` | cinematic | Sub-bass, string pad, volume swell |
| `professional` | cinematic | Cinematic without the swell |
| `nostalgic` | ambient | Ambient with more reverb |
| `dark` | cinematic | Cinematic with pink noise dominance |
| `any` | ambient | Safe default |

## Implementation Notes

- Always compute `duration = ceil(targetDurationSec)` for ffmpeg lavfi inputs
- The `enable='gte(t,0)'` expression in cinematic profile creates a 4s fade-in via `volume=0.15*min(t/4,1)`
- All profiles output mono at 44100Hz (`-ac 1 -ar 44100`)
- The `alimiter` at the end prevents any clipping
- Cache generated files by hash = `${mood}_${duration}_${profile}` — reuse on next run
