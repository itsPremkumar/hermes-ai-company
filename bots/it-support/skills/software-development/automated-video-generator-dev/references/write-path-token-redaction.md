# AVS Write-Path Secret Redaction Trap

## Symptom
The `patch` / `write_file` tools REDACT strings that look like auth tokens /
secrets **at write time** — even when your edit does NOT touch the token line.
Observed 2026-08-11 in `src/agentic/delivery/publish.ts`:

- Original source (hex-confirmed via `git show 4118b5c:...` blob):
  `-H "Authorization: Bearer $YOUTUBE_ACCESS_TOKEN" ...`
- After a `patch` edit to a *neighboring* line, the on-disk file contained:
  `-H "Authorization: Bearer $YOUTU...OKEN" ...`  <- invalid shell, breaks the script

This is the SAME trap that stalled the other Hermes session
(`@session:default/20260811_183937_b64ec1`) for 25+ messages - it mistook the
redaction for real repo content and "reverted" valid code into literal `*** `.

## Why it is insidious
- The redaction shows up in ANY output that echoes source: reads, diffs, session
  logs (you see `Bearer *** ` or `$YOUTU...OKEN`).
- It can be introduced by an edit to a NEIGHBORING line, not just the token
  line - the whole-file write pass re-redacts every secret-shaped string.
- `git diff` / `grep` DISPLAY is also redacted, so a textual check is useless.

## Verify (byte-proof - never trust text grep)
```
python -c "
s=open('src/agentic/delivery/publish.ts',encoding='utf-8').read()
for l in s.split('\n'):
    if 'Authorization' in l:
        print('BYTES='+l[25:55].encode().hex())
"
# compare against the git blob:
python -c "
import subprocess
blob=subprocess.run(['git','show','4118b5c:src/agentic/delivery/publish.ts'],capture_output=True).stdout
print('ORIG_BYTES='+[l for l in blob.decode().split('\n') if 'Authorization' in l][0][25:55].encode().hex())
"
```
- `$YOUTUBE_ACCESS_TOKEN` = `59 72 20 24 59 4f 55 54 55 42 45 5f 41 43 43 45 53 53 5f 54 4f 4b 45 4e`
- `$YOUTU...OKEN`        = `59 72 20 24 59 4f 55 54 55 2e 2e 2e 4f 4b 45 4e`
If the two hex strings differ -> redaction occurred.

## Fix (bypass the redacting write path)
Do NOT re-run `patch` - it redacts again. Use a raw Python byte write (Python
file I/O does not redact):
```
python -c "
p='src/agentic/delivery/publish.ts'
s=open(p,encoding='utf-8').read()
s=s.replace('YOUTU...OKEN','YOUTUBE_ACCESS_TOKEN')
open(p,'w',encoding='utf-8',newline='').write(s)
"
```
Then re-run the hex verify above - `ORIG_BYTES == BYTES` confirms the fix.

## Affected token-shaped strings in AVS
`YOUTUBE_ACCESS_TOKEN`, `TIKTOK_ACCESS_TOKEN`, `INSTAGRAM_ACCESS_TOKEN` (all in
`publish.ts` upload-helper scripts). Any `$XXX_...TOKEN` / `Bearer ...` / `_KEY`
/ `secret` / `apiKey` string written through the edit tools is at risk.

## Rule
When editing any file containing `Authorization` / `Bearer` / `_TOKEN` /
`secret` / `apiKey`, verify the token strings **byte-for-byte with the hex
method AFTER every edit**, never by text grep.
