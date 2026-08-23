# Voicebox verification & end-to-end generation recipe (verified live)

These steps were run successfully against a local Voicebox backend on a Windows
RTX 3050 box. Use them when you need to PROVE a voice-clone / TTS generation
actually produced audio, rather than just asserting the API returned 200.

## The two gotchas (why naive polling fails)
1. `GET /generate/{id}/status` is an **SSE stream that holds the connection**.
   A plain `curl` to it returns empty lines and never emits the terminal
   `completed` event, so a `for` loop polling it just times out. Don't rely on it.
2. `GET /audio/{id}` before completion throws
   `RuntimeError: File at path <data-dir> is not a file` because `audio_path`
   is empty and the backend falls back to the data-dir. Only call it once the
   DB says `completed`.

## Reliable status check: query SQLite directly
The backend stores everything in `<data-dir>/voicebox.db` (default
`C:/one/voicebox/.voicebox-data/voicebox.db`). The `generations` table has:
`id, profile_id, text, language, audio_path, duration, engine, model_size,
status, error, ...`. `audio_path` is RELATIVE to the data-dir
(`generations\\<id>.wav`). Status lifecycle: `generating` → (`loading_model`,
optional intermediate for first engine load) → `completed` (or `error`).
Chatterbox-Turbo first load shows `loading_model` for 60-120s.

```bash
# always clear the global PYTHONPATH leak on Windows
cd /c/one/voicebox
env PYTHONPATH= .venv/Scripts/python.exe - <<'PY'
import sqlite3, time
con=sqlite3.connect('.voicebox-data/voicebox.db'); c=con.cursor()
gid='099bcabe-022a-453a-b832-87e81b3598f3'   # the id from POST /speak
for _ in range(40):
    c.execute("SELECT status,audio_path,error FROM generations WHERE id=?", (gid,))
    st,ap,err=c.fetchone()
    if st in ('completed','error'):
        print(st, ap, err); break
    time.sleep(3)
con.close()
PY
```

## Full flow (what actually worked)
1. Start backend (background):
   ```bash
   cd /c/one/voicebox
   env PYTHONPATH= .venv/Scripts/python.exe -m backend.main \
     --host 127.0.0.1 --port 17493 --data-dir C:/one/voicebox/.voicebox-data
   ```
2. Confirm ready: `curl -s http://127.0.0.1:17493/models/status` (look for
   `GPU: CUDA ...` in the startup log; `torch.cuda.is_available()` must be True).
3. `POST /speak` with `{"text","profile":<id>,"engine":"chatterbox_turbo","language":"en"}`
   → capture `id`.
4. Poll the SQLite DB (above) until `status='completed'`. First Chatterbox-Turbo
   load downloads ~4GB and is slow — normal.
5. Retrieve audio: `cp .voicebox-data/generations/<id>.wav <out.wav>` (or
   `GET /audio/<id>` once completed).
6. Verify WAV: `wave.open(out)` → channels/rate/frames; a real clone is
   mono 24kHz. (Chatterbox-Turbo output was 24kHz mono, ~10.9s for a ~25-word line.)

## Re-usable generator
`scripts/generate_clone.py` does steps 3–6 in one shot (stdlib only: urllib +
sqlite3 + wave, no extra deps). Run it with the voicebox `.venv` python against a
running backend.
