# Windows IPython-kernel bootstrap: pitfalls & the fix

Symptom: prime-agent launches, authenticates, and reaches the model API, but every tool call
("list files", shell, etc.) fails with:
`Failed to set up the Python kernel runtime ... uv.exe pip install ... failed with exit code 2`
or the agent says "missing ipykernel". The model is fine; only the agent's execution "hands" die.

## Why it breaks on this Windows box
1. **uv-managed venv doesn't persist for standalone python.** Hermes bundles `uv`; its
   `uv venv` builds from a *managed* CPython (`Roaming/uv/python/...`). That venv's
   `python.exe` resolves sys.path to Hermes's `hermes-agent/venv` (a `_virtualenv.pth`
   hijack) and `pyvenv.cfg` can vanish — so `ipykernel` imported right after `uv pip install`
   but fails in a *fresh* shell. Same-shell success is misleading.
2. **venv pip can't resolve DNS.** `pip install` → `files.pythonhosted.org: getaddrinfo failed`.
   `uv`, however, HAS working network. So install deps with `uv`, not the venv's pip.
3. **`VIRTUAL_ENV` / `UV_*` redirect uv installs.** If set, `uv pip install --python <venv>`
   lands packages in the wrong env. `unset` them first.
4. **pandas 3.x binary incompat.** `pandas==3.0.5` → `ImportError: cannot import name 'ops'
   from 'pandas._libs'`. Pin `pandas<3`.
5. **bootstrap path fight.** prime-agent auto-bootstraps at `~/.prime/agent/kernel-venv` and
   looks for `kernel-venv/bin/python` (Linux). Build the venv off that path and disable
   bootstrap with `PRIME_AGENT_KERNEL_PYTHON`.

## Durable fix (verified)
- Standalone Python 3.12 venv (persists): `C:/Users/PREM KUMAR/AppData/Local/Programs/Python/Python312/python.exe -m venv`
- Install with uv, env redirects unset, include the LOCAL runtime dir
  `<npm-global>/prime-agent/dist/prime-agent-runtime` (NOT on PyPI; hatchling build).
- Venv at `~/.prime/kernel-venv` (off bootstrap path).
- `export PRIME_AGENT_KERNEL_PYTHON="$USERPROFILE/.prime/kernel-venv/Scripts/python.exe"`.
- Verify in a FRESH shell: `bash -lc "'<venv>/Scripts/python.exe' -c \"import ipykernel, rlm; print('OK')\""`

## prime-agent's kernel check (from bundle chunk-ALQBG3TN.js)
`hasIpykernel(python) && hasPrimeAgentRuntime(python) && bootstrapVersionCurrent(...)`.
So both `ipykernel` import AND `prime-agent-runtime` (`rlm`) import must succeed in the kernel
python, verified in a fresh shell.
