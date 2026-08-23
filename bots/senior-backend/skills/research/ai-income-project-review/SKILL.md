---
name: ai-income-project-review
description: Honestly evaluate whether a GitHub/agent/crypto project actually earns money, and pivot the user to a real owned paid-service when the pitch is unproven. Use when the user asks "will this AI earn money for me", shares an autonomous-agent / self-replicating / agent-marketplace repo, or any "AI earns its own existence" pitch.
triggers:
  - user asks if a repo/project will earn them money
  - user shares a crypto-agent, autonomous-income, self-replicating AI, or agent-marketplace link
  - user wants a "passive/autonomous income" AI
---

# AI Income Project Review (skeptical)

## Purpose
The user repeatedly asks whether some AI/agent/crypto repo will earn them money. Most such pitches ("first AI that can earn its own existence", "agents earn, agents spend") are **unproven frameworks + a tiny centralized marketplace you must fund first**. This skill turns the question into a real evaluation instead of a vibe-check, then offers a constructive owned alternative.

## Core rule
README/pitch is marketing. Income is real only when you can point to audited payouts from real customers. Anonymous testimonials ("I earned $847 by Monday") are NOT proof.

## Evaluation method (do all, not just README)
1. **Pull real data, not the landing page.** Use the GitHub API + raw README, NOT the browser (browser often times out on these repos). `curl -sL "https://api.github.com/repos/OWNER/REPO"` for stars/forks/last-push. `curl -sL "https://api.github.com/repos/OWNER/REPO/git/trees/main?recursive=1"` for the file tree.
2. **Probe the dependency marketplace for LIVE demand.** These projects route payments through their own marketplace (Moltlaunch, HYRVE, Conway Cloud). curl its API/tasks endpoints; if they 404 or return empty, demand is unverified. Confirm the marketplace site is real but don't assume it has users.
3. **Cost-first check.** Does it require YOU to fund a wallet / API key / credits before any income? "If it cannot pay, it stops existing" = you pay, it may never earn.
4. **Income proof.** Case studies? On-chain payouts? Or only anonymous quotes? Red flag if none.
5. **Commission / structure.** Centralized middleman taking 85%? Net loss after fees.
6. **Maintenance / abandonment.** Last push date vs now. Example: a Moltlaunch cashclaw fork showed last push Mar 2026 and 3 npm downloads/week = effectively dead.
7. **Deliver a verdict table** (template in references/evaluation-checklist.md).

## Red flags (one is enough to distrust income claims)
- "First AI that can earn its own existence / replicate / evolve" — vision pitch, not a product.
- Anonymous testimonials with specific dollar amounts and no audited proof.
- Marketplace API returns 404/empty when probed.
- You must fund compute/credits/wallet before earning.
- Predatory commission (e.g. 85%).
- Owner publishes many similarly hyperbolic repos.
- Tiny npm downloads (single/low double digits per week) for a claimed "global" agent economy.

## Constructive alternative (when the pitch fails)
Don't leave the user with just "no." Build a REAL owned paid service:
- Take a product they already control (e.g. their open-source Automated-Video-Generator).
- Wrap it in a static order site: pricing tiers + a form that opens a pre-filled WhatsApp chat to their number; payments via UPI (India) — zero gateway fees, no middleman.
- Deploy $0 on Vercel Hobby (static, no build). See references/real-money-paid-service.md and the live example: https://github.com/itsPremkumar/aivid-studio (live: https://aivid-studio-rust.vercel.app).
- Drive customers from where the audience already is (their own socials, niche communities). The site is the funnel; the user fulfills with their own engine.

## Pitfalls
- NEVER fabricate a UPI ID, wallet, or token. Leave a clear `YOUR_UPI_ID_HERE` placeholder for the user to set.
- Don't claim "verified income" — only verify repo/site integrity (HTTP 200, files present). Income is the user's to prove via real orders.
- When the system flags "unverified" on deleted temp files, run an ad-hoc integrity script (clean tree, remote files 200, site renders) and report it as ad-hoc, not suite-green.
- Browser navigation times out on these repos often; prefer `curl` + GitHub API.

## References
- references/evaluation-checklist.md — probe recipe (curl commands, verdict table) + git-credential-fill trick for pushing without `gh`.
- references/real-money-paid-service.md — Vercel static paid-service-site pattern, files, deploy command, WhatsApp deep-link snippet.
