#!/usr/bin/env python
"""Standalone, stdlib-only live probe of free LLM endpoints.

Re-run from the host before trusting the router's catalog — free-provider
reachability is time/region-sensitive (see references/provider-probe.md).

Usage:  python scripts/probe_providers.py
Prints per-endpoint HTTP status + whether a chat body came back.

No API keys, no pip deps.
"""
import json
import urllib.request
import urllib.error

ENDPOINTS = [
    ("pollinations_text", "https://text.pollinations.ai/openai/chat/completions", "openai"),
    ("opencode_zen/models", "https://api.opencode.ai/zen/v1/models", None),
    ("opencode_zen/chat", "https://api.opencode.ai/zen/v1/chat/completions", "gpt-5"),
    ("opencode_go/chat", "https://api.opencode.ai/go/v1/chat/completions", "gpt-5"),
    ("kilocode/models", "https://api.kilo.ai/api/openrouter/models", None),
    ("pollinations_gen", "https://gen.pollinations.ai/openai/chat/completions", "openai"),
    ("freemodel_dev", "https://api.freemodel.dev/chat/completions", "auto"),
]

CHAT_BODY = json.dumps({
    "model": "{model}",
    "messages": [{"role": "user", "content": "hi"}],
    "temperature": 0,
}).encode()


def probe(name, url, chat_model):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "Authorization": "Bearer anonymous",
    }
    try:
        data = CHAT_BODY.format(model=chat_model) if chat_model else None
        req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
        with urllib.request.urlopen(req, timeout=12) as r:
            body = r.read(200).decode("utf-8", "ignore")
            print(f"  [200] {name}  -> {body[:60].strip()}")
    except urllib.error.HTTPError as e:
        print(f"  [HTTP {e.code}] {name}  {e.reason}")
    except Exception as e:  # noqa: BLE001
        print(f"  [ERR ] {name}  {type(e).__name__}: {str(e)[:60]}")


if __name__ == "__main__":
    print("=== free provider live probe ===")
    for name, url, model in ENDPOINTS:
        probe(name, url, model)
    print("=== done (status is region/time sensitive; re-run before trusting) ===")
