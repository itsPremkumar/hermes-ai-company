#!/usr/bin/env python3
import json, sys, urllib.request
repo = sys.argv[1]
d = json.load(urllib.request.urlopen(f"https://api.github.com/repos/{repo}", timeout=20))
assert d.get("size", 0) > 5 or d.get("default_branch"), "repo empty/missing"
print(f"{repo}: {d['size']}KB default={d['default_branch']}")