# Stage Demo & Scoring (Delhi Browser-use Hackathon)

## Scoring rubric (out of 100)
| Criterion | Points |
|---|---|
| Live reliability — does it complete on stage | 30 |
| Usefulness — does anyone actually want this automated | 25 |
| Technical depth — how well it reasons + recovers | 20 |
| Creativity | 15 |
| Demo & storytelling | 10 |

Two hard rules: (1) Demo live — run it on stage or show a screen recording from a
real execution. (2) Build responsibly — own accounts, respect ToS, human approval
before payments/messages/submissions/deletions unless in a safe sandbox.

## Why hackathon-harvester scores high
- **Live reliability (30):** the DISCOVER module runs against live Devpost via Jina
  and is verified by an ad-hoc script (10/10 checks). Show it fetch + parse live.
- **Usefulness (25):** prize harvesting is a real, repeatable chore anyone entering
  hackathons faces.
- **Technical depth (20):** regex-hardened parser (nav-token + month-left handling),
  stdlib-only (RAM-safe), explicit human-approval gate.
- **Creativity (15):** meta — demo an agent that enters hackathons, *at* a hackathon.
- **Demo/storytelling (10):** 5-min script below.

## 5-minute stage script
1. (0:30) Problem: "I was about to manually scan Devpost for cash prizes. Instead I
   built the agent that does it." Show the email that triggered it.
2. (1:00) Live run `python discover.py` → prints 9 LIVE hackathons with prizes.
   Point at XPRIZE $2M, Backblaze $10k/3days.
3. (1:30) Show the JSON output (name/url/prize/days_left) — structured, sorted.
4. (1:00) Show the DRAFT stage: LLM (OpenClaw free model) turns a row into a pitch +
   writeup skeleton. (Pre-run; don't burn the live free-model quota on stage.)
5. (0:30) Show the human-approval gate: the SUBMIT stage fills the form but PRINTS
   "AWAITING USER APPROVAL" and stops — never auto-submits.
6. (0:30) Close: "It's meta — the demo IS the project. Autonomy with a human in the
   loop, exactly like the rules require."

## Pre-stage checklist
- Jina fetch cached to a file (avoid live 503 on stage).
- OpenClaw gateway started if you demo DRAFT live (`openclaw gateway`).
- AVS demo reel pre-rendered for the chosen hackathon (e.g. Backblaze = generative media).
