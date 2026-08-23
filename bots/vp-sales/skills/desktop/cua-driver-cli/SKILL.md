---
name: cua-driver-cli
description: |
  Drive the user's desktop by shelling out to the raw `cua-driver` CLI
  (`cua-driver call <tool> [json-args]`) from Python/Node scripts — instead of
  the Hermes-side `computer_use` actions. Use when you build an agent/script
  that automates the desktop headlessly (screenshots, clicks, typing, launching
  apps, browser-driven asset generation, screen recording). Covers the verified
  raw API contract and the non-obvious gotchas that break naive wrappers.
version: 1.0.0
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [computer-use, cua-driver, desktop-automation, cli, scripting]
    category: desktop
    related_skills: [computer-use]
---

# cua-driver CLI (script-driven desktop automation)

The Hermes `computer_use` skill documents the high-level action vocabulary.
This skill covers the **raw `cua-driver` CLI** you call from a script
(`subprocess`, not the `computer_use` tool) to automate the desktop
headlessly. Everything here was exercised live on Windows (cua-driver 0.7.1).

## When to use this (vs the `computer_use` skill)
- You are writing a Python/Node program that must capture the screen / click /
  type without an interactive agent loop.
- You want deterministic, testable desktop automation (e.g. a pytest suite that
  opens a browser, types, and records video).
- You need the agent's "see screen → act" loop embedded in code.

If you just want ad-hoc clicking as the agent, use the `computer-use` skill's
`computer_use` actions instead.

## Binary (Windows)
```
C:\Users\PREM KUMAR\AppData\Local\Programs\Cua\cua-driver\bin\cua-driver.exe
```
`Subcommands: mcp, list-tools, describe, call, serve, stop, status, config,
recording, update, check-update, doctor, diagnose, permissions, autostart,
skills, manifest`.

## Call a tool
```
cua-driver call <tool> [json-args]
cua-driver call get_desktop_state "{\"capture_scope\":\"desktop\"}"
```
Stdout = JSON result. Non-zero exit + stderr on failure.

## CRITICAL GOTCHAS (these cost a real debugging session)
1. **`get_desktop_state` returns BASE64 PNG, not a file path.** The payload is a
   JSON dict with `screenshot_png_b64` (+ `screenshot_mime_type`,
   `screenshot_width/height`). Base64-decode it to get a real image:
   ```python
   import base64, json, subprocess
   out = subprocess.run([CUA,"call","get_desktop_state",
       json.dumps({"capture_scope":"desktop"})],
       capture_output=True, text=True).stdout
   d = json.loads(out)
   png = base64.b64decode(d["screenshot_png_b64"])
   ```
   Writing the dict to a `.png` => CORRUPT file.
2. **Full-display capture needs `set_config capture_scope=desktop` first.**
   `get_desktop_state` with `capture_scope:"desktop"` errors
   "requires capture_scope=desktop (current scope is window)" until you call
   `set_config {"capture_scope":"desktop"}` once. Do it inside the screenshot
   helper so screen-absolute click/scroll also work.
3. **`list_apps` returns `{"apps":[...]}`, not a bare list.** Unwrap:
   `data.get("apps", [])`.
4. **Driver's `start_recording` is OFF by default** (`recording: disabled`).
   Don't depend on it. **Record the screen with ffmpeg `gdigrab`** instead
   (ffmpeg-static has it on Windows):
   ```bash
   ffmpeg -y -f gdigrab -framerate 10 -i desktop -t 8 \
          -pix_fmt yuv420p -c:v libx264 -preset ultrafast out.mp4
   ```
   Verified: 1920x1080, H.264, 10 fps, valid MP4.

## Useful tools (from `list-tools`)
- `get_desktop_state` — full-display screenshot (base64 PNG, see above)
- `get_window_state(pid)` — UIA tree + Markdown of one window
- `get_accessibility_tree` — processes + visible windows w/ bounds
- `list_apps` — installed + running apps (name, pid, active)
- `list_windows` — all top-level windows
- `get_screen_size` — display px + scale factor
- `click {x,y,button,pid?}` / `double_click` / `right_click`
- `scroll {x,y,amount,pid?}`
- `press_key {key,pid?}` / `hotkey {keys,pid?}`  (e.g. `ctrl+l`, `enter`)
- `type {text,pid?}` — types into focused field
- `launch_app {app,hidden}` — launches hidden, no focus steal
- `set_config {capture_scope}` — enable desktop scope

## Browser-driven advanced asset generation
Chrome: `C:\Program Files\Google\Chrome\Application\chrome.exe`
Edge:   `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`
Shotcut:`C:\Program Files\Shotcut\shotcut.exe`
Blender: NOT installed on this box — don't assume it.

Loop: `launch_app`/`os.startfile(url)` → observe (decode base64) → act
(click/type/hotkey) → capture result. The AGENT sees the screenshot via its
own native vision; no separate vision API needed. This is the "computer + AI
agent" advanced-asset path: real AI images via HF Spaces, screenshots of any
app, browser-tool outputs — all free, no GPU, no paid keys.

## Safety
- Refuse `type` of anything matching password/api_key/token/sk-.
- Never click credential/payment dialogs.
- Write outputs to a project `assets/` + `workspace/` dir, never the user's files.

## Cross-reference
The bundled `computer-use` skill owns the Hermes-side `computer_use` action
vocabulary. This skill is the script/CLI complement. See also
`remotion-ffmpeg-video` for ffmpeg `gdigrab` recording and lavfi asset gen.
