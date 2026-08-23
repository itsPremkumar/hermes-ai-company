# Windows git-bash Diagnostics (disk / RAM / processes)

Standard Linux disk/RAM tools misbehave under the MSYS git-bash on this Windows box.
These workarounds were validated during a session that needed to free disk and RAM.

## Measuring directory size (the `du -sh` problem)
- `du -sh /c/one/*` **times out** on large trees (deep node_modules, many repos).
- `robocopy SRC NULL /L /S /BYTES` and `cmd /c "dir /s"` quoting breaks in MSYS.
- PowerShell `Get-Process | Select @{...}` fails (parser errors from MSYS quoting).

**Fix: Python `os.scandir` recursive walk.** Write a small `.py` and run `python file.py`.
Critical: use **Windows-style paths** inside Python (`C:\\one\\...`). MSYS `/c/one`
does NOT resolve in Python `os.path` on this machine (returns False for `os.path.isdir`).

```python
import os
def size(p, depth=0, maxdepth=8):
    tot = 0
    try:
        for e in os.scandir(p):
            try:
                if e.is_file(): tot += e.stat().st_size
                elif depth < maxdepth: tot += size(e.path, depth+1, maxdepth)
            except Exception: pass
    except Exception: pass
    return tot
base = "C:\\one\\"
for d in ["sproutern", "Automated-Video-Generator", "voicebox"]:
    p = base + d
    print(d, round(size(p)/1024**3, 2), "GB") if os.path.isdir(p) else print(d, "MISSING")
```

## Listing RAM consumers
`tasklist /FO CSV /NH` works. Parse with Python `csv` and sort by the 5th column
(working set in KB):
```python
import csv, sys
rows=[]
for line in sys.stdin:
    r=next(csv.reader([line]))
    if len(r)>=5: rows.append((int(r[4].replace(',','').replace(' K','')), r[0], r[1]))
rows.sort(reverse=True)
for mem,name,pid in rows[:20]: print(f"{name:28} {mem/1024:6.1f} MB")
```

## Killing processes
- **Correct:** `taskkill /PID <n> /F` (single slash).
- **Wrong:** `taskkill //PID <n> /F` — MSYS mangles `//` and the kill silently no-ops
  (reports "already gone" while the process stays alive).
- **Windows auto-restart:** killing `SearchHost.exe`, `StartMenuExperienceHost.exe`,
  `erl.exe` causes Windows to respawn them with NEW PIDs. They cannot be permanently
  freed without disabling services. Don't expect lasting RAM gain from them.

## Disk free
`wmic.exe LogicalDisk where "DeviceID='C:'" get FreeSpace /Value` -> bytes free.
(Note: box reports ~6.14 GB TotalVisibleMemorySize though user calls it "8 GB" —
the rest is shared GPU memory, not usable RAM.)

## Big safe disk hogs found & cleared (example)
User Temp `AppData\Local\Temp` (24 GB), `uv` cache (7 GB), `pip` cache (4 GB),
`huggingface/hub` (7 GB, but may hold wanted models), Windows `SoftwareDistribution\Download`.
Temp had a few files locked by the OS ("Device or resource busy") — those are skipped,
rest deletes fine. Delete the obvious junk first; treat HuggingFace hub as
"keep unless confirmed unwanted" (may hold a needed model like Qwen3-TTS).
