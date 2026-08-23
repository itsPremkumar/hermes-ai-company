---
name: skill-name
version: 1.0.0
description: One-line summary. Folded scalar (>-) for multi-line descriptions that stay single-line in tool tips and listings.
tags: [category1, category2, domain]
---

# Skill Display Name

One paragraph: what the tool does, who it's for, and the pain point it addresses. Keep it tight — this is the reader's first impression.

## Install

```bash
# No dependencies needed — Python 3.8+ stdlib only
python tool_name.py --help

# Make it a system command
chmod +x tool_name.py
sudo cp tool_name.py /usr/local/bin/tool-name
```

## Commands

| Command | Description |
|---------|-------------|
| `command-a` | Does X — validate, check, list |
| `command-b` | Does Y — generate, insert, diff |
| `command-c` | Does Z — filter, merge, format |

## Usage

```bash
# Run the primary command
python tool_name.py command-a path/to/input

# With flags
python tool_name.py command-b path --flag value

# Multiple files
python tool_name.py command-c path/to/a path/to/b --output result
```

## Features

- **Zero dependencies** — pure Python stdlib, no pip/npm install
- **CI-friendly** — exits 0 on success, non-zero on findings
- **Stdin support** — pipe data through commands
- **Colorized output** — red/green diff, yellow warnings
- **Glob/regex filtering** — ignore noise patterns

## Examples

```bash
# Combine commands
python tool_name.py command-a input.file && python tool_name.py command-b input.file

# One-liner: validate then format
python tool_name.py validate package.json && python tool_name.py format package.json

# Programmatic use: export to file
python tool_name.py command-c input --output result.json
```

## Why This Exists

Existing tools (alternative X, alternative Y) require installs or heavy dependencies. This tool runs anywhere Python 3.8+ runs — Docker, CI, locked-down enterprise, Windows. A single file you can audit, copy, or vendor without package managers.

## Support

- File an issue on the [ClawHub registry](https://clawhub.nousresearch.com)
- MIT License — free to use, modify, and share
