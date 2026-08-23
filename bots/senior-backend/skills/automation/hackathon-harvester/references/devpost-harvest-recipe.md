# Devpost Harvest Recipe (verified 2026-08-01)

## The problem
`curl https://devpost.com/hackathons?online=1&prize=1` → **HTTP 403** (Cloudflare),
even with a browser User-Agent. The JSON API (`/api/hackathons.json`) is also hard 403.

## The fix: Jina Reader
Jina strips the page to clean markdown and is NOT Cloudflare-blocked:
```bash
curl -sL -m 30 -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" \
  "https://r.jina.ai/https://devpost.com/hackathons?online=1&prize=1"
# HTTP 200, ~15 KB markdown, one card per hackathon
```
This is exactly what agent-reach's zero-config `web` channel does — reuse it.

## Card format in the markdown
```
### <name> <N days left | about 1 month left | 2 months left> <Online|In-person> $<prize> in prizes **<participants>** participants <HOST> <Mon DD - Mon DD, YYYY> <theme1/theme2 ...>
(https://<slug>.devpost.com/...)
```

## Verified parsing regex (handles all 3 "days left" forms + nav-token filter)
```python
_CARD_RE = re.compile(
    r"###\s+"
    r"(?P<name>(?=[A-Za-z][\w&/.:' -]*[A-Za-z])"
    r"(?!Back\s*\]|Log in|Sign up|Join|Host|Resources|Most relevant|Recently added|Submission date)[^\n]+?)\s+"
    r"(?P<left>(?P<days>\d+)\s+days\s+left|about\s+1\s+month\s+left|2\s+months?\s+left)\s+"
    r"(?P<mode>Online|In-person|Hybrid)\s+"
    r"\$(?P<prize>[\d,]+)\s+in\s+prizes\s+"
    r"(?:\*\*(?P<parts>[\d,]+)\*\*\s+participants\s+)?"
    r"(?P<host>[A-Za-z0-9][^\n]*?)\s+"
    r"(?P<dates>[A-Z][a-z]{2}\s+\d{1,2}\s*-\s*[A-Z][a-z]{2}\s+\d{1,2},\s*\d{4})"
    r"(?P<themes>.*?)(?=\n|\[https|\(https|###|\Z)",
    re.DOTALL,
)
```
Normalize: `N days left`→N, `about 1 month left`→30, `2 months left`→60.

## Real live sample (captured this session, Devpost online+prize)
| Prize | Days left | Name | Host |
|---|---|---|---|
| $2,000,000 | 17 | Build with Gemini XPRIZE | XPRIZE |
| $685,000 | 60 | RevenueCat Shipaton 2026 | RevenueCat |
| $75,000 | 30 | Agentic Cinema: The Blockbuster Hackathon | Google |
| $20,500 | 10 | Build with DataHub: The Agent Hackathon | DataHub |
| $10,000 | 30 | CALL-E: Your Code Is Calling | CALL-E |
| $10,000 | 3 | Backblaze Generative Media Hackathon | Backblaze |
| $8,750 | 18 | CockroachDB × AWS Hackathon | Cockroach Labs |
| $8,000 | 14 | Arm Create: AI Optimization Challenge | arm |
| $6,000 | 16 | YouCam API Skin AI & Apparel VTO Hackathon | Perfect Corp |

## Pitfalls
- Jina **rate-limits rapid repeats** (503/403 AbuseAlleviationError). Cache the
  markdown to a file and parse that; don't re-fetch in a loop.
- `&page=N` returns the SAME ~24 cards — the filter view is capped, not paginated.
  Vary the filter to widen coverage.
- HackerEarth raw HTML loads (200) but is JS-rendered (no card data in body) → use
  Jina there too.
