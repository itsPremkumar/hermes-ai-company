# LangGraph version-pin recipe (Windows/MSYS, Python 3.11)

## The conflict (observed 2026-07)
Fresh `pip install langgraph langgraph-checkpoint-sqlite` resolves to:

- `langgraph 0.6.11`  → requires `langgraph-checkpoint <4.0.0,>=2.1.0`
- `langgraph-checkpoint-sqlite 3.1.0` → requires `langgraph-checkpoint >=4.1.0`
- resolver installs `langgraph-checkpoint 4.1.1` (satisfies the sqlite saver,
  VIOLATES langgraph's `<4` constraint)

Result: `from langgraph.checkpoint.sqlite import SqliteSaver` →
`ModuleNotFoundError: No module named 'langgraph.checkpoint.sqlite'`
(because 4.x moved the import path / the package split).

## The fix
Pin the sqlite saver to the version that wants checkpoint `<4`:

```toml
# pyproject.toml [project].dependencies
"langgraph>=0.2.40,<1",
"langgraph-checkpoint-sqlite==3.0.0",   # requires langgraph-checkpoint >=3,<4  ✓ matches langgraph 0.6.x
"langchain-core>=0.3,<1",
```

Then verify BEFORE writing tests:

```python
from langgraph_checkpoint_sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode
print("ok", SqliteSaver)
```

## How to find the compatible version (when PyPI release-level requires_dist is empty)
`pip index versions langgraph-checkpoint-sqlite` lists all versions. For each
candidate, fetch the version JSON and grep its `Requires-Dist`:

```bash
for v in 2.0.11 3.0.0 3.1.0; do
  echo "=== $v ==="
  curl -s "https://pypi.org/pypi/langgraph-checkpoint-sqlite/$v/json" \
    | python -c "import sys,json;d=json.load(sys.stdin);print([r for r in (d['info'].get('requires_dist') or []) if 'checkpoint' in r.lower()])"
done
```

Output that drove the pin:
```
2.0.11 -> ['langgraph-checkpoint<3.0.0,>=2.0.21']
3.0.0  -> ['langgraph-checkpoint<4.0.0,>=3']      <-- choose this
3.1.0  -> ['langgraph-checkpoint<5.0.0,>=4.1.0']  <-- conflicts with langgraph 0.6.x
```

## Install + verify (bounded)
```bash
python -m venv .venv && source .venv/Scripts/activate     # Windows git-bash
pip install -q -e ".[dev]"
python -m pytest -q
```
If you ever see `langgraph-checkpoint 4.x` installed alongside `langgraph 0.6.x`,
force downgrade the sqlite saver to `==3.0.0` and reinstall.
