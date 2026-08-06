"""Full-text extraction for items whose feed only carried a snippet."""

from __future__ import annotations

import asyncio
import logging

from ..config import IngestConfig
from ..models import Item
from .http import Fetcher

log = logging.getLogger(__name__)

_HTML_TYPES = ("text/html", "application/xhtml")


def extract_text(html: str, url: str = "") -> str:
    """Pull the article body out of a page.

    trafilatura first (best precision), readability-lxml as a fallback. Both
    are optional at runtime: without them we just keep the feed snippet.
    """
    try:
        import trafilatura

        text = trafilatura.extract(
            html, url=url or None, include_comments=False, include_tables=False, favor_precision=True
        )
        if text and len(text) > 200:
            return text.strip()
    except ImportError:
        pass
    except Exception as exc:
        log.debug("trafilatura failed on %s: %s", url, exc)

    try:
        from readability import Document

        from .rss import clean_html

        text = clean_html(Document(html).summary())
        if text and len(text) > 200:
            return text.strip()
    except ImportError:
        pass
    except Exception as exc:
        log.debug("readability failed on %s: %s", url, exc)

    return ""


def needs_full_text(item: Item, threshold: int) -> bool:
    if item.full_text:
        return False
    if item.url.startswith("https://arxiv.org/abs/"):
        return False  # the abstract is the whole point
    if item.url.startswith("https://news.ycombinator.com/"):
        return False  # a comment thread, not an article
    return len(item.summary) < threshold


async def hydrate_one(fetcher: Fetcher, item: Item) -> None:
    resp = await fetcher.get(item.url)
    if resp is None:
        return
    content_type = resp.headers.get("content-type", "")
    if content_type and not any(t in content_type for t in _HTML_TYPES):
        return
    text = extract_text(resp.text, item.url)
    if text:
        item.full_text = text
        log.debug("extracted %d chars from %s", len(text), item.url)


async def hydrate(fetcher: Fetcher, items: list[Item], cfg: IngestConfig) -> list[Item]:
    """Fill in full_text for snippet-only items, newest and best-sourced first."""
    if not cfg.fetch_full_text:
        return items

    candidates = [i for i in items if needs_full_text(i, cfg.snippet_threshold)]
    candidates.sort(key=lambda i: (-i.source_weight, -i.hn_points, i.age_hours))
    candidates = candidates[: cfg.max_full_text_fetches]
    if not candidates:
        return items

    log.info("fetching full text for %d of %d items", len(candidates), len(items))
    await asyncio.gather(
        *(hydrate_one(fetcher, item) for item in candidates), return_exceptions=True
    )
    return items
