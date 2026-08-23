#!/usr/bin/env python3
"""
generate_clone.py — end-to-end Voicebox TTS/voice-clone generation (stdlib only).

Why this script exists:
  * GET /generate/{id}/status is an SSE stream that HOLDS the connection, so a
    naive `curl` poll never sees the terminal "completed" event.
  * This script polls the backend's SQLite DB (generations.status) instead,
    which is the reliable completion signal, then copies the WAV out.

Usage (run with the voicebox venv python, backend already running):
  env PYTHONPATH= .venv/Scripts/python.exe scripts/generate_clone.py \
      --text "Hello from my cloned voice" \
      --profile 9d484367-edf8-427b-b0b3-1f7a38479229 \
      --engine chatterbox_turbo \
      --data-dir C:/one/voicebox/.voicebox-data \
      --out C:/Users/PREM KUMAR/voice_clone_sample.wav

Dependencies: Python stdlib only (urllib, sqlite3, wave). No pip installs.
"""
import argparse
import json
import os
import sqlite3
import time
import urllib.request
import wave

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 17493


def speak(host, port, text, profile, engine, language="en"):
    url = f"http://{host}:{port}/speak"
    payload = json.dumps(
        {"text": text, "profile": profile, "engine": engine, "language": language}
    ).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.loads(r.read().decode())
    return body["id"]


def wait_for_complete(db_path, gen_id, timeout=240, interval=3):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    deadline = time.time() + timeout
    try:
        while time.time() < deadline:
            cur.execute(
                "SELECT status, audio_path, error FROM generations WHERE id=?",
                (gen_id,),
            )
            row = cur.fetchone()
            if row is None:
                time.sleep(interval)
                continue
            status, audio_path, err = row
            if status == "completed":
                return audio_path
            if status == "error":
                raise RuntimeError(f"generation {gen_id} errored: {err}")
            time.sleep(interval)
    finally:
        con.close()
    raise TimeoutError(f"generation {gen_id} not complete within {timeout}s")


def copy_audio(data_dir, audio_path, out_path):
    src = audio_path
    if not os.path.isabs(src):
        src = os.path.join(data_dir, audio_path)
    with open(src, "rb") as f:
        data = f.read()
    with open(out_path, "wb") as f:
        f.write(data)
    return out_path


def verify_wav(path):
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        rate = w.getframerate()
        return w.getnchannels(), rate, n, n / rate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--profile", required=True, help="cloned or preset profile id")
    ap.add_argument("--engine", default="chatterbox_turbo")
    ap.add_argument("--language", default="en")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--data-dir", required=True, help="Voicebox data dir (has voicebox.db)")
    ap.add_argument("--out", required=True, help="output .wav path")
    args = ap.parse_args()

    db_path = os.path.join(args.data_dir, "voicebox.db")
    print(f"[1] POST /speak (profile={args.profile}, engine={args.engine})")
    gen_id = speak(args.host, args.port, args.text, args.profile, args.engine, args.language)
    print(f"    gen_id={gen_id}")

    print("[2] polling SQLite generations.status ...")
    audio_path = wait_for_complete(db_path, gen_id)
    print(f"    completed, audio_path={audio_path}")

    print(f"[3] copying to {args.out}")
    copy_audio(args.data_dir, audio_path, args.out)

    ch, rate, frames, dur = verify_wav(args.out)
    print(f"[4] verified WAV: channels={ch} rate={rate} frames={frames} dur={dur:.2f}s")
    print(f"DONE -> {args.out}")


if __name__ == "__main__":
    main()
