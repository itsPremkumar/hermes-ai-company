#!/usr/bin/env python3
"""TEMPLATE — copy to money/pipelineN_name.py and fill in. Stdlib-only.
Replace UPPERCASE tokens. Keep the proven shape: data dict + build_package
+ real n8n_workflow (no TODO) + self-test + --list/--out + main().
"""
import argparse, json, sys

ITEMS = {
    "starter": {"title": "I will <OUTCOME> for you",
                "monthly": 99, "note": "<cost note: free tools>"},
    "pro": {"title": "I will <BIGGER OUTCOME>",
            "monthly": 199, "note": "<cost note>"},
}


def build_package(key, price=None):
    it = ITEMS[key]
    price = price or it["monthly"]
    return {
        "tier": key,
        "gig_title": it["title"],
        "pricing": {"monthly": price, "margin_pct": 95,
                    "cost_note": it["note"]},
        # REAL n8n workflow — executable nodes, NO placeholder
        "n8n_workflow": build_n8n(key),
        "delivery_steps": [
            "1. <step>", "2. <step>", "3. <step>", "4. <step>", "5. <step>",
        ],
        "tags": ["<tag1>", "<tag2>", key + " <tag3>", "automation"],
    }


def build_n8n(key):
    return {
        "name": f"svc-{key}",
        "nodes": [
            {"type": "n8n-nodes-base.scheduleTrigger", "name": "Trigger",
             "params": {"interval": [{"field": "cronExpression", "expression": "0 9 * * *"}]}},
            {"type": "n8n-nodes-base.code", "name": "Process",
             # NOTE: use {{ }} for literal braces; keep a real `return`
             "code": "const d = items[0].json;\nreturn [{json: {result: d.input.toUpperCase()}}];"},
        ],
        "connections": "Trigger → Process",
    }


def main():
    p = argparse.ArgumentParser(description="Pipeline N — <NAME>")
    p.add_argument("--tier", help="tier: " + ", ".join(ITEMS.keys()))
    p.add_argument("--price", type=int); p.add_argument("--out")
    p.add_argument("--list", action="store_true"); p.add_argument("cmd", nargs="?", default="self-test")
    a = p.parse_args()
    if a.list:
        for k, v in ITEMS.items():
            print(f"  {k:8} ${v['monthly']}/mo  {v['title'][:40]}")
        return
    if a.cmd == "self-test" and not a.tier:
        for k in ITEMS:
            pkg = build_package(k)
            assert pkg["gig_title"] and pkg["n8n_workflow"]["nodes"]
            assert pkg["pricing"]["margin_pct"] == 95
            code = pkg["n8n_workflow"]["nodes"][1]["code"]
            assert "return" in code and "TODO" not in code
        print(f"self-test: OK — {len(ITEMS)} tiers")
        return
    if not a.tier or a.tier not in ITEMS:
        print("ERROR: --tier required: " + ", ".join(ITEMS.keys())); sys.exit(1)
    pkg = build_package(a.tier, a.price)
    if a.out:
        json.dump(pkg, open(a.out, "w", encoding="utf-8"), indent=2); print(f"Wrote -> {a.out}")
    else:
        print(f"\n💰 {a.tier}: {pkg['gig_title']}  ${pkg['pricing']['monthly']}/mo")


if __name__ == "__main__":
    main()
