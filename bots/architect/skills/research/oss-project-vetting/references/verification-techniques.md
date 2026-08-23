# Verification Techniques & Environment Workarounds

## 1. License check (GitHub API)
```bash
curl -s https://api.github.com/repos/OWNER/REPO | python -c "import sys,json;d=json.load(sys.stdin);print((d.get('license') or {}).get('spdx_id'))"
```
- `python3` is MISSING on this Windows box; use `python` (3.11.15).
- `NOASSERTION` / missing → fetch raw LICENSE and READ it. Non-commercial clauses
  hide here (Fish Speech).

## 2. Maintenance + size (GitHub API)
```bash
curl -s https://api.github.com/repos/OWNER/REPO | python -c "import sys,json;d=json.load(sys.stdin);print('lic',(d.get('license') or {}).get('spdx_id'),'| stars',d.get('stargazers_count'),'| pushed',d.get('pushed_at'))"
```

## 3. Model weights size (HuggingFace API)
```bash
curl -s "https://huggingface.co/api/models/OWNER/REPO/tree/main?recursive=true" | python -c "
import sys,json
d=json.load(sys.stdin)
tot=0
for f in d:
    if isinstance(f,dict) and f.get('path','').endswith(('.safetensors','.bin','.pt')):
        sz=f.get('size')
        if isinstance(sz,int): tot+=sz
print('%.2f GB'%(tot/1024**3))
"
```
- Some repos 401 (gated, e.g. resemble-ai/chatterbox needs HF login). Note as
  "gated" — a friction point for automation.
- Single-file size: `curl -sL "<resolve>/file" -o /dev/null -w "%{size_download}"`.

## 4. Capability verification (read SOURCE, not README)
- Clone or shallow-clone the repo, then grep the inference backend:
  `reference`, `voice_prompt`, `clone`, `speaker_embedding`, `prefill`,
  `from_pretrained`, `hf_hub_download`, `snapshot_download`, `requests.`, `api_key`.
- Absence of cloud HTTP in the engine backend = verified local.
- Presence of offline-patch (e.g. `hf_offline_patch.py`) = models fetched at
  runtime, NOT bundled.

## 5. Windows git-bash disk sizing WORKAROUND (critical)
`du -sh` on large trees TIMES OUT (60s) and MSYS path quirks make
`os.path.isdir('/c/one/X')` return False inside Python when the dir exists.
FIX — use a Python script FILE (not `-c` heredoc; raw-string quoting breaks) with
WINDOWS-style paths:
```python
import os
def size(p, depth=0, maxdepth=6):
    tot=0
    try:
        for e in os.scandir(p):
            try:
                if e.is_file(): tot+=e.stat().st_size
                elif depth<maxdepth: tot+=size(e.path, depth+1, maxdepth)
            except: pass
    except: pass
    return tot
base=r'C:\one\\'   # NOTE: raw string + escaped backslash
for d in ['sproutern','voicebox',...]:
    p=base+d
    print(d, '%.2f GB'%(size(p)/1024**3) if os.path.isdir(p) else 'MISSING')
```
- Write via write_file (avoids heredoc quoting), run `python script.py`.
- `robocopy /L` and `dir /s` parsing via cmd//c also failed (quoting). Python is reliable.
- `rm -rf` on multi-GB node_modules TAKES >60s and the foreground call TIMES OUT
  (but the rm still completes). Run big deletes with background=true +
  notify_on_complete=true, then poll/wait.

## 6. Repo cleanup safety rules (used on this user's machine)
- PROTECT (never delete): active project `Automated-Video-Generator`,
  `Hermes-Full-Autonomous-Company`, `paperclip-company`, `clawhub-repos`,
  and `voicebox` (jamiepine — the recommended voice engine, easy to mistake for
  the unrelated Microsoft VibeVoice).
- DELETE only explicitly-named dead repos (user named `sproutern`,
  `sproutern-cloudflar` → freed ~6.17 GB) + confirmed VibeVoice clones.
- Do NOT delete HuggingFace cache (`~/.cache/huggingface`) wholesale — it holds
  Qwen3-TTS etc. that are needed; only prune if user confirms.
- Always report disk free before/after via `wmic.exe LogicalDisk where
  "DeviceID='C:'" get FreeSpace /Value`.
