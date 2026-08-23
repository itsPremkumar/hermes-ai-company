# Repro recipe: reliable grep/list on Windows MSYS paths

The agent `search_files` tool throws `os error 3` on `/c/one/...` paths even
when the file exists. Use this `execute_code` pattern instead.

## Grep a file (single file)
```python
import subprocess
out = subprocess.run(
    ["rg", "-n", "PATTERN", "-n", "C:/one/Project/src/path/file.ts"],
    capture_output=True, text=True)
print(out.stdout.strip() or "(MISSING)")
```

## Grep across a dir, several symbols
```python
checks = {
  "src/agentic/orchestrator/ffmpeg.ts": ["estimateAudioDurationSafe"],
  "src/lib/captions.ts": ["syllableWordTimings", "writeCaptionSidecars"],
}
for fn, syms in checks.items():
    p = f"C:/one/Project/{fn}"
    r = subprocess.run(
        ["rg", "-n", "export (async )?(function|const) (" + "|".join(syms) + r")\b", "-n", p],
        capture_output=True, text=True)
    print(f"=== {fn} ===\n{r.stdout.strip()}\n")
```

## List a directory + existence check
```python
import os
d = "C:/one/Project/src/agentic/operations"
for f in sorted(os.listdir(d)):
    print(f)
print("exists:", os.path.exists("C:/one/Project/src/agentic/operations/slideshow.ts"))
```

## Read a JS/TS export signature block
```python
import subprocess
r = subprocess.run(
    ["rg", "-n", "^export (async )?function", "-n",
     "C:/one/Project/src/agentic/operations/image-video.ts"],
    capture_output=True, text=True)
print(r.stdout.strip())
```

## Note
- Always use the `C:/one/...` (drive-letter) form inside `subprocess`, never the
  `/c/one/...` MSYS form — ripgrep resolves the former reliably here.
- The false `TS6053: File not found` from `patch`/`read_file` lint is unrelated
  and must be ignored; confirm with `npm run typecheck` in `terminal`.
