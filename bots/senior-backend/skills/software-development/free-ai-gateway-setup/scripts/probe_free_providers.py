"""probe_free_providers.py — stdlib-only UP/DOWN probe for no-signup free LLM hosts.

Run:  python scripts/probe_free_providers.py
Prints [UP]/[DOWN] for each candidate endpoint with the real HTTP code + first reply
chars. Use this (or `free_llm_router check`) to verify which free models actually
answer anonymously from the CURRENT machine/region before trusting any catalog.

NOTE (verified India, 2026-07-20): only text.pollinations.ai answers with no key.
OpenCode zen/v1 -> 401, gen.pollinations.ai -> 401/522, duckduckgo -> no token,
mimocode -> 403, freemodel.dev -> 403. Catalog `noAuth:true` flags lie; probe live.
"""
import json
import sys
import urllib.request
import urllib.error

CANDIDATES = [
    ("pollinations_text", "https://text.pollinations.ai/openai/chat/completions", "openai-fast"),
    ("pollinations_gen", "https://gen.pollinations.ai/v1/chat/completions", "openai-fast"),
    ("opencode_zen", "https://opencode.ai/zen/v1/chat/completions", "kimi-k2.6"),
    ("opencode_go", "https://opencode.ai/zen/go/v1/chat/completions", "kimi-k2.6"),
    ("freemodel_dev", "https://api.freemodel.dev/v1/chat/completions", "auto"),
    ("kilo_openrouter", "https://api.kilo.ai/api/openrouter/chat/completions", "kilo-auto/free"),
]


def probe(name, url, model, timeout=12):
    payload = json.dumps(
        {"model": model, "messages": [{"role": "user", "content": "Reply with exactly: PONG"}],
         "temperature": 0, "stream": False}
    ).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "free-probe/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
            try:
                txt = json.loads(body)["choices"][0]["message"]["content"].strip()
                ok = "PONG" in txt
            except Exception:
                txt, ok = body[:60], False
            return ("UP" if ok else "DOWN"), "200 %r" % txt[:50]
    except urllib.error.HTTPError as e:
        return "DOWN", "HTTP %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:60])
    except Exception as e:  # noqa: BLE001
        return "DOWN", str(e)[:60]


def main():
    print("=== free provider probe ===")
    up = 0
    for name, url, model in CANDIDATES:
        status, detail = probe(name, url, model)
        up += status == "UP"
        print("  [%s] %-18s %s" % (status, name, detail))
    print("\nUP: %d / %d" % (up, len(CANDIDATES)))
    return 0 if up else 1


if __name__ == "__main__":
    sys.exit(main())
