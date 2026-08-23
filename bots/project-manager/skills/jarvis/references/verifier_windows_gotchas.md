# Verifier Windows Path Gotchas (real bugs, fixed in prems-jarvis-hermes)

## 1. `os.path.exists` lies on space-truncated paths
Naive verifier: `path = text[text.index("exists at")+8:].split()[0]`.
On `C:\Users\PREM KUMAR\AppData\...\spec.md with a price or offer`
→ path becomes `C:\Users\PREM`.
`os.path.exists("C:/Users/PREM")` returns **True** on Windows (the prefix
resolves to an existing directory), so the gate PASSES on a NON-EXISTENT file.

FIX: never split a path at whitespace. Separate path from the content clause
at the FIRST keyword `with`/`containing`/`contains`:
```python
m = re.search(r"exists\s+at\s+(.+)$", text, re.I)
tail = m.group(1)
kw = re.search(r"\s+(?:with|containing|contains)\s+", tail, re.I)
path = tail[:kw.start()] if kw else tail
clause = tail[kw.end():] if kw else None
```
A quoted path (`'C:\Users\PREM KUMAR\file.txt'`) is also handled.

## 2. Content-clause verification (boolean)
`file exists at <path> with a price or offer` → verifier reads the FILE and
applies: `or`=any token, `and`=all tokens, `/`=any token; strip filler
(a/an/the). So a worker must satisfy the content, not just create the file.
Test: `tests/test_verifier.py::test_verify_content_clause`.

## 3. Stray `./nul` from MSYS `cmd //c`
`cmd //c "C:\...\jarvis_loop.cmd >nul 2>&1"` can create a literal `nul` file in
cwd. `git add` then fails: "short read while indexing nul / failed to insert
into database". Fix: `rm -f ./nul` before `git add`; avoid `>nul` (use
`> /dev/null 2>&1` or no redirect).
