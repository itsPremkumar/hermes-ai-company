# Vendored Python backend — requirements split (verified-good)

When making a vendored backend self-contained INSIDE the repo (no external
venv), split the deps so the base stays clean + reproducible and the
fragile / unused ones are opt-in.

## Rule (from user correction)
- NEVER overwrite/truncate the canonical `requirements.txt` to "remove unused"
  deps. KEEP the full base; MOVE fragile bits to a separate file with a
  documented command.
- PREFER a FRESH install from the project's OWN declared requirements over
  copying/freezing the external ad-hoc venv (which carries --no-deps hacks,
  git-only deps, --find-links custom indexes → unreproducible on fresh clone).

## Verified split (AVS src/speech/)
`src/speech/requirements.txt` (FULL base, no git-only / --find-links lines):
  fastapi, uvicorn[standard], pydantic
  sqlalchemy, alembic
  torch, transformers (<=4.57.6), accelerate, huggingface_hub, qwen-tts
  kokoro==0.9.4, onnxruntime, soundfile, librosa, scipy, numpy  (DEFAULT zero-config engine = kokoro)
  conformer, diffusers, omegaconf, pykakasi, resemble-perth, s3tokenizer,
  spacy-pkuseg, pyloudnorm   (clone-engine BASE deps)

`src/speech/requirements-clone.txt` (FRAGILE opt-in ONLY):
  --find-links https://k2-fsa.github.io/icefall/piper_phonemize.html
  linacodec @ git+https://github.com/ysharma3501/LinaCodec.git
  Zipvoice @ git+https://github.com/ysharma3501/LuxTTS.git
  + header comment with the install command below.

## Install command (documented in BOTH files + VENDORED.md)
```
cd src && python -m venv ../venv && cd ..
uv pip install --python venv/Scripts/python.exe -r src/speech/requirements.txt
# optional, only if cloning voices:
uv pip install --python venv/Scripts/python.exe -r src/speech/requirements-clone.txt
```
- Match the external venv's Python MINOR (e.g. 3.11) when creating venv,
  or the freeze import fails.
- `venv/` is gitignored (machine-specific, heavy). The code stays in src/speech/ (tracked).

## Gotchas
- A `uv pip install -r requirements.txt` that exits 0 can STILL stop mid-resolve
  and miss a dep (e.g. kokoro never lands). Always confirm:
  `venv/Scripts/python.exe -m pip list | grep -i kokoro` AND a live /speak.
- The default voice engine (kokoro) is NOT in the upstream's "interesting" deps —
  if you split by "what the clone demo uses" you will drop kokoro and the
  zero-config path breaks. KEEP kokoro + its deps in the BASE.
- Only delete the external folder (e.g. C:/one/voicebox) AFTER the in-repo
  venv is verified live (backend boots via in-repo venv, /speak returns bytes).
