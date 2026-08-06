"""RSS/Atom ingestion."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone

import feedparser

from ..config import Source
from ..models import Item
from .http import Fetcher

log = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def clean_html(raw: str) -> str:
    """Strip tags from a feed summary without pulling in a parser."""
    if not raw:
        return ""
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    text = re.sub(r"(?i)<(br|/p|/div|/li)[^>]*>", "\n", text)
    text = _TAG_RE.sub(" ", text)
    for entity, char in (
        ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'),
        ("&#39;", "'"), ("&apos;", "'"), ("&nbsp;", " "), ("&#8217;", "'"),
        ("&hellip;", "..."), ("&mdash;", "--"), ("&ndash;", "-"),
    ):
        text = text.replace(entity, char)
    return _WS_RE.sub(" ", text).strip()


def _published(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    return None


def _entry_summary(entry) -> str:
    """Longest available body-ish field, cleaned."""
    candidates = [entry.get("summary", "")]
    for content in entry.get("content", []) or []:
        candidates.append(content.get("value", ""))
    candidates.append(entry.get("description", ""))
    return max((clean_html(c) for c in candidates if c), key=len, default="")


def parse_feed(raw: str, source: Source, *, lookback_hours: int = 24) -> list[Item]:
    """Parse feed bytes into Items, dropping anything outside the window."""
    parsed = feedparser.parse(raw)
    if parsed.bozo and not parsed.entries:
        log.warning("failed to parse feed %s: %s", source.name, parsed.get("bozo_exception"))
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    items: list[Item] = []
    for entry in parsed.entries:
        link = (entry.get("link") or "").strip()
        title = clean_html(entry.get("title", "")).strip()
        if not link or not title:
            continue
        published = _published(entry)
        if published is None:
            # No date at all: assume it is current, but only for the first few
            # entries -- feeds without dates list newest first.
            if len(items) > 10:
                continue
            published = datetime.now(timezone.utc)
        elif published < cutoff:
            continue
        items.append(
            Item(
                title=title,
                url=link,
                source=source.name,
                category=source.category,
                source_weight=source.weight,
                summary=_entry_summary(entry),
                published=published,
                author=clean_html(entry.get("author", "")),
            )
        )
    return items


async def fetch_source(fetcher: Fetcher, source: Source, lookback_hours: int) -> list[Item]:
    raw = await fetcher.get_text(source.url)
    if raw is None:
        return []
    items = parse_feed(raw, source, lookback_hours=lookback_hours)
    log.info("%s: %d items", source.name, len(items))
    return items


async def fetch_all(fetcher: Fetcher, sources: list[Source], lookback_hours: int) -> list[Item]:
    results = await asyncio.gather(
        *(fetch_source(fetcher, s, lookback_hours) for s in sources), return_exceptions=True
    )
    items: list[Item] = []
    for source, result in zip(sources, results):
        if isinstance(result, BaseException):
            log.warning("source %s failed: %s", source.name, result)
            continue
        items.extend(result)
    return items
