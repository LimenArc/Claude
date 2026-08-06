"""Hacker News front page via the Algolia search API.

robots.txt is not consulted for this endpoint: it is a documented public JSON
API meant to be called programmatically, not a crawlable web page. Article
pages linked *from* HN still go through the normal robots check when we fetch
their full text.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from ..config import HackerNewsConfig
from ..models import Item
from .http import Fetcher

log = logging.getLogger(__name__)

API = "https://hn.algolia.com/api/v1/search"
DISCUSSION = "https://news.ycombinator.com/item?id={}"


async def fetch(fetcher: Fetcher, cfg: HackerNewsConfig, lookback_hours: int = 24) -> list[Item]:
    if not cfg.enabled:
        return []

    since = int((datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).timestamp())
    params = {
        "tags": "story",
        "numericFilters": f"created_at_i>{since},points>{cfg.min_points}",
        "hitsPerPage": str(min(100, max(cfg.max_items * 2, 20))),
    }
    data = await fetcher.get_json(API, check_robots=False, params=params)
    if not isinstance(data, dict):
        return []

    items: list[Item] = []
    for hit in data.get("hits", []):
        title = (hit.get("title") or "").strip()
        if not title:
            continue
        object_id = str(hit.get("objectID", ""))
        discussion = DISCUSSION.format(object_id)
        url = (hit.get("url") or "").strip() or discussion
        created = hit.get("created_at_i")
        published = (
            datetime.fromtimestamp(created, tz=timezone.utc)
            if created
            else datetime.now(timezone.utc)
        )
        items.append(
            Item(
                title=title,
                url=url,
                source="Hacker News",
                category="tech",
                source_weight=0.9,
                summary=(hit.get("story_text") or "").strip(),
                published=published,
                author=hit.get("author", ""),
                hn_points=int(hit.get("points") or 0),
                hn_comments=int(hit.get("num_comments") or 0),
                hn_url=discussion,
            )
        )

    items.sort(key=lambda i: i.hn_points, reverse=True)
    items = items[: cfg.max_items]
    log.info("Hacker News: %d stories over %d points", len(items), cfg.min_points)
    return items
