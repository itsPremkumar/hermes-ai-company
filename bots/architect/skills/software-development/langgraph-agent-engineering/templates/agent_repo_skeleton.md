# New domain-agent repo skeleton (copy + modify)

Layout for each project built on `langgraph-agent-kit`:

```
<repo-name>/
  pyproject.toml            # depends on kit via file://../langgraph-agent-kit
  README.md                 # SEO/GEO/AEO: badges, feature table, quickstart, arch diagram
  .env.example
  Dockerfile                # default CMD runs `pytest -q`
  .github/
    workflows/ci.yml        # matrix py3.10/3.11/3.12; install, ruff, pytest, docker build
    workflows/release.yml   # tag-driven GH release
    ISSUE_TEMPLATE/bug_report.yml
    ISSUE_TEMPLATE/feature_request.yml
    PULL_REQUEST_TEMPLATE.md
  <package>/
    __init__.py             # export build fn + config + state
    state.py                # ProjectState(BaseAgentState, total=False) + domain channels
    config.py               # ProjectConfig(AgentSettings) with env_prefix
    prompts.py              # register versioned prompts via PromptManager
    tools.py                # ToolRegistry: offline-fallback tools + real adapters
    graph.py                # build_<x>_graph(): planner/researcher/verifier/synthesizer nodes
    cli.py                  # `main()` entry (argparse) calling app.ainvoke
  tests/
    __init__.py
    test_core.py            # offline: FakeLLM + offline tools; assert final/done/stream
  docs/                     # architecture.md, api.md, deployment.md (link from README)
  data/                     # gitignored; sqlite checkpoints/cache/memory
```

## pyproject.toml dependency line
```toml
dependencies = [
  "langgraph-agent-kit @ file:///${PROJECT_ROOT}/../langgraph-agent-kit",
]
```
(Change to a published version once the kit is released: `"langgraph-agent-kit>=0.1.0"`.)

## Minimal build entrypoint
```python
from langgraph_agent_kit import FakeLLM, ToolRegistry, PromptManager, build_reflective_agent
from .config import load_config
from .tools import build_default_registry

def build_app(checkpoint_path=None):
    cfg = load_config()
    llm = FakeLLM(model="fake")            # swap for OpenAI/Anthropic in prod
    tools = build_default_registry()
    return build_reflective_agent(llm=llm, tools=tools, checkpoint_path=checkpoint_path)

if __name__ == "__main__":
    import asyncio
    out = asyncio.run(build_app().ainvoke({"meta": {"goal": "..."}, "messages": [],
        "scratchpad": [], "results": [], "sources": [], "errors": [],
        "iterations": 0, "done": False, "final_answer": ""}))
    print(out["final_answer"])
```

## Quality gate before marking "done"
- [ ] `pytest -q` passes offline (no API keys)
- [ ] `ruff check .` clean
- [ ] `Dockerfile` builds and its `CMD` (pytest) exits 0
- [ ] CI matrix green (3.10/3.11/3.12)
- [ ] README has badges, feature table, quickstart, architecture sketch
- [ ] Every bug hit during dev became a regression test
