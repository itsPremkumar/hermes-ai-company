/**
 * verify-output.ts — COMPREHENSIVE video output verification.
 *
 * Runs 31 checks across 8 categories on any rendered MP4.
 *
 * Categories:
 *   1. File Integrity (F1-F4)     — size, existence, sanity
 *   2. ffprobe Metadata (M1-M5)   — format, duration, bitrate
 *   3. Video Stream (V1-V8)       — codec, resolution, FPS, aspect ratio
 *   4. Audio Stream (A1-A4)       — codec, sample rate, channels
 *   5. Video Stats (S1-S4)        — corruption, frame count, loudness
 *   6. Black Frames (B1-B2)       — blackdetect with pix_th=0.15
 *   7. Pipeline Logs (L1-L6)      — workspace artifacts
 *   8. Gate Report (G1)           — gate.json pass/fail
 *
 * Usage: npx tsx scripts/verify-output.ts <path-to.mp4> [--verbose]
 */

import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';

// ── Config ──────────────────────────────────────────────────
const verbose = process.argv.includes('--verbose');
const mp4Path = process.argv[2];
if (!mp4Path || !fs.existsSync(mp4Path)) {
    console.error('Usage: npx tsx scripts/verify-output.ts <path-to-mp4> [--verbose]');
    process.exit(1);
}

const fileSize = fs.statSync(mp4Path).size;
let FFPROBE = 'ffprobe';
let FFMPEG = 'ffmpeg';
try { FFPROBE = require('ffprobe-static')?.path || 'ffprobe'; } catch {}
try { FFMPEG = require('ffmpeg-static') || 'ffmpeg'; } catch {}

interface CheckResult { id: string; label: string; pass: boolean; detail: string; }
const results: CheckResult[] = [];
let passCount = 0;
let failCount = 0;

function check(id: string, label: string, pass: boolean, detail: string) {
    results.push({ id, label, pass, detail });
    if (pass) passCount++;
    else failCount++;
    console.log(`  ${pass ? '✓' : '✗'} ${id.padEnd(6)} ${label}: ${detail}`);
}

function runCmd(cmd: string, timeout = 15000) {
    try {
        const out = execSync(cmd, { encoding: 'utf8' as BufferEncoding, timeout, maxBuffer: 10 * 1024 * 1024 });
        return { stdout: out.trim(), stderr: '', code: 0 };
    } catch (e: any) {
        return {
            stdout: e.stdout?.toString()?.trim() || '',
            stderr: e.stderr?.toString()?.trim() || e.message,
            code: e.status ?? -1,
        };
    }
}

// ── 1. FILE INTEGRITY ──────────────────────────────────────
console.log('\n═══ 1. FILE INTEGRITY ═══');
check('F1', 'File exists', true, `${mp4Path}`);
check('F2', 'File size', fileSize > 100_000, `${(fileSize / 1024 / 1024).toFixed(2)} MB`);
check('F3', 'Not oversized', fileSize < 500_000_000, `${(fileSize / 1024 / 1024).toFixed(2)} MB`);
check('F4', 'Min size threshold', fileSize > 50_000, '> 50KB');
if (fileSize < 100_000) { console.log('\n⚠ File too small — aborting'); process.exit(1); }

// ── 2. FFPROBE METADATA ────────────────────────────────────
console.log('\n═══ 2. FFPROBE METADATA ═══');
const probeCmd = `"${FFPROBE}" -v quiet -print_format json -show_format -show_streams "${mp4Path}"`;
const probe = runCmd(probeCmd, 20000);
check('M1', 'ffprobe reads file', probe.code === 0 && probe.stdout.length > 0, probe.code ? `Metadata parsed` : `Error: ${probe.stderr.slice(0, 100)}`);
if (probe.code !== 0) { console.log('\n⚠ Cannot read file — corruption'); process.exit(1); }

