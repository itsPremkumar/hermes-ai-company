# Install a Node CLI from a GitHub-release `.tgz` (not on npm)

Worked template from installing `prime-agent@0.7.0` (PrimeIntellect) on Windows 10 / nvm4w / git-bash.
This pattern applies to ANY global Node CLI shipped as a versioned release tarball instead of the public npm registry.

## Why this path
- `npm view prime-agent` -> `404 Not Found`. The package is NOT on registry.npmjs.org.
- The repo's `install.sh` is a shell script (macOS/Linux only) that downloads a release tarball and runs `npm install -g`. We replicate it manually for control + checksum verification.

## Steps (verified)
```bash
mkdir -p /c/one/prime-agent-install && cd /c/one/prime-agent-install
VER=v0.7.0
# 1. release manifest (sha256 per tarball) + CLI tarball
curl -fsSL -o latest.json "https://github.com/PrimeIntellect-ai/prime-agent/releases/download/$VER/latest.json"
curl -fsSL -o "prime-agent-$VER.tgz" "https://github.com/PrimeIntellect-ai/prime-agent/releases/download/$VER/prime-agent-$VER.tgz"

# 2. verify sha256 against manifest EXACTLY
exp=$(grep -A2 '"file": "prime-agent-'$VER'.tgz"' latest.json | grep sha256 | grep -oE '[0-9a-f]{64}')
act=$(sha256sum "prime-agent-$VER.tgz" | cut -d' ' -f1)
[ "$exp" = "$act" ] && echo "HASH OK ($act)" || { echo "MISMATCH"; exit 1; }

# 3. inspect package.json WITHOUT installing (trap check)
tar -xzf "prime-agent-$VER.tgz" -C . package/package.json
node -e "const p=require('./package/package.json');console.log(JSON.stringify({name:p.name,version:p.version,bin:p.bin,os:p.os,engines:p.engines,scripts:p.scripts},null,2))"
# -> bin: {prime-agent: dist/bundle/cli.js}, engines.node >=22.8.0, NO os field => Windows ok

# 4. inspect postinstall for OS-specific traps
tar -xzf "prime-agent-$VER.tgz" -C . package/dist/postinstall.js
# -> only runs if PRIME_AGENT_BOOTSTRAP_KERNEL_ON_INSTALL=1 / PRIME_AGENT_BOOTSTRAP_TOOLS_ON_INSTALL=1; default is no-op. Safe.

# 5. install globally (big: ~192 deps; use background+notify if slow)
npm install -g "./prime-agent-$VER.tgz" 2>&1 | tail -15

# 6. verify on Windows (nvm4w puts bin on PATH via /c/nvm4w/nodejs symlink)
prime-agent --version          # 0.7.0
prime-agent --help             # renders full command surface
prime-agent status             # no background services (fine)
```

## Windows run caveat
- CLI boots fine on nvm4w (Node 22.23.1 satisfies >=22.8.0, no `os` restriction).
- Its IPython *kernel* tool (persistent Python sandbox) may assume a POSIX shell. For full fidelity, run under WSL (installed but service disabled on this box — `wsl --install`/enable to use).
- It is NOT a security sandbox; only point at trusted repos.

## Cleanup
Scratch dir may be "device busy" if cwd is inside it (AV lock). `cd` out then `rm -rf`, or `mv` to a temp name first then remove.
