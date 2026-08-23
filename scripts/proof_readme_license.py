#!/usr/bin/env python3
import os, sys
d = sys.argv[1]
fs = [f.upper() for dp, _, fs in os.walk(d) for f in fs if ".git" not in dp]
assert any(f == "README.MD" for f in fs), "no README"
assert any(f.startswith("LICENSE") for f in fs), "no LICENSE"
print("readme+license ok")