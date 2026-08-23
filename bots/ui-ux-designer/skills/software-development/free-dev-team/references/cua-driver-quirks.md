# cua-driver real API quirks (Windows, v0.7.1)

Discovered 2026-07-16 while building `computer-agent` (drive the laptop's apps
for free asset generation). These are the gotchas that break a naive wrapper —
capture them so the next session doesn't re-debug them.

## 1. `get_desktop_state` returns BASE64 PNG, not a file path
The tool's `data` is a **dict** with keys:
`platform, screen_height, screen_width, screenshot_height, screenshot_width,
screenshot_mime_type, screenshot_png_b64`. It does NOT return a path.

**Wrong:** writing the dict to `desktop.png` → corrupt file.
**Right:**
```python
import base64
d = r["data"]
png_path = os.path.join(workspace, "desktop.png")
with open(png_path, "wb") as f:
    f.write(base64.b64decode(d["screenshot_png_b64"]))
```

## 2. Full-display capture needs `set_config capture_scope=desktop` FIRST
`get_desktop_state` with `capture_scope:"desktop"` fails with:
`"get_desktop_state requires capture_scope=\"desktop\" (current scope is \"window\")"`.
Call once before screenshotting:
```python
_call("set_config", {"capture_scope": "desktop"}, timeout=20)
```
This also enables window-less screen-absolute `click(x,y)` / `scroll(x,y)`.

## 3. `list_apps` returns `{"apps": [...]}` (a dict, not a list)
```python
data = r.get("data", [])
if isinstance(data, dict):
    apps = data.get("apps", [])
else:
    apps = data if isinstance(data, list) else []
```
Each app entry has `name`, `pid`, sometimes `bundle_id`. 328 apps discovered on
this box (Chrome, Edge, Clipchamp, Notepad, etc.).

## 4. Available tools (verified `list-tools` output)
`bring_to_front, check_permissions, click, double_click, drag, end_session,
get_accessibility_tree, get_agent_cursor_state, get_config, get_cursor_position,
get_desktop_state, get_recording_state, get_screen_size, get_window_state,
hotkey, kill_app, launch_app, list_apps, list_windows, move_cursor, press_key,
right_click, scroll, set_agent_cursor_enabled, start_recording, stop_recording, ...`

Key ones for asset generation:
- `get_desktop_state` — screenshot (base64, see #1)
- `launch_app` — launch hidden (`hidden:true` → SW_SHOWNOACTIVATE, no focus steal)
- `click/scroll/type/press_key/hotkey` — drive any app
- `start_recording` / `stop_recording` — trajectory/screen recording (needs ffmpeg
  installed via `install_ffmpeg`; on this box `recording: disabled` by default, so
  prefer ffmpeg `gdigrab` directly for video capture — see below)

## 5. Screen RECORDING: driver's recorder is off → use ffmpeg gdigrab
`cua-driver recording` reports `Recording: disabled`. Rather than enable it,
record the desktop with the already-present ffmpeg-static:
```python
subprocess.Popen([
    ffmpeg, "-y", "-f", "gdigrab", "-framerate", "10", "-i", "desktop",
    "-t", str(seconds), "-pix_fmt", "yuv420p", "-c:v", "libx264",
    "-preset", "ultrafast", out_path,
])
```
Verified: produces a valid 1920×1080 H.264 MP4 (8s, ~232 KB).

## 6. The agent "sees" via the model's NATIVE vision, not a separate API
`computer_use` capture + `vision_analyze` (auxiliary model) may 403 (out of
credits). The agent's OWN multimodal vision on the captured PNG works fine.
User instruction: "use your model to see the image" → rely on native vision,
don't wire a separate vision API. The capture itself always works.

## 7. No GPU / no Blender on this box
Local AI image/video gen (SDXL/ComfyUI/AnimateDiff) is NOT viable (no GPU, 6GB
RAM). User directive: drop Blender; drive the **Chrome browser** (installed at
`C:\Program Files\Google\Chrome\Application\chrome.exe`) to free HF Spaces /
browser tools for advanced generation. This is the free advanced-asset path.
