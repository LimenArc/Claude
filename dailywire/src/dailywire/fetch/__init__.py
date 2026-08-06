"""Ingestion: RSS/Atom feeds, Hacker News, arXiv, plus full-text extraction."""

from __future__ import annotations

import logging

from ..config import Config
from ..models import Item
from . import arxiv, extract, hackernews, rss
from .http import Fetcher

log = logging.getLogger(__name__)

__all__ = ["Fetcher", "arxiv", "extract", "hackernews", "rss", "ingest"]


async def ingest(cfg: Config) -> list[Item]:
    """Run every configured source and return all fresh items."""
    async with Fetcher(cfg.ingest) as fetcher:
        items = await rss.fetch_all(fetcher, cfg.sources, cfg.ingest.lookback_hours)
        items += await hackernews.fetch(fetcher, cfg.ingest.hackernews, cfg.ingest.lookback_hours)
        items += await arxiv.fetch(fetcher, cfg.ingest.arxiv, cfg.ingest.lookback_hours)
        log.info("ingested %d items from %d feeds", len(items), len(cfg.sources))
        await extract.hydrate(fetcher, items, cfg.ingest)
    return items
