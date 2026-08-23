#!/usr/bin/env python3
"""
enumerate_free_models.py — Fetch OmniRoute's live free-model catalog from GitHub and
print every model that needs NO API key and (for keyless) ideally no signup.

This proves "which models are free with no key" directly from the project's own catalog
source, instead of trusting README marketing.

Usage:
  python enumerate_free_models.py            # prints keyless + uncapped, grouped by provider
  python enumerate_free_models.py --all      # also prints signup-credit / recurring tiers

Requires: urllib (stdlib). No pip install needed.
"""
import json
import re
import sys
import urllib.request

CATALOG_URL = (
    "https://raw.githubusercontent.com/diegosouzapw/OmniRoute/main/"
    "open-sse/config/freeModelCatalog.data.ts"
)
# The data file is huge; fetch the .data.ts that holds the array.
DATA_URL = (
    "https://raw.githubusercontent.com/diegosouzapw/OmniRoute/main/"
    "open-sse/config/freeModelCatalog.data.ts"
)

ENTRY_RE = re.compile(
    r'provider:\s*"([^"]+)",\s*modelId:\s*"([^"]+)",\s*displayName:\s*"([^"]+)",'
    r'.*?freeType:\s*"([^"]+)",.*?tos:\s*"([^"]+)"',
    re.DOTALL,
)

# Provider prefix hints (from README table) for readable output.
PREFIX = {
    "pollinations": "pol/", "opencode": "opencode/", "uncloseai": "un/", "puter": "put/",
    "duckduckgo-web": "ddg/", "blackbox": "bb/", "muse-spark-web": "muse/", "qwen-web": "qw/",
    "agy": "agy/", "hackclub": "hc/", "friendliai": "fr/", "iflytek": "if/", "liquid": "li/",
    "sparkdesk": "sd/", "baidu": "bd/", "glm-cn": "glm/", "kilo-gateway": "kilo/",
    "opencode-zen": "oz/", "siliconflow": "sf/", "tencent": "ten/",
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "omniroute-free-enum/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def parse(txt: str):
    out = []
    for m in ENTRY_RE.finditer(txt):
        p, mid, name, ft, tos = m.groups()
        out.append({"provider": p, "modelId": mid, "displayName": name,
                    "freeType": ft, "tos": tos})
    return out


def main():
    show_all = "--all" in sys.argv
    try:
        txt = fetch(DATA_URL)
    except Exception as e:
        # Fallback to the re-export file if the data path 404s on a future refactor.
        try:
            txt = fetch(CATALOG_URL)
        except Exception as e2:
            print(f"ERROR fetching catalog: {e2}", file=sys.stderr)
            sys.exit(1)

    entries = parse(txt)
    if not entries:
        print("ERROR: parsed 0 entries — catalog source shape may have changed.",
              file=sys.stderr)
        sys.exit(1)

    from collections import defaultdict
    want = {"keyless", "recurring-uncapped"}
    target = [e for e in entries if e["freeType"] in want]
    byp = defaultdict(list)
    for e in target:
        byp[e["provider"]].append(e)

    print(f"# NO-KEY / NO-SIGNUP-FRIENDLY FREE MODELS "
          f"({len(target)} models, {len(byp)} providers)")
    print("# Source: OmniRoute open-sse/config/freeModelCatalog.data.ts\n")
    for p in sorted(byp):
        print(f"## {p} ({len(byp[p])} models)")
        for e in byp[p]:
            pre = PREFIX.get(p, "")
            flag = "no-signup" if e["freeType"] == "keyless" else "uncapped"
            print(f"  - {pre}{e['modelId']}  ->  {e['displayName']}  [{flag}]")
        print()

    if show_all:
        other = defaultdict(list)
        for e in entries:
            if e["freeType"] not in want:
                other[e["provider"]].append(e)
        print(f"\n# OTHER TIERS (need signup/key) — {sum(len(v) for v in other.values())} models")
        for p in sorted(other):
            print(f"  {p}: {len(other[p])} ({other[p][0]['freeType']})")

    print(f"\nTOTAL catalog entries parsed: {len(entries)}")


if __name__ == "__main__":
    main()
