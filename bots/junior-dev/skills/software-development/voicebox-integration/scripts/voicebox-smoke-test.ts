/**
 * Voicebox Lifecycle Smoke Test
 * ===============================
 * Drop this into any project to verify Voicebox auto-start, GPU mode, and
 * basic synthesis work. Runs offline (no generation needed).
 *
 * Usage:
 *   // In a Node/TS project with Voicebox lifecycle:
 *   npx tsx path/to/voicebox-smoke-test.ts
 *
 * Expected output:
 *   Backend up? false
 *   ensureBackend() → true  (spawns Voicebox in ~7-15s)
 *   GPU: ✅ CUDA (NVIDIA GeForce RTX 3050 Laptop GPU)
 */
import { ensureBackend, isBackendUp, killBackend } from '../src/lib/voicebox-lifecycle.js';
// Adjust import path to match your project structure.
// For a test file in lib/:    '../src/lib/voicebox-lifecycle.js'
// For a test file in tests/: '../../src/lib/voicebox-lifecycle.js'

async function test() {
    console.log('\n=== VOICEBOX SMOKE TEST ===');
    console.log('1. Checking backend...');
    const up = await isBackendUp();
    console.log('   Backend up?', up);

    if (up) {
        console.log('   (killing for clean test)');
        killBackend();
        await new Promise(r => setTimeout(r, 2000));
    }

    console.log('\n2. Calling ensureBackend()...');
    console.time('spawn');
    const ok = await ensureBackend();
    console.timeEnd('spawn');
    console.log('   Result:', ok);
    if (!ok) process.exit(1);

    console.log('\n3. Health check...');
    try {
        const h = await fetch('http://127.0.0.1:17493/health').then(r => r.json());
        console.log('   GPU:', h.gpu_available ? '✅' : '❌', h.gpu_type || '(none)');
        console.log('   Backend variant:', h.backend_variant);
    } catch {
        console.log('   Health endpoint unreachable');
        process.exit(1);
    }

    console.log('\n=== PASSED ===');
    process.exit(0);
}

test().catch(e => {
    console.error('FAILED:', e.message);
    process.exit(1);
});
