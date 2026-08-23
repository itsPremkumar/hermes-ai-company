#!/usr/bin/env python3
"""
find-dead-intents.py — Diff DECLARED vs IMPLEMENTED command/intent surfaces.

Given a router file (declares intents via a union type) and a dispatcher file
(executes via a switch/case), print which declared intents have NO executor.

Generic enough for most TS "classify → dispatch" codebases. Adjust the two regexes
below if your project names things differently.

Usage:
    python3 find-dead-intents.py <router.ts> <dispatch.ts>

Output: lists dead intents (declared but not dispatched) and orphans (dispatched
but not declared, usually none).

Pitfall for AVS-style code: a `classifyOne()` router WITHOUT a default fallback
will silently mis-route unimplemented intents (e.g. "convert" -> full_video).
This script surfaces exactly that failure class.
"""
import re
import sys
import os


def extract_union_members(text, union_start_marker):
    """Extract 'x' | 'y' members after a union type marker (e.g. `type Kind =`)."""
    idx = text.find(union_start_marker)
    if idx == -1:
        return []
    # take the slice up to the next ';' or closing ')'
    slice_end = text.find(';', idx)
    if slice_end == -1:
        slice_end = idx + 1200
    chunk = text[idx:slice_end]
    return re.findall(r"\| '([a-z0-9_]+)'", chunk)


def extract_switch_cases(text, case_marker="case '([a-z0-9_]+)':"):
    return re.findall(case_marker, text)


def main():
    if len(sys.argv) < 3:
        print("usage: find-dead-intents.py <router.ts> <dispatch.ts>")
        sys.exit(1)
    router, dispatch = sys.argv[1], sys.argv[2]
    if not (os.path.exists(router) and os.path.exists(dispatch)):
        print("one or both files not found")
        sys.exit(1)

    rt = open(router, encoding="utf-8").read()
    dt = open(dispatch, encoding="utf-8").read()

    # Union marker: the line that introduces the TaskKind union.
    union_marker = "TaskKind"
    kinds = extract_union_members(rt, union_marker)
    # Fallback: also grab from first `type X =` near 'TaskKind'
    if not kinds:
        m = re.search(r"type\s+\w+\s*=\s*([^;]+)", rt)
        if m:
            kinds = re.findall(r"'([a-z0-9_]+)'", m.group(1))

    cases = extract_switch_cases(dt)

    print(f"=== Declared intents ({len(kinds)}) ===")
    for k in kinds:
        print(f"  - {k}")
    print(f"\n=== Implemented ops ({len(cases)}) ===")
    for c in cases:
        print(f"  - {c}")

    dead = [k for k in kinds if k not in cases]
    orphan = [c for c in cases if c not in kinds]
    print("\n=== ⚠️ DECLARED BUT NOT IMPLEMENTED (dead intents) ===")
    if dead:
        for d in dead:
            print(f"  - {d}")
    else:
        print("  (none)")
    print("\n=== Dispatched but not declared (orphan) ===")
    print("  " + (", ".join(orphan) if orphan else "(none)"))


if __name__ == "__main__":
    main()
