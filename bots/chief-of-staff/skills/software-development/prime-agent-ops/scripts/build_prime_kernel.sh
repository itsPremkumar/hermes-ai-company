#!/usr/bin/env bash
# Build a durable Prime Agent IPython kernel venv on Windows (MSYS/git-bash).
# Fixes: uv-managed-venv non-persistence, pip DNS failure, VIRTUAL_ENV redirect,
#        bootstrap path fight, pandas 3.x binary incompat.
# Run from a bash terminal. Requires: standalone Python 3.12 + Hermes's uv on PATH.
set -e

# --- standalone Python 3.12 (NOT uv's managed python) ---
SYS_PY="/c/Users/PREM KUMAR/AppData/Local/Programs/Python/Python312/python.exe"
# Hermes's uv (has working network; venv pip cannot resolve DNS)
export PATH="$USERPROFILE/AppData/Local/hermes/bin:$PATH"

# --- locate the local prime-agent-runtime wheel source inside the npm global root ---
NPM_GLOBAL=$(npm root -g 2>/dev/null || echo "$APPDATA/../Local/nvm/v22.23.1/node_modules")
RT="$NPM_GLOBAL/prime-agent/dist/prime-agent-runtime"
if [ ! -d "$RT" ]; then
  echo "ERROR: prime-agent-runtime not found at $RT" >&2
  echo "       glob: $(ls -d "$NPM_GLOBAL"/prime-agent/dist/prime-agent-runtime 2>/dev/null || echo none)" >&2
  exit 2
fi

# --- kernel venv OFF the bootstrap path so prime-agent doesn't fight it ---
VENV="$USERPROFILE/.prime/kernel-venv"
rm -rf "$VENV"

# --- unset env that redirects uv/pip installs ---
unset VIRTUAL_ENV UV_PROJECT_ENVIRONMENT UV_VENV_DIR PYTHONPATH CONDA_PREFIX

echo "==> creating venv from standalone Python 3.12"
"$SYS_PY" -m venv "$VENV"
echo "    pyvenv.cfg exists: $([ -f "$VENV/pyvenv.cfg" ] && echo YES || echo NO)"

echo "==> installing deps via uv (working network)"
uv pip install --python "$VENV/Scripts/python.exe" \
  ipykernel nest-asyncio tyro requests httpx pyyaml "pandas<3" numpy dill \
  "$RT" 2>&1 | tail -6

echo "==> FRESH-shell verify (the real test)"
bash -lc "'$VENV/Scripts/python.exe' -c \"import ipykernel, rlm, requests, httpx, yaml, numpy, pandas; print('KERNEL OK | ipykernel', ipykernel.__version__, '| rlm', bool(__import__('rlm')), '| pandas', pandas.__version__)\"" 2>&1 | tail -3

echo ""
echo "==> DONE. To run prime-agent:"
echo "export PRIME_AGENT_KERNEL_PYTHON=\"$VENV/Scripts/python.exe\""
echo "OPENCODE_API_KEY=\"\$KEY\" prime-agent --provider opencode --model deepseek-v4-flash-free"