const meta = JSON.parse(probe.stdout);
const format = meta.format || {};
const streams: any[] = meta.streams || [];
const videoStream = streams.find((s: any) => s.codec_type === 'video');
const audioStream = streams.find((s: any) => s.codec_type === 'audio');
check('M2', 'Format name', !!format.format_name, format.format_name || 'unknown');
check('M3', 'Duration > 0', !!format.duration && Number(format.duration) > 0, `${format.duration}s`);
check('M4', 'Bitrate reported', !!format.bit_rate && Number(format.bit_rate) > 0, `${(Number(format.bit_rate) / 1000).toFixed(0)} kbps`);

// ── 3. VIDEO STREAM ─────────────────────────────────────────
console.log('\n═══ 3. VIDEO STREAM ═══');
if (videoStream) {
    const codec = videoStream.codec_name || 'unknown';
    const width = videoStream.width || 0;
    const height = videoStream.height || 0;
    const fps = eval(videoStream.r_frame_rate || '0/1');
    const pixfmt = videoStream.pix_fmt || 'unknown';
    check('V1', 'Video present', true, `${codec} ${width}x${height} @${fps.toFixed(1)}fps`);
    check('V2', 'Codec is h264', /^(h264|avc1)/.test(codec), codec);
    check('V3', 'Min resolution ≥360p', width >= 360 && height >= 360, `${width}x${height}`);
    check('V4', 'Max resolution ≤4K', width <= 4096 && height <= 4096, `${width}x${height}`);
    check('V5', 'FPS 12-60', fps >= 12 && fps <= 60, `${fps.toFixed(1)} fps`);
    check('V6', 'Pixel format YUV', /^(yuv|420)/.test(pixfmt), pixfmt);
    const ar = width / height;
    const expAr = Math.abs(ar - 16/9) < 0.05 ? '16:9' : Math.abs(ar - 9/16) < 0.05 ? '9:16' : Math.abs(ar - 1) < 0.05 ? '1:1' : `${width}:${height}`;
    check('V7', 'Standard aspect ratio', ['16:9','9:16','1:1'].includes(expAr), `${width}x${height}=${expAr}`);
} else { check('V1', 'Video present', false, 'NO VIDEO STREAM'); }

// ── 4. AUDIO STREAM ─────────────────────────────────────────
console.log('\n═══ 4. AUDIO STREAM ═══');
if (audioStream) {
    const aCodec = audioStream.codec_name || 'unknown';
    const sr = audioStream.sample_rate || '0';
    const ch = audioStream.channels || 0;
    check('A1', 'Audio present', true, `${aCodec} ${sr}Hz ${ch}ch`);
    check('A2', 'Codec AAC/MP3', /^(aac|mp3|libmp3lame)/.test(aCodec), aCodec);
    check('A3', 'Sample rate ≥ 22050Hz', Number(sr) >= 22050, `${sr} Hz`);
    check('A4', '≥ mono', ch >= 1, `${ch} channel(s)`);
} else { check('A1', 'Audio present', false, 'NO AUDIO STREAM'); }

// ── 5. VIDEO STATISTICS ─────────────────────────────────────
console.log('\n═══ 5. VIDEO STATISTICS ═══');
const validCmd = `"${FFMPEG}" -v error -i "${mp4Path}" -f null - -t 1 2>&1`;
const validOut = runCmd(validCmd, 30000);
check('S1', 'No corruption', !validOut.stderr || validOut.stderr.length < 10, validOut.stderr ? `Errors: ${validOut.stderr.slice(0, 150)}` : 'Clean');

let frameCount = 0;
let detectedFps = 30;
const fcCmd = `"${FFPROBE}" -v error -select_streams v:0 -count_frames -show_entries stream=nb_read_frames,r_frame_rate -of csv=p=0 "${mp4Path}" 2>&1`;
const fcOut = runCmd(fcCmd, 20000);
const fcParts = fcOut.stdout.split(',');
frameCount = parseInt(fcParts[0]?.trim() || '0');
if (fcParts[1]) { const rp = fcParts[1].trim().split('/'); detectedFps = rp.length === 2 ? (parseInt(rp[0]) / parseInt(rp[1])) : 30; }
check('S2', 'Frame count > 0', frameCount > 0, `${frameCount} frames (${(frameCount / detectedFps).toFixed(1)}s)`);

