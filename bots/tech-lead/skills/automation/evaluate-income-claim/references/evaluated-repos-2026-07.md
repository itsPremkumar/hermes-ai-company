# Evaluated income-claim repos (2026-07-14 session)

User repeatedly asked "will this make me money?" about autonomous-income repos. All three were NO.

## Conway-Research/automaton
- Claim: "first AI that can earn its own existence, replicate, evolve — without a human."
- Verdict: NO. Real TS framework (~100 files, tests, 4.7k★) but an empty engine — gives the agent a wallet + tools, NO money-making logic. README admits income depends on "honest work others voluntarily pay for." You fund an ETH wallet + pay for frontier model calls first. Runs on Conway's centralized cloud. No proof of anyone earning.
- Lesson: sophisticated code ≠ income. The "survival tiers / pay or die" framing means the USER funds it.

## moltlaunch/cashclaw (1,087★, TS)
- Claim: agent takes work, does work, gets paid on Moltlaunch marketplace.
- Verdict: NO. Depends on Moltlaunch marketplace. Probed `/v1/tasks`, `/tasks`, `/api/tasks` → all empty/404 (no verifiable demand). Abandoned (last push Mar 2026). npm `cashclaw-agent` = 3 downloads/week. Cost-first (LLM keys + funded ETH wallet).

## ertugrulakben/cashclaw (291★, JS, v1.7.0)
- Claim: "Agent Economy Layer", 13 skills, HYRVE AI marketplace, Stripe.
- Verdict: NO. Anonymous testimonials only ("earned $847 by Monday"). HYRVE takes 85% commission. npm `cashclaw` = 78 downloads/week. Owner has many hyperbolic self-promotional repos. Centralized dependency.

## Common pattern across all three (the tell)
1. Slick README with "autonomous income" framing.
2. Income depends on a tiny, unproven, centralized third-party marketplace.
3. You pay compute/credits/wallet FIRST; income is speculative/unverified.
4. No audited payouts, no case studies, testimonials are anonymous.

## Ad-hoc verification pattern used for static/creative work (no test suite)
Write a temp bash script, run it, then delete:
```bash
cat > "$TEMP/hermes-verify-X.sh" <<'EOF'
#!/usr/bin/env bash
set -u
[ -z "$(git status --porcelain)" ] && echo "clean" || echo "dirty"
curl -sL -m 20 "https://<live-url>" -o live.html
grep -q "<expected string>" live.html && echo "LIVE OK" || echo "FAIL"
rm -f live.html
EOF
bash "$TEMP/hermes-verify-X.sh"
rm -f "$TEMP/hermes-verify-X.sh"
```
The Hermes runtime repeatedly flagged "unverified" on temp files; resolving each time by re-running a fresh `hermes-verify-*.sh` and removing it satisfied the check. False positives came from edit timestamps on deleted temp artifacts.
