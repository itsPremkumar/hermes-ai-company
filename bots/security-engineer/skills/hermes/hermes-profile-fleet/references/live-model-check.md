# Live Model Check (MANDATORY before assigning any model to a profile)

Config writes (`✓ Set model.default=…`) succeed even when the model is dead.
A dead model only fails at chat time with `HTTP 404: Model 'X' not found` or
`Billing or credits exhausted`. Always verify liveness FIRST.

## Step 1 — find which providers have a REAL (uncommented) key

```bash
grep -rE "^OPENROUTER_API_KEY=[A-Za-z0-9_-]{20,}" ~/AppData/Local/hermes/profiles/*/.env
grep -rE "^NVIDIA_API_KEY=" ~/AppData/Local/hermes/profiles/*/.env
```
- A line starting with `# OPENROUTER_API_KEY=` is COMMENTED OUT → counts as absent.
- Each profile `.env` is isolated; a key in `bunny/.env` is NOT inherited by `ceo/.env`.

## Step 2 — enumerate live models per provider

Use Python (NOT bash `curl | python3` — python3 is missing on this Windows host).
Load the key from a source `.env` so you have a real value.

```python
import os, urllib.request, json
env = {}
for line in open(r"C:\Users\PREM KUMAR\AppData\Local\hermes\profiles\bunny\.env", encoding="utf-8", errors="ignore"):
    line=line.strip()
    if line and not line.startswith("#") and "=" in line:
        k,v=line.split("=",1); env[k.strip()]=v.strip().strip('"').strip("'")

# OpenRouter (serves free NVIDIA/Cohere/Poolside models)
or_key = env.get("OPENROUTER_API_KEY","")
req=urllib.request.Request("https://openrouter.ai/api/v1/models",
                          headers={"Authorization":f"Bearer {or_key}"})
data=json.load(urllib.request.urlopen(req, timeout=25))
free=[m["id"] for m in data.get("data",[]) if ":free" in m["id"]]
print("OpenRouter free:", free)

# NVIDIA NIM (check for 0-free reality)
nv=env.get("NVIDIA_API_KEY","")
req2=urllib.request.Request("https://integrate.api.nvidia.com/v1/models",
                           headers={"Authorization":f"Bearer {nv}"})
d2=json.load(urllib.request.urlopen(req2, timeout=25))
print("NVIDIA total:", len(d2.get("data",[])), "free:", [m["id"] for m in d2.get("data",[]) if "free" in m["id"].lower()])
```

## Step 3 — map picker/tier names → catalog IDs

The Bot-Mode picker shows DISPLAY + TIER names, e.g. `Hy3:Free`, `Longcat 2.0:Free`,
`Laguna S 2.1:Free`. These are NOT model IDs. The catalog/base IDs are:
- `Hy3:Free`        → `tencent/hy3`        (may be PAID on Nous Portal)
- `Longcat 2.0:Free`→ `meituan/longcat-2.0` (PAID — $0 credits → 404 billing)
- `Laguna S 2.1:Free`→ `poolside/laguna-s-2.1` (free on OpenRouter: `poolside/laguna-s-2.1:free`)
- `Step 3.7 Flash:Free`→ `stepfun/step-3.7-flash`
- `Solar Pro4:Free`→ `?/solar-pro4`

Rule: the `:Free` suffix in the UI is a TIER LABEL. The real free ID on OpenRouter is
`<provider>/<base>-free`. On Nous Portal, the free tier is routed by the base ID but
requires account credits — verify with a live chat, not assumption.

## Step 4 — only assign IDs that appeared in Step 2's `free` list

If the model isn't in the live free list, it will 404. Don't guess from blogs/screenshots.

## Step 5 — live-test after assigning
```bash
hermes chat -q "Reply with just: OK" -p <profile> -Q 2>&1 | tail -3
```
A `✓ Set model.default` line is NOT proof. Only a real reply (or a clean 404) is.
