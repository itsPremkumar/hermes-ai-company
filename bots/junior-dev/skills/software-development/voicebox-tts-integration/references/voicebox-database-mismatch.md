# Voicebox Database Mismatch — Diagnosis & Fix

## Symptom

`POST /speak` returns `{"detail":"Voice profile '<id>' not found."}` despite
SQLite queries showing the profile exists. Or polling the generations table
returns no rows while the generation actually completed.

## Root Cause

Voicebox stores profiles and generations in a SQLite database whose location
depends on the `--data-dir` flag passed at launch:

- **With `--data-dir`:** `{data-dir}/voicebox.db`
- **Without `--data-dir` (default):** `{cwd}/data/voicebox.db`

If you launch the server with `--data-dir C:/one/voicebox/.voicebox-data`, the
database lives at `C:/one/voicebox/.voicebox-data/voicebox.db`.

**But** if you launched without that flag (e.g. via a lifecycle script that
omitted `--data-dir`), the server uses `C:/one/voicebox/data/voicebox.db`.

Profiles created by directly INSERTing into `.voicebox-data/voicebox.db` (via
Python's `sqlite3` module) land in the wrong database and are invisible to the
server.

## Diagnosis Steps

1. **Find the server PID and command line:**
   ```
   netstat -ano | findstr :17493
   wmic process where "processid=<PID>" get commandline /format:list
   ```

2. **Check for `--data-dir` in the command line.** If absent, the default is
   `./data/` relative to the server's working directory.

3. **Identify the server's cwd:**
   ```
   wmic process where "processid=<PID>" get executablepath /format:list
   ```
   Or infer from the cwd of the parent process that spawned it.

4. **Query the correct database:**
   ```python
   import sqlite3
   con = sqlite3.connect('{data-dir}/voicebox.db')  # ← use the actual data-dir
   profiles = con.execute('SELECT id, name, preset_voice_id FROM profiles').fetchall()
   print(profiles)
   ```

## Fix

**Always create profiles via the API, never via SQLite:**  
`POST /profiles` with `{"name","voice_type":"preset","preset_engine":"kokoro","preset_voice_id":"af_heart","default_engine":"kokoro"}`

This guarantees the profile lands in whichever database the server is using.

## Session Trace (from real workflow)

```
# ❌ Wrong: listing profiles from .voicebox-data/ shows the profile exists
$ sqlite3 .voicebox-data/voicebox.db "SELECT id,name FROM profiles"
# → 43dce705-253d-458a-a3a9-3ded6bea6f80 | Narrator (Kokoro Heart)

# ❌ But speak fails because server uses data/voicebox.db instead
$ curl -X POST /speak -d '{"profile":"43dce7...","engine":"kokoro"}'
# → {"detail":"Voice profile '43dce7...' not found."}

# ✅ Check the server's command line — no --data-dir flag
$ wmic process where "processid=19416" get commandline
# → python -m backend.main --host 127.0.0.1 --port 17493  (no --data-dir!)

# ✅ Server uses default: ./data/voicebox.db
$ sqlite3 data/voicebox.db "SELECT id,name FROM profiles"
# → (empty — no profiles here!)

# ✅ Create profile via API
$ curl -X POST /profiles -d '{"name":"Kokoro Heart Demo","voice_type":"preset","preset_engine":"kokoro","preset_voice_id":"af_heart","default_engine":"kokoro"}'
# → {"id":"ce4beb9f-32e0-42dc-87e8-2ca585c5f967",...}

# ✅ Now speak works
$ curl -X POST /speak -d '{"profile":"ce4beb9f-...","engine":"kokoro"}'
# → {"id":"17929942-...","status":"generating"}
```

## Verified Working Profile Reference

| Profile ID | Name | Engine | Kokoro Preset |
|---|---|---|---|
| `ce4beb9f-32e0-42dc-87e8-2ca585c5f967` | Kokoro Heart Demo | kokoro | af_heart |

Use this profile ID for quick Kokoro access:  
`TTS_PROVIDER=voicebox VOICEBOX_PROFILE_ID=ce4beb9f-32e0-42dc-87e8-2ca585c5f967 VOICEBOX_ENGINE=kokoro`
