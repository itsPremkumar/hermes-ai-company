/**
 * async_ffmpeg_probe.cjs — reusable ffmpeg/ffprobe runner that CANNOT hang.
 *
 * Why this exists: on a RAM-starved box (e.g. ~6 GB / ~100 MB free),
 * `execFileSync(ffmpeg, …)` / `spawnSync(ffmpeg, …)` blocks the Node
 * event loop PERMANENTLY. The fork/spawn syscall hits EAGAIN and the calling
 * thread never returns, so the JS `{ timeout }` option can't fire (the timer
 * lives on the same blocked thread). The process hangs forever with no error,
 * no stack — looks identical to a "legit slow render."
 *
 * The fix: async `spawn` + a `setTimeout` that SIGKILLs the child and
 * resolves -1. Copy this shape into any hot-path ffmpeg call you convert
 * from sync. Drop it in %TEMP% (Windows) or /tmp (*nix), run, then delete.
 *
 * Usage (from terminal, quick probe):
 *   node async_ffmpeg_probe.cjs <media-file>
 * Prints Duration (s), max_volume dB, width x height, codec — from stderr
 * written to a temp file (NOT swallowed by 2>/dev/null), async + timeout.
 */
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

function ffmpegBin() {
  try { return require('ffmpeg-static'); } catch { return 'ffmpeg'; }
}
function ffprobeBin() {
  try { return require('ffprobe-static'); } catch { return 'ffprobe'; }
}

/**
 * Run an ffmpeg/ffprobe command asynchronously with a hard timeout kill.
 * Resolves to { code, stdout, stderr, timedOut? }. On timeout: kills child, code = -1.
 */
function run(args, bin, timeoutMs = 60000) {
  return new Promise((resolve) => {
    const child = spawn(bin, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    let out = '', err = '';
    child.stdout.on('data', (d) => (out += d));
    child.stderr.on('data', (d) => (err += d));
    const t = setTimeout(() => {
      try { child.kill('SIGKILL'); } catch {}
      resolve({ code: -1, stdout: out, stderr: err, timedOut: true });
    }, timeoutMs);
    child.on('error', (e) => { clearTimeout(t); resolve({ code: -1, stdout: out, stderr: err + '\n' + e.message }); });
    child.on('close', (code) => { clearTimeout(t); resolve({ code: code ?? -1, stdout: out, stderr: err }); });
  });
}

async function probe(file) {
  // ffprobe JSON is the safe, parseable path for dimensions/codec/duration.
  const p = await run(
    ['-v', 'error', '-show_format', '-show_streams', '-of', 'json', file],
    ffprobeBin()
  );
  if (p.code !== 0) {
    console.error('ffprobe failed:', p.stderr.slice(0, 500));
    return;
  }
  const meta = JSON.parse(p.stdout);
  const dur = parseFloat(meta.format && meta.format.duration) || 0;
  const vid = (meta.streams || []).find((s) => s.codec_type === 'video') || {};
  const aud = (meta.streams || []).find((s) => s.codec_type === 'audio') || {};
  console.log('Duration(s):', dur.toFixed(2));
  console.log('Video:', (vid.width || '?') + 'x' + (vid.height || '?'), vid.codec_name || '?');
  console.log('Audio:', aud.codec_name ? 'present (' + aud.codec_name + ')' : 'NONE');

  // volumedetect MUST read stderr (it prints there). Write to a file, never 2>/dev/null.
  const tmp = path.join(os.tmpdir(), 'ffvol-' + Date.now() + '.txt');
  const v = await run(['-i', file, '-af', 'volumedetect', '-f', 'null', '-'], ffmpegBin());
  fs.writeFileSync(tmp, v.stderr);
  const m = v.stderr.match(/max_volume:\s*(-?[\d.]+)\s*dB/);
  console.log('max_volume:', m ? m[1] + ' dB' : 'n/a (no audio stream?)');
  fs.unlinkSync(tmp);
}

if (require.main === module) {
  const f = process.argv[2];
  if (!f) { console.error('usage: node async_ffmpeg_probe.cjs <file>'); process.exit(2); }
  probe(f).catch((e) => { console.error(e); process.exit(1); });
}

module.exports = { run, probe, ffmpegBin, ffprobeBin };
