# 20 Agentic AI Projects — Build Program

Goal: Build 20 different, genuinely-useful, **zero-API-key / free-stack** agentic AI projects
and push each to the **<github-account> (<github-account-2>)** GitHub account as a public repo.

All projects use: Hermes agents for orchestration, AgentEye (free data), AVS (free video),
local models / free APIs only. No paid keys.

## The 20 Projects
1. **research-radar** — Agentic web researcher: given a topic, spawns sub-agents to gather,
   summarize, and write a markdown report + weekly digest (AgentEye + Hermes).
2. **doc-watcher** — Monitors docs/URLs for changes, alerts on diff (AgentEye fetch + cron).
3. **price-patrol** — Tracks product prices across free sources, alerts on drop (product-price-monitor style).
4. **rss-forge** — Aggregates RSS/Atom feeds into a single agentic newsletter (blogwatcher).
5. **video-newsie** — Turns a topic into a short narrated video via AVS (agentic AVS pipeline).
6. **meeting-minutes-ai** — From notes/transcript, extracts decisions + action items (meeting-action-items).
7. **tweet-thread-bot** — Converts a blog/post into an X/Twitter thread draft (not posting, draft only).
8. **code-review-bot** — Agentic PR reviewer using Hermes + security-engineer logic (static checks).
9. **self-host-monitor** — Health dashboard for self-hosted services + alert on downtime.
10. **legal-clause-finder** — Scans contracts/docs for risky clauses (offline NLP, zero key).
11. **recipe-genie** — Agentic meal planner from fridge items + dietary rules (local logic).
12. **flashcard-forge** — Turns notes into Q/A flashcards (anki/markdown export).
13. **resume-tailor** — Tailors a resume to a job description (draft, local).
14. **link-archiver** — Saves web pages as clean markdown + screenshot (offline-asset-generation).
15. **agent-router** — Routes a prompt to the best free model/backend (free-llm-router logic).
16. **invoice-extractor** — OCR-free invoice data extraction from text/pdf (ocr-and-documents).
17. **story-spinner** — Agentic interactive fiction generator (local LLM, branching).
18. **seo-auditor** — Crawls a site (free), reports SEO issues + fixes (web_research).
19. **habit-coach** — Agentic daily habit tracker + nudges via cron (local state).
20. **knowledge-graph** — Builds a markdown interlinked KB from notes (llm-wiki style).

## Execution Model
- Chief of Staff creates 1 parent kanban task + 20 child tasks.
- Each child: assigned to a dev agent (backend/frontend/fullstack) in a git worktree
  (feat/<agent>/<project>), built, security-reviewed, pushed to <github-account>/<project>.
- Security Engineer reviews each before merge/push.
- All repos: public, README with live demo + free-stack note, no email IDs.
