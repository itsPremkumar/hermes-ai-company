#!/usr/bin/env python3
import os, re, json

base = r"C:\Users\PREM KUMAR\AppData\Local\hermes\profiles"
skip = {"jarvis", "bunny", "premthedev"}

profiles = []
for p in sorted(os.listdir(base)):
    if p in skip:
        continue
    cfg_path = os.path.join(base, p, "config.yaml")
    soul_path = os.path.join(base, p, "SOUL.md")
    if not os.path.exists(cfg_path):
        continue
    with open(cfg_path, encoding="utf-8", errors="ignore") as f:
        cfg = f.read()
    m = re.search(r"^\s*model:\s*\n\s*default:\s*(.+)", cfg, re.M)
    if m:
        model = m.group(1).strip().strip('"').strip("'")
    else:
        m2 = re.search(r"^\s*model:\s*(.+)", cfg, re.M)
        model = m2.group(1).strip().strip('"').strip("'") if m2 else "-"
    soul = "-"
    if os.path.exists(soul_path):
        with open(soul_path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                h = re.match(r"^#\s+(.+)", line)
                if h:
                    soul = h.group(1).strip()
                    break
    profiles.append({"name": p, "model": model, "soul": soul})

print(f"Total: {len(profiles)}")
for p in profiles:
    print(f"  {p['name']:<22} | model={p['model'][:40]:<40} | soul={p['soul'][:35]}")

fleet = {"profiles": []}
for p in profiles:
    fleet["profiles"].append({
        "name": p["name"],
        "model": p["model"],
        "soul": p["soul"],
    })
out = r"C:\one\hermes-ai-company\configs\FLEET.json"
with open(out, "w") as f:
    json.dump(fleet, f, indent=2)
print(f"\nFLEET.json -> {out} ({len(fleet['profiles'])} entries)")