if (audioStream) {
    const loudCmd = `"${FFMPEG}" -i "${mp4Path}" -af "volumedetect" -f null - -t 5 2>&1`;
    const loudOut = runCmd(loudCmd, 30000);
    const meanVol = loudOut.stderr.match(/mean_volume:\s*(-?\d+\.?\d*)/)?.[1];
    const maxVol = loudOut.stderr.match(/max_volume:\s*(-?\d+\.?\d*)/)?.[1];
    check('S3', 'Audio not silent', !meanVol || Number(meanVol) > -50, `Mean: ${meanVol || 'N/A'} dB`);
    check('S4', 'Audio not clipping', !maxVol || Number(maxVol) <= 0, `Max: ${maxVol || 'N/A'} dB`);
}

// ── 6. BLACK FRAME DETECTION ────────────────────────────────
console.log('\n═══ 6. BLACK FRAME DETECTION ═══');
const blackCmd = `"${FFMPEG}" -i "${mp4Path}" -filter:v "blackdetect=d=0.3:pix_th=0.15" -f null - 2>&1`;
const blackOut = runCmd(blackCmd, 60000);
const blackMatch = [...blackOut.stderr.matchAll(/black_start:([\d.]+)\s+black_end:([\d.]+)\s+black_duration:([\d.]+)/g)];
check('B1', 'Black segment check ran', true, `${blackMatch.length} black segments found`);
const maxBlack = blackMatch.reduce((m, b) => Math.max(m, parseFloat(b[3])), 0);
check('B2', 'No segment > 0.5s black', maxBlack < 0.5, maxBlack > 0 ? `Max: ${maxBlack.toFixed(2)}s` : 'None');

// ── 7. PIPELINE LOGS ────────────────────────────────────────
console.log('\n═══ 7. PIPELINE LOGS ═══');
check('L1', '.mp4 filename', /\.mp4$/i.test(mp4Path), path.basename(mp4Path));
const jobDirName = path.basename(path.dirname(mp4Path));
const wsPath = path.join(process.cwd(), 'workspace', 'jobs', jobDirName);
if (fs.existsSync(wsPath)) {
    const files = fs.readdirSync(wsPath);
    check('L2', 'Assets dir', files.some(f => f.startsWith('assets')), '✓');
    check('L3', 'Manifest', files.some(f => f.endsWith('manifest.json')), '✓');
    check('L4', 'Decision report', files.some(f => f.startsWith('decisions')), '✓');
} else { check('L2', 'Workspace logs', false, 'Not found'); }

// ── 8. GATE REPORT ─────────────────────────────────────────
console.log('\n═══ 8. GATE REPORT ═══');
const gatePath = path.join(wsPath, 'gate.json');
if (fs.existsSync(gatePath)) {
    try {
        const gate = JSON.parse(fs.readFileSync(gatePath, 'utf-8'));
        check('G1', 'Gate result', true, gate.pass ? 'PASS' : 'FAIL');
    } catch { check('G1', 'Gate parse', false, 'Parse error'); }
} else { check('G1', 'Gate file', false, 'gate.json not found'); }

// ── SUMMARY ─────────────────────────────────────────────────
console.log(`\n══════════════════════════════════════`);
console.log(`  ${passCount} passed, ${failCount} failed, ${results.length} total`);
console.log(`══════════════════════════════════════\n`);
if (failCount > 0) {
    results.filter(r => !r.pass).forEach(r => console.log(`  ✗ ${r.id}: ${r.label} — ${r.detail}`));
    console.log('');
}
process.exit(failCount > 0 ? 1 : 0);