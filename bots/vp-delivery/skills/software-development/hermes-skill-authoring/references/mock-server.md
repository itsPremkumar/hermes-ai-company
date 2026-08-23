# Mock OpenAI-compatible server (for testing skill helpers)

Use this to verify a `bin/` helper's happy path WITHOUT hitting a real LLM.
It returns a deterministic "refined" string so you can assert the parse/output
logic of the real script.

```python
# hermes-verify-mock.py  — run: python <this> <PORT>
import http.server, json, sys

class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(n))
        user = body['messages'][-1]['content']
        refined = "REFINED: " + user.strip().capitalize()
        out = {"choices": [{"message": {"content": refined}}]}
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(out).encode())
    def log_message(self, *a):
        pass

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8899
http.server.HTTPServer(('127.0.0.1', PORT), H).serve_forever()
```

Launch it as a background process (terminal background=true), then point the
helper at `http://127.0.0.1:<PORT>/v1` by `sed`-replacing the real base_url in a
temp copy of the script. Assert the helper prints `REFINED: ...`.

## Verification harness shape

A Python script that: (1) spawns the mock, (2) builds a temp copy of the helper
with the mock URL, (3) runs guardrail / happy / dead-endpoint cases via
`subprocess.run(["bash", tmp], ...)`, (4) asserts returncodes + stdout, (5) cleans
up temp files. Use an OS-safe temp path with `hermes-verify-` prefix.
