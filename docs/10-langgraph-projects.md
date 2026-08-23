# 10 LangGraph Agentic AI Projects — Build Program

Goal: Build 10 genuinely-useful, **zero-API-key / free-stack** agentic AI projects using **LangGraph** + TypeScript/Python, and push each to GitHub.

All projects use: LangGraph (agent orchestration), Hermes agents for execution, AgentEye (free data), local models / free APIs only. No paid keys.

---

## Project 1: Research Radar
**Purpose**: Given a topic, spawn parallel sub-agents to gather, summarize, and write a cited markdown report. Weekly digest mode.
**Stack**: LangGraph + TypeScript + AgentEye + DuckDuckGo
**Repo**: `research-radar`
**LangGraph pattern**: Supervisor → N searcher nodes → synthesizer → writer
**MVP**: `research-radar "topic"` → spawns 3 parallel search agents → merges → report.md with citations

## Project 2: Code Review Bot
**Purpose**: Watches GitHub PRs, reviews code for bugs/security/style, posts inline comments.
**Stack**: LangGraph + TypeScript + GitHub MCP
**Repo**: `code-review-bot`
**LangGraph pattern**: PR fetch → diff analysis → security scan → style check → comment poster
**MVP**: Given PR URL → spawn reviewer agents (correctness, security, style) → post review

## Project 3: Knowledge Graph Builder
**Purpose**: Ingest documents/URLs, extract entities + relationships, build queryable knowledge graph.
**Stack**: LangGraph + Python + Neo4j + spaCy/Hugging Face
**Repo**: `kg-builder`
**LangGraph pattern**: Ingest → chunk → NER → relationship extraction → graph upsert → query
**MVP**: `kg-builder ingest file.pdf` → `kg-builder query "what is X related to"`

## Project 4: Meeting Minutes AI
**Purpose**: Transcribe meeting audio, extract action items, decisions, follow-ups. Generate structured minutes.
**Stack**: LangGraph + TypeScript + Whisper (local) + LLM
**Repo**: `meeting-minutes`
**LangGraph pattern**: Transcribe → segment → extract (items/decisions/followups) → format → notify
**MVP**: `meeting-minutes meeting.mp3` → structured markdown minutes

## Project 5: RSS Forge
**Purpose**: Aggregate RSS/Atom feeds, summarize each item, generate unified newsletter.
**Stack**: LangGraph + TypeScript + RSS parser + LLM
**Repo**: `rss-forge`
**LangGraph pattern**: Fetch feeds in parallel → summarize each → deduplicate → rank → generate newsletter
**MVP**: `rss-forge --feeds urls.txt` → weekly newsletter.md

## Project 6: Price Patrol
**Purpose**: Track product prices across free sources, alert on drops.
**Stack**: LangGraph + TypeScript + web scraper + DuckDuckGo
**Repo**: `price-patrol`
**LangGraph pattern**: Config → scheduled fetch → compare → alert on drop
**MVP**: `price-patrol add "product name" --target $50` → checks daily → alert

## Project 7: Self-Host Monitor
**Purpose**: Monitor uptime/health of self-hosted services, alert on downtime.
**Stack**: LangGraph + TypeScript + HTTP checker + Telegram/Discord notify
**Repo**: `self-host-monitor`
**LangGraph pattern**: Config → ping all services → classify (up/down/degraded) → alert on down → periodic re-check
**MVP**: `monitor add https://example.com` → pings every 60s → alerts

## Project 8: Doc Watcher
**Purpose**: Monitor docs/URLs for changes, alert on diff.
**Stack**: LangGraph + TypeScript + DuckDuckGo + diff
**Repo**: `doc-watcher`
**LangGraph pattern**: Register URL → periodic fetch → compare → alert on change → show diff
**MVP**: `doc-watcher add https://example.com/docs` → weekly check → alert + diff

## Project 9: Invoice Extractor
**Purpose**: Extract structured data from PDF invoices (vendor, amount, date, line items).
**Stack**: LangGraph + Python + pdfplumber + LLM
**Repo**: `invoice-extractor`
**LangGraph pattern**: Parse PDF → OCR fallback → extract fields → validate → export JSON/CSV
**MVP**: `invoice-extractor invoice.pdf` → JSON with vendor, amount, date, items

## Project 10: Tweet Thread Bot
**Purpose**: Turn a topic/URL into a thread of connected tweets, scheduled posting.
**Stack**: LangGraph + TypeScript + Twitter API (free tier)
**Repo**: `tweet-thread-bot`
**LangGraph pattern**: Input (topic/URL) → research → outline → generate tweets → thread → post
**MVP**: `tweet-thread-topic "AI agents"` → generates 5-tweet thread → posts

---

## Kanban Board Setup

All 10 projects go on the `it-company-ops` board as cards, assigned to `fullstack-dev`.

Each card follows the SOP lifecycle: `ready → assigned → claimed → in_progress → request-review → approved → complete → archived`.

## Build Order (priority)

1. research-radar (already done)
2. rss-forge (simple, fast)
3. self-host-monitor (simple, useful)
4. doc-watcher (medium)
5. code-review-bot (medium)
6. price-patrol (medium)
7. invoice-extractor (medium-hard)
8. meeting-minutes (hard)
9. kg-builder (hard)
10. tweet-thread-bot (medium)
