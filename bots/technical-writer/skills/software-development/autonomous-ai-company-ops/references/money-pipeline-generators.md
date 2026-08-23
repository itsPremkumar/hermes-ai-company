# Money-pipeline generators — verified pattern (2026-07-13)

Turn the `ai-company` free-OSS blueprint into runnable, sellable income tooling.
Built this session: 3 pipelines → 18 ready-to-sell package JSONs + a dashboard, all
stdlib-only, 95–99% margin, live on GitHub.

## Layout
```
money/
├── MONEY_AUTOMATION_IDEAS.md        # research + 12-pipeline ranked idea bank
├── pipeline1_fiverr_gig_factory.py  # 8 services  -> gigs/*.json
├── pipeline2_cold_email_agency.py   # 5 niches    -> email_packs/*.json
├── pipeline3_video_service.py       # 5 formats   -> video_packs/*.json  (uses Automated-Video-Generator)
├── run_all.py                       # orchestrator -> regenerates all + INCOME_DASHBOARD.md
├── INCOME_DASHBOARD.md              # auto-generated summary
└── README.md
```

## Each pipeline module contract
- Module-level dict `DATA = {key: {title/gig_title, pricing/price, tags, ...}}`.
- `build_*(key, price=None) -> dict` returns a package incl. an n8n/render **manifest stub**
  (nodes + connections, or a render manifest for video).
- argparse with: `--list`, `--<selector>` (service/niche/format), `--out <file>`,
  and a positional `cmd` defaulting to `self-test`.
- `self-test` loops ALL keys and asserts: required keys present, margin_pct correct,
  manifest node count, step count. REAL asserts — never `return 0`.

## run_all.py orchestrator
- Import each module by path (works regardless of CWD):
  ```python
  import importlib.util, os
  def load_module(name):
      path = os.path.join(HERE, name + ".py")
      spec = importlib.util.spec_from_file_location(name, path)
      mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
  ```
- `price_of(pkg)` normalizes across shapes: `pkg["pricing"]["price"]` OR `["setup"]` OR `pkg["price"]`.
- Regenerate every package JSON, then write `INCOME_DASHBOARD.md`: per-pipeline table
  (count / price range / recurring?), combined one-time value, 90-day target.
- `self-test` asserts `len(rows) == 18` and 3 distinct pipelines; `--dry-run` prints totals
  without writing.

## Validated 2026 income figures (from web-research, use for pricing)
- n8n freelancers: $800–$2,500/project + $99–$149/mo retainer; solo 5 retainers+2 projects
  → $3k–$5k/mo in 6–12mo (affstudio.org).
- Fiverr AI gigs grew 340% YoY Q1 2026; email-automation gig $350–$800 price, $3–$8 AI cost
  = 95–99% margin (betonai.net).
- Workflow-automation market $23.77B (2025) → $37.45B (2030); 76% of businesses want
  automation but lack in-house skills.
- Video service (self-hosted Remotion+Edge-TTS): $150–$500/video, ~$0 API cost = ~99% margin.

## Pitfalls (all hit this session)
- f-string with backslash in `{}` → compute into a var first.
- literal `{}` in an f-string → drop the `f` (plain template string) or double to `{{}}`.
- helper defined after use in a one-shot verify script → define helpers at the TOP.
- verify then DELETE the temp `hermes-verify-*.py` so it doesn't re-trigger the unverified flag.
