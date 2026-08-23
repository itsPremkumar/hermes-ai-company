#!/usr/bin/env python3
"""yaml_sq.py — YAML single-quote safe-wrapper (copy into any content generator).

Bug it prevents: writing YAML frontmatter like `title: 'How I'd Do It'` breaks YAML
parsing (apostrophe inside single quotes) -> downstream Vercel prerender crash
(YAMLException: can not read a block mapping entry). YAML escapes a single quote by
doubling it, so `'` -> `''`.

Usage:
    from yaml_sq import yaml_sq
    fm = f"title: {yaml_sq(title)}\ndate: {yaml_sq(date)}\n"
"""
def yaml_sq(s):
    """Wrap a string in YAML single quotes, escaping inner quotes by doubling."""
    return "'" + str(s).replace("'", "''") + "'"


if __name__ == "__main__":
    import sys
    # CLI: echo "value" | python yaml_sq.py  ->  'escaped value'
    data = sys.stdin.read() if not sys.argv[1:] else sys.argv[1]
    print(yaml_sq(data))
