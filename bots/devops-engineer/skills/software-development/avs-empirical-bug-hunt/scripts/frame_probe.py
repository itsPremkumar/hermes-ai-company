#!/usr/bin/env python3
"""
frame_probe.py — empirical feature-correctness probe for AVS final videos
(used when vision_analyze is unavailable). Extracts a frame at each given
timestamp via ffmpeg (INPUT seek: -ss AFTER -i) as 160x90 rgb24 rawvideo,
then reports per-frame: avg luma, warm-yellow caption %, near-white %, and
saturated-% (emoji/color). Prints "<-TEXT" when caption glyphs are detected.

Usage:  python workspace/tmp/frame_probe.py <video.mp4> [t1 t2 t3 ...]
Authoritative QA gate is still scripts/avs-verify.sh; this is the targeted
"did the filter / overlay actually burn?" companion (see G30).
"""
import subprocess, sys

FF = 'node_modules/ffmpeg-static/ffmpeg.exe'

def probe(video, t, w=160, h=90):
    raw = subprocess.check_output(
        [FF, '-v', 'error', '-ss', str(t), '-i', video, '-frames:v', '1',
         '-vf', f'scale={w}:{h}', '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-'],
        stderr=subprocess.DEVNULL)
    n = len(raw) // 3
    r = raw[0::3]; g = raw[1::3]; b = raw[2::3]
    luma = sum(max(r[i], g[i], b[i]) for i in range(n)) / n
    yellow = sum(1 for i in range(n) if r[i] > 150 and g[i] > 120 and b[i] < 150)
    white = sum(1 for i in range(n) if r[i] > 200 and g[i] > 200 and b[i] > 200)
    sat = 0
    for i in range(n):
        mx = max(r[i], g[i], b[i]); mn = min(r[i], g[i], b[i])
        if mx > 120 and (mx - mn) > 60:
            sat += 1
    return {
        'luma': round(luma, 1),
        'yellow%': round(yellow / n * 100, 3),
        'white%': round(white / n * 100, 3),
        'saturated%': round(sat / n * 100, 3),
    }

video = sys.argv[1]
times = [float(x) for x in sys.argv[2:]] or [0.5, 2, 5, 8, 9.5]
for t in times:
    p = probe(video, t)
    print(f't={t:5.1f}s luma={p["luma"]:5.1f} yellow%={p["yellow%"]:6.3f} white%={p["white%"]:6.3f} sat%={p["saturated%"]:5.2f}'
          + ('  <-TEXT' if p['yellow%'] > 1 or p['white%'] > 1 else ''))
