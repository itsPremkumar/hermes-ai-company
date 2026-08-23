// brace-depth.cjs — verify TS brace balance after an edit to a deeply nested
// try/for block. tsc reports "'catch' expected" / "'try' expected" FAR from the
// real problem; this finds the exact line where depth first goes negative.
//
// Usage:  node bin/brace-depth.cjs <path-to-ts-file> [fromLine] [toLine]
const fs = require('fs');
const p = process.argv[2];
const from = parseInt(process.argv[3] || '1', 10);
const to = parseInt(process.argv[4] || '1e9', 10);
const lines = fs.readFileSync(p, 'utf8').split('\n');
let depth = 0, lineNo = 0, firstNeg = -1;
for (const raw of lines) {
    lineNo++;
    if (lineNo < from || lineNo > to) continue;
    // strip line comments (rough; template-string `}` inside comments can false-positive — ignore those)
    let line = raw.replace(/\/\/.*$/, '');
    for (const c of line) {
        if (c === '{') depth++;
        else if (c === '}') depth--;
    }
    if (depth < 0 && firstNeg === -1) { firstNeg = lineNo; }
    if (/[{}]/.test(raw)) console.log(`${lineNo}: depth=${depth}  ${raw.trim().slice(0, 50)}`);
}
console.log('FIRST NEGATIVE at', firstNeg, '| FINAL depth', depth);
