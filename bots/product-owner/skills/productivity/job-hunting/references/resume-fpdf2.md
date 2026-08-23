# Resume PDF generation without LaTeX (this Windows host)

No `pdflatex` / `xelatex` / `pandoc` / `pdftoppm` / `gs` available. Use `fpdf2` for code-generated PDFs (resumes, reports).

## Install
```bash
python -m pip install fpdf2 pymupdf
```
(`pymupdf` for render/verify. pip can be slow on this host — run in background if needed.)

## Builder pattern (resume)
```python
from fpdf import FPDF
pdf = FPDF(format="A4")
pdf.set_auto_page_break(auto=True, margin=15)
pdf.set_margins(16, 14, 16)
pdf.add_page()
pdf.set_font("Helvetica", "B", 20)
pdf.cell(0, 9, "Premkumar M", align="C", ln=1)
pdf.set_font("Helvetica", "", 8.5)
pdf.cell(0, 5, "email | phone | github | linkedin", align="C", ln=1)
pdf.ln(3)
# section header w/ blue rule:
def h1(t):
    pdf.set_font("Helvetica", "B", 13); pdf.set_text_color(0, 90, 160)
    pdf.cell(0, 7, t); pdf.ln(1.5)
    y = pdf.get_y(); pdf.set_draw_color(0, 90, 160); pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y); pdf.ln(2.5)
    pdf.set_text_color(20, 20, 20)
# body via pdf.multi_cell(0, 4.8, text); bullets via cell(4,4.6,"-") + multi_cell
pdf.output(r"C:\path\to\out.pdf")
```
Use latin-1-safe text only (no emoji / → / ★ — spell "stars" / "->"). `ln=` is deprecated but harmless.

## Verify (do ALL three)
1. **Page count:** `fitz.open(p).page_count` == expected (1 for one-pager).
2. **Content present:** fpdf2 zlib-compresses text, so a raw byte scan of the PDF shows MISS even when content exists. Decompress to confirm:
```python
import zlib, re
data=open(path,'rb').read()
for m in re.finditer(rb'stream\r?\n(.*?)\r?\nendstream',data,re.S):
    try: d=zlib.decompress(m.group(1))
    except Exception: continue
    if b'Premkumar' in d: print('FOUND')
```
3. **Visual:** `fitz.open(path)[0].get_pixmap(dpi=130).save('preview.png')` then `vision_analyze`.
   **Pitfall:** vision can misread a single digit (phone `93455` read as `93435`). Confirm critical IDs against source data / decompressed text, NOT only the image.

## Honesty rules for the resume
- Lead with VERIFIED flagships (stars, live URLs, OSCG mentor). Back every claim with repo evidence.
- Do NOT invent traffic/"daily users" you can't verify — phrase as "deployed and operated in production."
- Curate to 2–5 repos; don't dump 100.
- Bundle Resume + Portfolio + Proof-of-work in the reply; foreground AVS + Sproutern + OSCG 2026 Mentor.

## Working example
`C:\Users\PREM KUMAR\job-readiness\build_resume_pdf.py` → `RESUME_Premkumar_2026.pdf`
(generated for the Open Source Connect volunteer submission). Copy/modify for future tasks.
