#!/usr/bin/env python3
import os, sys
d = sys.argv[1]
fs = [os.path.join(dp, f) for dp, _, fs in os.walk(d) for f in fs if ".git" not in dp]
total = sum(os.path.getsize(x) for x in fs)
assert len(fs) >= 4 and total > 200, f"only {len(fs)} files / {total}B"
print(f"{len(fs)} files, {total}B")