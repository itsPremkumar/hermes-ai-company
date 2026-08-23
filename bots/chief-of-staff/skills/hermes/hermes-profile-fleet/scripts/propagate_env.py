import os, sys

# Copy one env var (e.g. OPENROUTER_API_KEY) from a source profile's .env into every
# other profile's .env that lacks it. Commented-out keys do NOT count as present.
# Usage: python propagate_env.py <profiles_dir> <env_var> <source_profile>
# e.g. python propagate_env.py "C:/Users/PREM KUMAR/AppData/Local/hermes/profiles" OPENROUTER_API_KEY bunny

profiles_dir = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\PREM KUMAR\AppData\Local\hermes\profiles"
var = sys.argv[2] if len(sys.argv) > 2 else "OPENROUTER_API_KEY"
src = sys.argv[3] if len(sys.argv) > 3 else "bunny"

src_env = os.path.join(profiles_dir, src, ".env")
val = None
if os.path.exists(src_env):
    for line in open(src_env, encoding="utf-8", errors="ignore"):
        if line.strip().startswith(f"{var}=") and not line.strip().startswith(f"#{var}="):
            val = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
            break
if not val:
    print(f"ERROR: {var} not found (uncommented) in {src}/.env")
    sys.exit(1)

n = 0
for p in os.listdir(profiles_dir):
    ep = os.path.join(profiles_dir, p, ".env")
    if not os.path.exists(ep):
        open(ep, "w").write("")
    txt = open(ep, encoding="utf-8", errors="ignore").read()
    # present only if an uncommented assignment exists
    present = any(l.strip().startswith(f"{var}=") and not l.strip().startswith(f"#{var}=") for l in txt.splitlines())
    if not present:
        with open(ep, "a", encoding="utf-8") as f:
            f.write(f"\n{var}={val}\n")
        n += 1
        print(f"+ {var} -> {p}")

print(f"\nPropagated {var} to {n} profiles from '{src}'.")
