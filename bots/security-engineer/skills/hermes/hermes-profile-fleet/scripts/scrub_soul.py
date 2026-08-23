import os, re, sys

# Scrub a source profile's name from all cloned SOUL.md files and replace with role names.
# Usage: python scrub_soul.py <profiles_dir> <source_name> <role_name_default>
# e.g. python scrub_soul.py "C:/Users/PREM KUMAR/AppData/Local/hermes/profiles" bunny Chief of Staff

profiles_dir = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\PREM KUMAR\AppData\Local\hermes\profiles"
source = sys.argv[2] if len(sys.argv) > 2 else "bunny"
# Default replacement when no role mapping matches
default_repl = sys.argv[3] if len(sys.argv) > 3 else "the appropriate role"

# Per-profile correct role name (edit as needed)
role_map = {
    "architect": "Solution Architect / CTO",
    "product-owner": "Product Owner",
    "product-manager": "Product Manager",
    "ceo": "CEO",
    "cto": "CTO",
    "coo": "COO",
}

count = 0
for p in os.listdir(profiles_dir):
    if p == source:
        continue
    soul = os.path.join(profiles_dir, p, "SOUL.md")
    if not os.path.exists(soul):
        continue
    txt = open(soul, encoding="utf-8").read()
    if re.search(re.escape(source), txt, re.I):
        repl = role_map.get(p, default_repl)
        new = re.sub(rf"\b{re.escape(source)}\b", repl, txt, flags=re.I)
        # Also fix "escalate to **Bunny** (CTO)" style -> "escalate to **CTO**"
        new = new.replace(f"**{source.capitalize()}**", f"**{repl}**")
        open(soul, "w", encoding="utf-8").write(new)
        count += 1
        print(f"scrubbed {p}: replaced '{source}' -> '{repl}'")

print(f"\nDone. Scrubbed {count} files. (Source profile '{source}' left untouched — give it a real role separately.)")
