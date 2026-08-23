// source-audit probe template — copy, edit imports/assertions, run: npx tsx probe.ts
// Purpose: RUNTIME-VERIFY a suspected bug instead of asserting it from reading.
// Delete the file when done (never leave probe*.ts in the repo).

// 1) Import the ACTUAL function under test (use .js extension for tsx ESM):
import { FreeImageAdapter } from './src/lib/free-image/adapter.js';
import { isSafeUrl } from './src/lib/net-safety.js';

// 2) Assert expected vs actual; print both so the result is self-evident:
const r1 = FreeImageAdapter.isOnTopic('lion', 'Lions in the wild');
console.log('lion vs "Lions in the wild" =>', r1, '(expected true)');

console.log('[::ffff:127.0.0.1] =>', JSON.stringify(isSafeUrl('http://[::ffff:127.0.0.1]/x')));
console.log('[::1] =>', JSON.stringify(isSafeUrl('http://[::1]/x')));

// 3) For SSRF/URL guards, also test the vectors the guard claims to cover:
//    loopback, link-local/metadata 169.254.169.254, RFC1918, .internal/.local,
//    and the IPv4-mapped IPv6 form the dotted-decimal check misses.
