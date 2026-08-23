# Python CLI tool pattern for ClawHub skills

Stdlib-only CLI tool template proven in the `secret-scanner` skill. Use as
scaffolding for any ClawHub skill that ships a Python executable.

## Structure

```
clawhub-skills/my-skill/
├── SKILL.md              # frontmatter + docs
└── my_tool.py            # the executable
```

## Argparse subcommand pattern

Two proven dispatch patterns. Pick the one that matches your tool's complexity.

### Pattern A: dict-dispatch with `parse_args()` (simpler, preferred for clean CLIs)

Used by `json-tools`, `md-linter`, and `file-watcher` — all 3 published skills
from this session. Works when all subcommand flags use argparse properly and
don't need pass-through arguments.

```python
#!/usr/bin/env python3
"""One-line module docstring — becomes the tool's help text."""

import argparse, os, sys


def cmd_validate(args) -> None:
    """Validate something. Exits 1 on failure."""
    for path in args.paths:
        # ... logic ...
        pass
    sys.exit(exit_code)


def cmd_format(args) -> None:
    """Format something."""
    data = load_json(args.path)
    print(json.dumps(data, indent=args.indent))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tool description")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="Validate input")
    p.add_argument("paths", nargs="+", metavar="FILE")

    p = sub.add_parser("format", help="Format input")
    p.add_argument("path", help="Input path")
    p.add_argument("--indent", type=int, default=2)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    cmds = {
        "validate": cmd_validate,
        "format": cmd_format,
    }
    cmds[args.command](args)


if __name__ == "__main__":
    main()
```

Key advantages:
- No `parse_known_args` complexity — flags land cleanly on subparser args
- Dict dispatch is testable inline: `cmd_format(type('args', (), {'path': p, 'indent': 2})())`
- Single return path per command, clear exit-code handling
- Works for 2-20 subcommands without growing complexity
- Each cmd_* function receives a namespace, not a raw list — flags are named attributes

### Pattern B: positional-arg dispatch with `parse_known_args()` (for tools with positional overload)

```python
#!/usr/bin/env python3
"""One-line module docstring — becomes the tool's help text."""

import argparse, os, sys

def cmd_scan(args: list[str]) -> None:
    path = args[0]
    # ... logic ...
    print(f"Scanned {path}")

def cmd_check(args: list[str]) -> None:
    filepath = args[0]
    # ... logic ...

def cmd_list(args: list[str]) -> None:
    for item in get_items():
        print(item)

def main() -> None:
    parser = argparse.ArgumentParser(description="...")
    parser.add_argument("--version", action="version", version="tool 1.0.0")

    sub = parser.add_subparsers(dest="command", required=True)

    scan_p = sub.add_parser("scan", help="Scan something")
    scan_p.add_argument("path", nargs="?")
    scan_p.add_argument("--json", action="store_true")

    sub.add_parser("list", help="List things")

    check_p = sub.add_parser("check", help="Check single file")
    check_p.add_argument("file", nargs="?")

    parsed, rest = parser.parse_known_args()

    if parsed.command == "list":
        cmd_list(rest)
    elif parsed.command == "scan":
        args = rest if not parsed.path else [parsed.path] + rest
        # propagate subparser flags through to cmd_scan
        if getattr(parsed, "json", False):
            args.append("--json")
        cmd_scan(args)
    elif parsed.command == "check":
        cmd_check(rest if not parsed.file else [parsed.file] + rest)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Pitfalls

- **Subparser flags with `parse_known_args`:** flags defined on subparsers
  (like `--json` on `scan`) are consumed by argparse into `parsed.json`, not
  `rest`. Pass them explicitly: `if getattr(parsed, 'json', False): args.append("--json")`.
- **Nested `nargs="?"`:** positional args on subparsers land in `parsed.path`
  etc. Prefix unknown extra args from `rest` to support both
  `scan path --json` and `scan --json path`.
- **Exit codes:** Use `sys.exit(2)` for "secrets found" / "violation detected"
  states. CI systems check `$?` — 0 = clean, 1 = usage error, 2 = findings.
- **Redacted output for CI safety:** Show secrets as `first4****last4` in
  reports to prevent log leakage.
- **Binary-file guard:** Check for `\0` bytes in the first 8KB before reading
  as text — prevents crashes on binary files.
- **HTMLParser `_skip` set init (text-extraction tools):** When using `html.parser.HTMLParser`
  to strip tags and extract text (common in web-scraping skills), the `_skip` set that
  tracks tags whose content should be suppressed (script, style, noscript) MUST start
  empty. A common bug: initializing `self._skip = {"script", "style", "noscript"}`
  instead of `self._skip = set()`, then testing `if tag in self._skip: self._skip.add(tag)`.
  With the wrong init, the set is never empty, so `if not self._skip:` in
  `handle_data` is always False and ALL text content is silently dropped.
  **Correct pattern:**
  ```python
  SKIP_TAGS = {"script", "style", "noscript"}
  class _Parser(HTMLParser):
      def __init__(self):
          super().__init__()
          self._skip = set()
      def handle_starttag(self, tag, attrs):
          if tag in SKIP_TAGS:
              self._skip.add(tag)
      def handle_endtag(self, tag):
          self._skip.discard(tag)
      def handle_data(self, data):
          if not self._skip:        # only capture when no skip-tag is active
              self._text.append(data)
  ```
  Keep `SKIP_TAGS` as a module-level constant so the inner class doesn't redefine
  it every instantiation.
