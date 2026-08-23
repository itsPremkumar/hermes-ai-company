# Screenshot OCR fallback (when vision_analyze is unavailable)

## When to use
- Active model is text-only (e.g. DeepSeek) → `vision_analyze` returns
  400 `unknown variant 'image_url', expected 'text'` for ANY image, even after
  resize/convert. This is a provider limitation, not a corrupt image.
- User pastes a screenshot (GSC verification page, DNS panel, error dialog,
  terminal capture) and you must read the text from it.

## Recipe (verified 2026-08-04)
```bash
pip install rapidocr-onnxruntime -q
```
Downscale large images first (ffmpeg is usually present; ~75KB PNGs at full
res can still be read, but halving helps):
```bash
ffmpeg -y -i screenshot.png -vf "scale=iw*0.5:ih*0.5" -q:v 4 small.jpg
```
Read it:
```bash
python -c "
from rapidocr_onnxruntime import RapidOCR
result, _ = RapidOCR()('small.jpg')
for line in (result or []):
    print(line[1])
"
```
Result lines are `[text, confidence, bbox]` — print index 1 for the text.
No GPU, no PyTorch, no internet needed after install (~tens of MB).

## Critical caveat
OCR can DROP characters (esp. long base64-ish tokens). For anything that
must be EXACT — GSC `google-site-verification=<token>` TXT values, API keys,
verification codes — never trust OCR verbatim. Have the user paste the exact
copied value and compare (or diff) against the OCR output before acting on it.
In the 2026-08-04 GSC session, the OCR'd TXT value was plausibly complete but
the correct flow was: user clicks COPY in GSC → pastes here → agent compares
→ user adds record in DNS panel → agent verifies via `nslookup -type=TXT`.
