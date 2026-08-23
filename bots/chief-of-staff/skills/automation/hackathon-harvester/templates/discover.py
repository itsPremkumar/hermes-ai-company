"""hackharvest.discover — pull LIVE online hackathons with cash prizes.

Stdlib-only (urllib + re). Uses Jina Reader (agent-reach 'web' channel) to bypass
Devpost's Cloudflare 403 on raw scraping. Verified 2026-08-01 against live data.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone

DEVPOST_PRIZE_URL = "https://devpost.com/hackathons?online=1&prize=1"
JINA_ENDPOINT = "https://r.jina.ai/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


@dataclass
class Hackathon:
    name: str
    url: str
    prize_usd: int | None
    prize_text: str
    days_left: int | None
    deadline: str
    host: str
    mode: str = "online"
    themes: list[str] = field(default_factory=list)
    participants: int | None = None
    source: str = "devpost"
    fetched_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def fetch_markdown(url: str, timeout: int = 30) -> str:
    target = JINA_ENDPOINT + url
    req = urllib.request.Request(target, headers={"User-Agent": UA, "Accept": "text/plain"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


# One Devpost card:
#   ### Name 17 days left Online $2,000,000 in prizes **23317** participants
#   HOST Jun 30 - Aug 18, 2026 Theme1/Theme2 ...  (url)
# Name must start with a letter and not be a bare nav token (Back/Log in/...).
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


def _month_to_days(left: str) -> int:
    if left.startswith("about 1 month"):
        return 30
    if left.startswith("2 months"):
        return 60
    return 0


def _parse_prize(text: str) -> int | None:
    m = re.search(r"[\d,]+", text)
    return int(m.group(0).replace(",", "")) if m else None


def _parse_days(raw: str | None) -> int | None:
    if not raw:
        return None
    m = re.search(r"\d+", raw)
    return int(m.group(0)) if m else None


def parse_devpost_markdown(md: str) -> list[Hackathon]:
    now = datetime.now(timezone.utc).isoformat()
    results: list[Hackathon] = []
    seen = set()
    for m in _CARD_RE.finditer(md):
        url_m = re.search(r"\((https://[a-z0-9.-]+\.devpost\.com/[^)]*)\)", md[m.end():m.end() + 400])
        url = url_m.group(1) if url_m else DEVPOST_PRIZE_URL
        name = m.group("name").strip()
        key = (name, url)
        if key in seen:
            continue
        seen.add(key)
        themes = [t.strip(" ,") for t in re.split(r"[/\n]", m.group("themes") or "") if t.strip(" ,")]
        days_left = _parse_days(m.group("days")) if m.group("days") else _month_to_days(m.group("left") or "")
        results.append(Hackathon(
            name=name, url=url,
            prize_usd=_parse_prize(m.group("prize")),
            prize_text=f"${m.group('prize')} in prizes",
            days_left=days_left,
            deadline=m.group("dates").strip(),
            host=m.group("host").strip().split("\n")[0][:60],
            mode=m.group("mode"),
            themes=themes[:8],
            participants=int(m.group("parts").replace(",", "")) if m.group("parts") else None,
            fetched_at=now,
        ))
    return results


def discover(url: str = DEVPOST_PRIZE_URL, min_prize: int = 0, max_days: int | None = None) -> list[Hackathon]:
    md = fetch_markdown(url)
    items = parse_devpost_markdown(md)
    if min_prize:
        items = [i for i in items if (i.prize_usd or 0) >= min_prize]
    if max_days is not None:
        items = [i for i in items if (i.days_left or 10_000) <= max_days]
    items.sort(key=lambda h: h.prize_usd or 0, reverse=True)
    return items


if __name__ == "__main__":
    items = discover()
    print(json.dumps([h.to_dict() for h in items], indent=2))
    print(f"\n{len(items)} hackathons (live, cash prizes).", file=sys.stderr)
