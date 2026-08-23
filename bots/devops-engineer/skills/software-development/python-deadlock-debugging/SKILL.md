---
name: python-deadlock-debugging
description: "Diagnose and fix Python hangs/deadlocks that freeze a test run or server with no traceback — most commonly a non-reentrant threading.Lock. Use when pytest or a server freezes silently (timeout, no error) and you suspect a lock, not a slow import or network stall."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, python, concurrency, threading, deadlock, pytest, hang]
    related_skills: [systematic-debugging, verify-codebase]
---

# Python Deadlock / Hang Debugging

## Overview

A Python process that **freezes with no traceback** — `pytest` prints a few dots then
hangs until timeout, or a server accepts no connections with no error in the log — is
almost always a **deadlock**, not a slow import or network call. The hardest part is
that the failure is *silent*: no exception, no output, the runner just sits there.

This skill is the focused checklist for that exact symptom. Pair with
`systematic-debugging` for the full root-cause discipline.

## The #1 Cause: non-reentrant `threading.Lock()`

`threading.Lock()` is **NOT reentrant**. If a method takes the lock and then calls
another method on the same object that ALSO takes that same lock, the thread blocks on
itself and never returns:

```python
self._lock = threading.Lock()

def update(self, old, new):
    with self._lock:            # acquires lock
        self.put(new)           # put() does `with self._lock:` -> BLOCKS FOREVER

def put(self, record):
    with self._lock:            # waits on itself
        ...
```

This is the canonical "test suite hangs" bug. It surfaces on the **first test that
exercises the re-entrant call path** (the wrapper that re-locks), which makes it look
random.

### Fix (minimal — do NOT rewrite the locking logic)
Change `Lock()` to `RLock()` (reentrant lock). That single line lets the same thread
re-acquire.

```python
self._lock = threading.RLock()
```

Prefer `RLock()` for any class whose public methods may call each other while holding
the lock.

## Diagnostic Loop (tight + fast)

1. **Confirm it's a hang, not a crash.** Run a single suspect scope with a hard timeout:
   ```bash
   timeout 90 python -m pytest tests/test_module.py::test_suspect -v -p no:cacheprovider 2>&1 | tail -20
   ```
   If it freezes with no output past the test header, it's a deadlock.

2. **Rule out the "model download / network" reflex.** A frozen test with NO I/O
   (no download progress, no socket connect) is a lock. Grep the call path of the
   hanging test for any `with self._lock` / `self._lock.acquire()` inside a method that
   is itself invoked from under the same lock.

3. **Find the re-entrant pairs.** Look for method A that takes the lock and calls method
   B which also takes it. `grep -n "_lock" file.py` across the class shows the structure
   instantly.

4. **Verify the fix with the same loop** — test goes green, full suite passes.

## Other Silent-Hang Causes (secondary)

- **SQLite + `check_same_thread=False` without a lock** but two threads writing
  concurrently → occasional lock-up; add a lock (RLock around writes).
- **`threading.Lock` shared across a `ThreadPoolExecutor`** with nested locked calls.
- **Blocking call inside a lock** (e.g. `time.sleep`, network) while another thread
  waits for the lock → classic two-thread deadlock (different from self-deadlock).
  Fix by shrinking the critical section, not widening it.

## Red Flags You're Misdiagnosing

| Symptom you see | Wrong conclusion | Reality |
|-----------------|-----------------|---------|
| pytest freezes after 2 dots | "it's downloading the model" | silent self-deadlock on a lock |
| server accepts no connections, no error | "boot failed / port taken" | a thread holds a lock and re-entered it |
| freeze looks random per run | "flaky test" | first re-entrant-path test always hangs |

## Rule of Thumb

If a function takes a lock AND calls a sibling method that also takes that lock → you
need `RLock()`. When in doubt about re-entrancy, `RLock()` is the safe default for
single-object locks.

See `references/deadlock-hang-repro.md` for a minimal reproduction recipe you can run
to confirm the mechanism.
