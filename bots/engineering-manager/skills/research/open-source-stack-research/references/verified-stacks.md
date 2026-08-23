# Verified open-source stacks (condensed, live-star verified where marked ✅)

> Update as new repos are verified. `(c)` = canonical/not re-verified this session.

## Web crawling / research (AI-native)
- `firecrawl/firecrawl` ✅ 148.8k · AGPL-3.0 — AI search/scrape/extract, JS sites, MCP, Docker
- `unclecode/crawl4ai` ✅ 72.2k · Apache-2.0 — local-first, LLM-ready Markdown, RAG
- `browser-use/browser-use` ✅ 104.1k · MIT — AI browser control, logins, forms
- `Panniantong/Agent-Reach` ✅ 54.3k · MIT — internet + social intelligence, zero API fee
- `scrapy/scrapy` ✅ 63.1k · BSD-3 — large-scale structured crawling
- `searxng/searxng` ✅ 33.7k · AGPL-3.0 — private metasearch
- `apify/crawlee` ✅ 24.6k · Apache-2.0 — modern JS crawler

## Voice / telecalling
- `dograh-hq/dograh` ✅ 4.8k · BSD-2 — self-hosted voice AI (Vapi alt)
- `pipecat-ai/pipecat` ✅ 13.3k · BSD-2 — voice/multimodal framework
- `livekit/livekit` ✅ 19.7k · Apache-2.0 — realtime comms
- `openai/whisper` ✅ 104.7k · MIT — STT
- `rhasspy/piper` ✅ 11.2k · MIT — local TTS
- `kirklandsig/AIReceptionist` ✅ 57 · — AI phone receptionist
- `mohitbadwal/ringback` ✅ 16 · — MCP: AI calls your phone

## Voice cloning / realistic TTS (LICENSE-VERIFIED, 2026-07)
> For a project that must be free + self-hosted + license-clean (MIT/Apache only, NO
> AGPL/non-commercial/MPL) + realistic voice cloning + agentic (CLI/MCP/REST).
> All star counts / licenses / sizes below pulled LIVE from GitHub + HuggingFace.

### ✅ Recommended (license-clean + clones)
- `resemble-ai/chatterbox` ✅ 25.5k · **MIT** — zero-shot clone (few-sec), `[laugh]`/`[sigh]` tags.
  GOTCHA: weights ~1.8GB AND **HF-gated (login required)** to download.
- `QwenLM/Qwen3-TTS` ✅ · **Apache-2.0** — multilingual clone (10 langs) + delivery instructions
  ("speak slowly"). Sizes: 0.6B=~1.7GB, 1.7B heavier. Use 0.6B on low-RAM.
- `hexgrad/Kokoro-82M` ✅ 8k · **Apache-2.0** — NOT cloning (50 built-in voices only), but
  **312MB**, tiny/fast/CPU. Best always-on default narrator for low-RAM boxes.
- `swivid/F5-TTS` ✅ 14.9k · **MIT** (switched from MPL) — zero-shot clone (10s ref), ~1.3GB,
  maintained. Best STANDALONE clone engine if you skip a bundled app.
- `fishaudio/GPT-SoVITS` ✅ 59.9k · **MIT** — few-shot clone (1-2s), 50+ langs. Heavy (~2-3GB);
  RAM-hungry, not for 6GB box.
- `jamiepine/voicebox` ✅ 42k · **MIT** — local-first voice STUDIO bundling 7 engines
  (Qwen3-TTS, Chatterbox Multilingual/Turbo, LuxTTS, Kokoro, Qwen CustomVoice, HumeAI TADA)
  behind ONE headless FastAPI server + built-in MCP. Clones via zero-shot.
  KEY: models are NOT bundled — downloaded on-demand from HF, cached after.
  Load/unload one engine at a time via REST: `POST /models/load`, `POST /models/{name}/unload`.
  Run backend-only (`python -m backend.main --port 17493`) to skip the GUI and save RAM.
  HumeAI TADA backend is fully LOCAL (imports torch + DAC shim, no cloud key).

### ❌ Rejected for a published MIT project (verified reasons)
- `fishaudio/fish-speech` — **Fish Audio Research License = NON-COMMERCIAL**. Commercial use
  forbidden. GitHub shows "NOASSERTION" hiding this. REJECT.
- `debpalash/OmniVoice-Studio` — **AGPL-3.0**. Network use forces source disclosure. REJECT.
- `coqui-ai/TTS` (XTTS) — **MPL-2.0** (file-level copyleft) AND repo **archived ~2y**. REJECT
  for new builds (legacy wiring only).
