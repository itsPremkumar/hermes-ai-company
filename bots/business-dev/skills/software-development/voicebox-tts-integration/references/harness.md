# Voicebox multi-scenario verification harness

Pattern: exercise EVERY voice path the pipeline can use, against a live backend,
write one WAV per scenario, assert each is a valid RIFF file. Proves the
integration end-to-end without a full video render.

## Scenarios to cover
- A1 Kokoro preset `af_heart` (warm female narrator) — engine `kokoro`
- A2 Kokoro preset `am_adam`  (male narrator)            — engine `kokoro`
- A3 Kokoro preset `af_bella` (bright female)            — engine `kokoro`
- B  Chatterbox-Turbo clone (user's voice)               — engine `chatterbox_turbo`
  (B is a `cloned` profile; upload a 10-30s reference clip + verbatim transcript
   via `POST /profiles/{id}/samples` first. Until then it's a placeholder clone.)

## Flow per scenario
```
POST /speak {text, profile:<id>, engine}  -> {id}
poll GET /generate/{id}/status (SSE `data: {...}`) until status in
     {completed, complete, done} or error (cap ~120 * 3s)
GET /audio/{id} -> Buffer -> write <label>.wav
assert buf[0:4] == 'RIFF' and len > 1000
```

## Prereqs
- Backend running (see SKILL.md launch cmd, port 17493, `env PYTHONPATH=`).
- Profiles created via `POST /profiles` (preset + cloned) before the run.
- Pull live profile ids from `GET /profiles` so the script never hardcodes stale UUIDs.

## Reference-clip upload (clone)
```
curl -X POST http://127.0.0.1:17493/profiles/<CLONE_ID>/samples \
  -F "file=@your-voice.wav" \
  -F "reference_text=verbatim transcript of the clip"
```
Or the bundled `scripts/setup-voicebox-clone.mjs <clip.wav> "<transcript>"`
(which creates the cloned profile, uploads the sample, writes `.env`).

## Pass criterion
4/4 scenarios produce valid audio. If a scenario fails, the backend log
(`backend_run.log`) shows the real cause (missing import, CUDA OOM, model
download in progress — wait for the ~4GB Chatterbox-Turbo first-load download).
