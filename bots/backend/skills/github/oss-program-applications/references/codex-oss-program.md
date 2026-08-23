# OpenAI Codex for Open Source Program — application reference

Rolling review; selected applicants notified by email. Form requires agreeing to the Codex for Open Source Program Terms.

## Question set
1. **Describe your role: are you a primary or core maintainer?** (no stated limit)
2. **Why does this repository qualify?** — stars, monthly downloads, ecosystem importance. **Max 500 chars.**
3. **OpenAI Organization ID** — account-specific; the form's "Click here" link opens `https://platform.openai.com/settings/organization` → copy the `org-...` string. Agent cannot fill this; give the user the lookup steps.
4. **How will you use API credits for your project?** **Max 500 chars.**
5. **Anything else we should know?** **Max 500 chars.**

## Verified stats: itsPremkumar/Automated-Video-Generator (fetched 2026-08-01)
- GitHub: 26★, 5 forks, 11 open issues, MIT, created 2026-03-30, last push same day (daily commits)
- npm `automated-video-generator` v5.0.0: **205 downloads last month** (Jul 2–31), **748 last 6 months**
- Release-spike pattern (honest adoption signal): 98 on 2026-03-31 (launch), 165 on 2026-07-01, 72 on 2026-07-03; steady ~25-30/mo organic between spikes

## Final 500-char answers that passed

**Q2 (exactly 500/500):**
> Automated Video Generator is a MIT-licensed, fully self-hosted AI text-to-video pipeline (npm: automated-video-generator: 748 downloads/6 months, 205 last month, 26 stars). It fills a real gap: text-to-video is dominated by paid SaaS (Descript, InVideo, Pictory) with watermarks and subscriptions; open alternatives are scarce. Ships three surfaces — Electron desktop app, CLI, MCP server — 100% local, no API key, serving faceless-YouTube/shorts creators needing private, zero-cost batch production.

**Q4 (449/500):**
> Add an optional OpenAI backend to the agentic pipeline: GPT-driven script-to-scene planning (semantic segmentation, stock-media query generation, caption/chapter drafting) with cost-per-video telemetry, plus an OpenAI TTS fallback. Credits fund CI integration tests and a benchmark suite comparing plan quality and $/video against the current free-tier LLM routing, so users get a measurable quality upgrade while the zero-cost default stays intact.

**Q5 (332/500):**
> Sole creator and primary maintainer, active daily (last commit today; 11 issues triaged, 5 forks, Windows installer, MCP server, 20+ task operations). I mentor for OSCG 2026 and maintain full docs (llms.txt, docs site). Credits would let me build, test, and CI-verify an OpenAI adapter end-to-end without burning personal API costs.

## Framing notes
- Modest star count is fine: the pitch leans on zero-cost/no-API-key positioning, MCP-server/agent alignment, and daily maintenance.
- Q4's "optional backend that keeps the free default" structure is the reviewer-friendly pattern.
- Trim path for Q2 if the form ever tightens: drop the competitor names or the surface list first; keep the download + star stats.
