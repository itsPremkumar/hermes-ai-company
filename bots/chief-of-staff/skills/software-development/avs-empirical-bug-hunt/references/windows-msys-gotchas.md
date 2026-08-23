# Windows / MSYS tooling gotchas (AVS environment)

These cost real debugging time this session. Encode them so future sessions skip
the blind alleys.

## read_file on absolute MSYS paths intermittently fails
`read_file(path=/c/one/Automated-Video-Generator/src/...)` sometimes returns
"system cannot find the path specified. (os error 3)" even though the file
exists. WORKAROUND: use `search_files` with the RELATIVE path
(`src/agentic/operations/edit.ts`) or run `terminal` `grep -n` with the quoted
path. Do not conclude the file is missing — re-try via search_files.

## .mjs is ESM — `require is not defined`
In a `.mjs` repro, `require(...)` throws. Use:
```js
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const ffmpeg = require('ffmpeg-static');
```

## patch can emit a false `error TS6053: file not found`
When patching a source file, the auto syntax-check sometimes reports
`error TS6053: File '.../src/...ts' not found` for the very file being edited.
This is a pre-existing/false positive from the check running before the file is
resolved — IGNORE it; verify with a real `npm run typecheck` afterward.

## Importing an absolute Windows path dynamically
`import('C:/one/.../foo.js')` throws `ERR_UNSUPPORTED_ESM_URL_SCHEME`. Use:
```js
import { pathToFileURL } from 'url';
await import(pathToFileURL('C:/one/.../foo.js').href);
```

## Running a .ts/.mts repro
`node --import tsx workspace/bug-hunt/repro.mts` (NOT `node repro.mts` — that
fails on TS syntax / ESM require).

## /tmp path quirk in shell
`/tmp/...` under MSYS sometimes fails for ffmpeg output ("No such file or
directory" on an existing dir). Use a repo-relative path under
`workspace/bug-hunt/` or `process.env.TEMP` via node `os.tmpdir()`.

## terminal runs git-bash/MSYS
Use POSIX syntax (`ls`, `$VAR`, single quotes). PowerShell builtins don't work.
MSYS-style paths (`/c/Users/...`) and native (`C:\Users\...`) both resolve.