- `OPENVOICE222/OpenVoice` (myshell) — MIT but **last push Apr 2025 (stale/dead)**. Avoid.
- `microsoft/VibeVoice` — MIT, but **TTS code REMOVED** by Microsoft (only ASR + Realtime-0.5B
  remain, fixed voices, no cloning). VibeVoice-ASR is 15.9GB (won't run on 6GB). REJECT for clone.
- `RVC-Project/Retrieval-based-Voice-Conversion` — MIT, but **voice CONVERSION** (transform
  existing audio), NOT text-to-speech. Wrong tool for script→narration.
- ElevenLabs / Azure / cloud TTS — paid + data-leaves-box. Breaks zero-cost + privacy.

### Low-RAM (6GB, no GPU) deployment pattern
- Default narrator = **Kokoro (312MB)**. Always-on, comfortable.
- Clone engine = load **ONE** at a time, on-demand, then unload:
  Chatterbox Turbo (350M, lightest clone) or Qwen3-TTS 0.6B preferred.
  NEVER load TADA 3B / Chatterbox Multilingual / Qwen 1.7B simultaneously (OOM).
- Voicebox: run headless backend only, load 1 engine per job, `POST /models/{name}/unload`
  after, kill backend process entirely when video job done → zero RAM footprint until next run.
- Disk: plan +5-8GB for cached model weights after first use; undownloaded engines stay absent.

## ERP / CRM / Finance
- `frappe/erpnext` ✅ 36.7k · GPL-3.0 — full ERP
- `odoo/odoo` ✅ 52.9k · — ERP suite
- `nocobase/nocobase` ✅ 23.3k · — no-code CRM builder
- `twentyhq/twenty` ✅ 52.7k · — Salesforce alt CRM
- `mautic/mautic` ✅ 10.1k · — marketing automation
- `InvoicePlane/InvoicePlane` ✅ 3.1k · — invoicing
- `chatwoot/chatwoot` ✅ 34.3k · — support/omnichannel

## Agent frameworks / orchestration
- `crewAIInc/crewAI` ✅ 55.3k · MIT — role-based teams
- `OpenHands/OpenHands` ✅ 80.3k · Open — autonomous SWE
- `FoundationAgents/MetaGPT` ✅ 69.3k · MIT — AI software company
- `microsoft/autogen` ✅ 59.6k · CC-BY-4.0 — multi-agent
- `langchain-ai/langgraph` ✅ 37k · MIT — resilient workflows
- `GreenSheep01201/claw-empire` ✅ 1.3k · Apache-2.0 — CEO desk
- `markus-global/markus` ✅ 166 · AGPL-3.0 — AI workforce OS

## Memory / knowledge / brain
- `mem0ai/mem0` ✅ 60.5k · Apache-2.0 — long-term memory
- `getzep/graphiti` ✅ 28.6k · Apache-2.0 — knowledge graph
- `open-webui/open-webui` ✅ 144.9k · — knowledge portal
- `docling-project/docling` ✅ 62.9k · MIT — document parsing
- `pgvector/pgvector` ✅ 22.1k · — vector search in Postgres

## Infra / IAM / observability
- `keycloak/keycloak` ✅ 35.6k · Apache-2.0 — IAM
- `Infisical/infisical` ✅ 27.8k · — secrets
- `coollabsio/coolify` ✅ 58.2k · Apache-2.0 — self-host PaaS
- `minio/minio` ✅ 61.3k · AGPL-3.0 — S3 storage
- `grafana/grafana` ✅ 75.5k · AGPL-3.0 — observability
- `n8n-io/n8n` ✅ 195.9k · — workflow automation

## OpenClaw ecosystem
- `openclaw/openclaw` ✅ 382.5k · — main assistant
- `openclaw/clawhub` ✅ 9.1k · TS — skill/plugin registry (clawhub.ai)
- Trending ClawHub skills: self-improving agent, Skill Vetter, SkillScan (security gate),
  ontology (memory graph), Github (@steipete), Gog (@steipete, Google Workspace)

## Compulsory baseline (every company, 20 projects)
Keycloak, Infisical, PostgreSQL, MinIO, Docker+Coolify, Prometheus+Grafana+Loki, NATS,
ERPNext, Postal+Listmonk, Outline+OpenWebUI, Mem0+pgvector, n8n, Hermes+CrewAI+LangGraph,
Agent-Reach+SearXNG, Chatwoot, Matomo, Gitea+Forgejo, Plane, Wazuh.
(For non-AI companies drop memory/orchestration/research — other 17 are universal.)
