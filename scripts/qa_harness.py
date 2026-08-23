#!/usr/bin/env python3
"""Generic QA harness - works on ANY project directory without prior setup.

Usage: python qa_harness.py <project_dir>

Checks (each independent, failures accumulate):
  1. COMPILE   - py_compile every .py (skips venv/node_modules/.git)
  2. TESTS     - discovers pytest/test_*.py/self-test subcommands and RUNS them
  3. SECRETS   - scans for hardcoded keys/tokens (sk-..., ghp_..., AKIA...)
  4. DOCS      - README.md or SKILL.md exists

Exit 0 = PASS, exit 1 = FAIL (with per-check detail printed).
"""
import os, re, subprocess, sys, py_compile

SKIP_DIRS = {"venv", ".venv", "node_modules", "__pycache__", ".git", "dist", "build"}
SECRET_PAT = re.compile(r"(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})")

def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            yield os.path.join(dirpath, f)

def main():
    if len(sys.argv) < 2:
        print("usage: qa_harness.py <project_dir>"); return 1
    root = os.path.abspath(sys.argv[1])
    if not os.path.isdir(root):
        print(f"FAIL: not a directory: {root}"); return 1

    results, failed = [], False
    pys = [f for f in walk(root) if f.endswith(".py")]

    # 1. compile
    bad = []
    for f in pys:
        try: py_compile.compile(f, doraise=True)
        except Exception as e: bad.append(f"{os.path.relpath(f, root)}: {e}")
    ok = not bad; failed |= not ok
    results.append(("COMPILE", ok, f"{len(pys)} files checked" + (f"; {len(bad)} broken" if bad else "")))

    # 2a. pytest / test files
    tests = [f for f in pys if os.path.basename(f).startswith("test_") or "/tests/" in f.replace("\\", "/")]
    tr = None
    if tests:
        tr = subprocess.run([sys.executable, "-m", "pytest", "-x", "-q", root],
                            capture_output=True, text=True, timeout=300)
        ok = tr.returncode == 0; failed |= not ok
        tail = (tr.stdout or "").strip().splitlines()[-1:] or ["no output"]
        results.append(("PYTEST", ok, tail[0][:120]))
    else:
        results.append(("PYTEST", True, "no test files found (skipped)"))

    # 2b. self-test subcommands
    ran = 0
    for f in pys:
        try:
            src = open(f, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        if '"self-test"' in src or "'self-test'" in src:
            r = subprocess.run([sys.executable, f, "self-test"], capture_output=True,
                               text=True, timeout=120)
            ran += 1
            ok = r.returncode == 0; failed |= not ok
            results.append((f"SELFTEST {os.path.basename(os.path.dirname(f))}/{os.path.basename(f)}",
                            ok, (r.stdout or r.stderr).strip().splitlines()[-1][:120] if (r.stdout or r.stderr) else "silent"))
    if ran == 0:
        results.append(("SELFTEST", True, "none declared (skipped)"))

    # 3. secrets
    hits = []
    for f in walk(root):
        if f.endswith((".py", ".md", ".yaml", ".yml", ".json", ".txt", ".sh", ".bat")):
            try: src = open(f, encoding="utf-8", errors="ignore").read()
            except Exception: continue
            m = SECRET_PAT.search(src)
            if m: hits.append(f"{os.path.relpath(f, root)}: {m.group(0)[:12]}...")
    ok = not hits; failed |= not ok
    results.append(("SECRETS", ok, "clean" if ok else "; ".join(hits[:3])))

    # 4. docs
    has_docs = any(os.path.exists(os.path.join(root, d)) for d in ("README.md", "SKILL.md", "readme.md"))
    results.append(("DOCS", has_docs, "found" if has_docs else "missing README/SKILL"))
    failed |= not has_docs

    width = max(len(n) for n, _, _ in results)
    print(f"\nQA HARNESS: {root}")
    for n, ok, detail in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {n.ljust(width)}  {detail}")
    verdict = "PASS ✅" if not failed else "FAIL ❌"
    print(f"\nVERDICT: {verdict}")
    return 0 if not failed else 1

if __name__ == "__main__":
    sys.exit(main())
