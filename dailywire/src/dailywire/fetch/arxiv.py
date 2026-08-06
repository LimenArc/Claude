"""New arXiv submissions for the configured categories.

Uses the public export API (Atom). arXiv asks callers to leave at least three
seconds between requests, which is enforced here regardless of the global
per-domain delay.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import feedparser

from ..config import ArxivConfig
from ..models import Item
from .http import Fetcher
from .rss import clean_html

log = logging.getLogger(__name__)

API = "http://export.arxiv.org/api/query"
ARXIV_MIN_DELAY = 3.0
ABS_URL = "https://arxiv.org/abs/{}"


def _arxiv_id(entry_id: str) -> str:
    return entry_id.rsplit("/abs/", 1)[-1] if "/abs/" in entry_id else entry_id.rsplit("/", 1)[-1]


def parse_response(raw: str, category: str, *, lookback_hours: int = 24) -> list[Item]:
    parsed = feedparser.parse(raw)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    items: list[Item] = []
    for entry in parsed.entries:
        published = None
        for key in ("published_parsed", "updated_parsed"):
            if entry.get(key):
                published = datetime(*entry[key][:6], tzinfo=timezone.utc)
                break
        if published is None or published < cutoff:
            continue
        title = clean_html(entry.get("title", "")).strip()
        if not title:
            continue
        paper_id = _arxiv_id(entry.get("id", ""))
        authors = ", ".join(a.get("name", "") for a in entry.get("authors", []) or [])
        items.append(
            Item(
                title=title,
                url=ABS_URL.format(paper_id) if paper_id else entry.get("link", ""),
                source=f"arXiv {category}",
                category="ai",
                source_weight=0.85,
                summary=clean_html(entry.get("summary", "")),
                published=published,
                author=authors,
                extra={"arxiv_id": paper_id, "arxiv_category": category},
            )
        )
    return items


async def fetch(fetcher: Fetcher, cfg: ArxivConfig, lookback_hours: int = 24) -> list[Item]:
    if not cfg.enabled or not cfg.categories:
        return []

    per_category = max(5, cfg.max_items)
    items: list[Item] = []
    for index, category in enumerate(cfg.categories):
        if index:
            await asyncio.sleep(ARXIV_MIN_DELAY)
        raw = await fetcher.get_text(
            API,
            check_robots=False,  # documented API endpoint, not a crawlable page
            params={
                "search_query": f"cat:{category}",
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "max_results": str(per_category),
            },
        )
        if raw is None:
            continue
        found = parse_response(raw, category, lookback_hours=lookback_hours)
        log.info("arXiv %s: %d new submissions", category, len(found))
        items.extend(found)

    # A paper cross-listed in cs.AI and cs.LG arrives twice.
    unique: dict[str, Item] = {}
    for item in items:
        unique.setdefault(item.url, item)
    return list(unique.values())[: cfg.max_items]
