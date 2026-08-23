# Minimal Deadlock Reproduction (self-deadlock via non-reentrant Lock)

Run this to confirm the mechanism. It freezes forever on the `update()` call.

```python
import threading

class Store:
    def __init__(self):
        self._lock = threading.Lock()   # WRONG: not reentrant

    def put(self, x):
        with self._lock:
            return x

    def update(self, old, new):
        with self._lock:          # holds lock
            return self.put(new)  # re-enters -> blocks on itself

s = Store()
s.update(1, 2)   # <-- hangs here, no traceback
print("done")    # never reached
```

## The fix
```python
self._lock = threading.RLock()   # reentrant: same thread may re-acquire
```

After the change, `s.update(1, 2)` returns immediately and `done` prints.

## How this showed up in a real session
SAMM's `MemoryStore.update()` held `self._lock` (a `threading.Lock()`) and called
`self.put()`, which also did `with self._lock:`. Result: `pytest tests/` printed 2 dots
then hung; the runner timed out at 300s with no error. The human reflex was "it's
downloading the sentence-transformers model" — wrong. Isolating with
`pytest tests/test_engine.py -v` + `timeout 90` showed the freeze on the first
re-entrant-path test (`test_versioning_and_history`). Switching `Lock()` -> `RLock()`
fixed it; the full suite then passed 27 tests.

## Diagnostic one-liner (real repo)
```bash
cd repo && timeout 90 python -m pytest tests/test_engine.py -v -p no:cacheprovider 2>&1 | tail -20
```
A frozen single test with no I/O = lock, not download. Then grep:
```bash
grep -n "_lock" samm/store.py
```
to find the method that takes the lock and calls a sibling that re-takes it.
