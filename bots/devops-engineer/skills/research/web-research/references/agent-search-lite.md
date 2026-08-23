# Agent Search Lite (User's Free Search Package)

**Repo**: https://github.com/itsPremkumar/agent-search-lite
**Version**: v2.3.0
**License**: MIT
**Purpose**: Completely free, zero-API-key web search + content extraction for AI agents.

This is the user's own package — a stripped-down, English-only version of Panniantong/agent-reach. It supersedes the upstream agent-reach for free search in this environment.

## When to use

- User asks to research/search anything online and wants a free solution
- Building new features that need web search without paid API keys
- Contributing to open-source projects that need free web access

## Backends (parallel execution)

| Backend | How | Key |
|---------|-----|-----|
| **DDGS** | Pure Python DDG | Optional, `pip install ddgs` |
| **Jina Reader + DDG HTML** | Free web search | Always works |
| **GitHub CLI** | Code/repo search | Via `gh` CLI |
| **HackerNews Algolia** | Tech news | Free API |

## Key features

- **Query expansion**: 3-5 reformulations per query
- **Site operators**: `site:github.com`, `site:wikipedia.org`
- **Date filters**: `after:YYYY-MM-DD`, `before:YYYY-MM-DD`
- **Pollution detection**: Auto-filters spam
- **Result ranking**: relevance + verification + quality scores
- **SSR extraction**: JSON-LD, microdata, readability scoring
- **Token-conscious formatting**: Minimizes LLM token usage

## Hermes Plugin

The plugin lives in `plugins/web/agentreach/` in the hermes-agent fork:
- `itsPremkumar/hermes-agent` branch `feat/agentreach-free-search`
- PR #87765 to NousResearch/hermes-agent (OPEN)

## Usage

```python
from agent_search.core import AgentSearchLite
search = AgentSearchLite()
result = search.search("query", mode="code")
results = search.extract(["https://example.com"])
```

```bash
agent-search-lite search "query" --site github.com --after 2024-01-01
agent-search-lite extract https://example.com
agent-search-lite doctor
```

## Attribution

- Based on Agent Reach by Panniantong (MIT)
- Query expansion inspired by brcrusoe72/agent-search (MIT)
- SSR extraction inspired by telly6/searchpin (MIT)
- Ranking inspired by drmikecrypto/WebSearchFree (MIT)

## Notes

- HN API: use Algolia (`https://hn.algolia.com/api/v1`), NOT Firebase (broken/301)
- Reddit: currently 403 blocked, removed from backends
- SearXNG: optional Docker setup at `scripts/setup-searxng.sh`
- Jina Reader: rate-limits rapid repeats; cache results
