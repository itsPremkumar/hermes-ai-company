#!/usr/bin/env python3
import json, sys
g = json.load(open(sys.argv[1], encoding="utf-8"))
assert g.get("goal") and len(g.get("criteria", [])) >= 1, "trivial goal"
print("goal documented:", g["goal"][:60])