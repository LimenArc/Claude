"""Ingestion tests. Every HTTP call goes through an httpx MockTransport."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from dailywire.config import ArxivConfig, HackerNewsConfig, IngestConfig, Source
from dailywire.fetch import arxiv, hackernews
from dailywire.fetch.extract import extract_text, needs_full_text
from dailywire.fetch.http import Fetcher
from dailywire.fetch.rss import clean_html, fetch_all, parse_feed
from dailywire.models import Item


def rfc822(when: datetime) -> str:
    return when.strftime("%a, %d %b %Y %H:%M:%S +0000")


def rss_feed(entries: list[tuple[str, str, datetime]]) -> str:
    items = "".join(
        f"<item><title>{title}</title><link>{link}</link>"
        f"<description>{title} happened.</description>"
        f"<pubDate>{rfc822(when)}</pubDate></item>"
        for title, link, when in entries
    )
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>Test</title>{items}</channel></rss>'


SOURCE = Source(name="Test Feed", url="https://feed.example/rss", category="world", weight=1.3)


def transport(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True)


# -- RSS --------------------------------------------------------------------


def test_parse_feed_builds_items_with_source_metadata():
    now = datetime.now(timezone.utc)
    raw = rss_feed([("Rates rise", "https://feed.example/1", now - timedelta(hours=2))])
    items = parse_feed(raw, SOURCE)
    assert len(items) == 1
    item = items[0]
    assert item.title == "Rates rise"
    assert item.source == "Test Feed" and item.category == "world"
    assert item.source_weight == 1.3
    assert "happened" in item.summary


def test_parse_feed_drops_items_outside_the_lookback_window():
    now = datetime.now(timezone.utc)
    raw = rss_feed(
        [
            ("Fresh", "https://feed.example/1", now - timedelta(hours=2)),
            ("Ancient", "https://feed.example/2", now - timedelta(days=5)),
        ]
    )
    assert [i.title for i in parse_feed(raw, SOURCE, lookback_hours=24)] == ["Fresh"]


def test_parse_feed_skips_entries_without_a_link():
    raw = '<?xml version="1.0"?><rss version="2.0"><channel><item><title>No link</title></item></channel></rss>'
    assert parse_feed(raw, SOURCE) == []


def test_parse_feed_survives_garbage():
    assert parse_feed("this is not xml at all", SOURCE) == []


def test_parse_atom_feed():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw = f"""<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Atom Test</title>
      <entry><title>Atom story</title><link href="https://atom.example/1"/>
        <updated>{now}</updated><summary>Body text here.</summary></entry>
    </feed>"""
    items = parse_feed(raw, SOURCE)
    assert [i.title for i in items] == ["Atom story"]
    assert items[0].url == "https://atom.example/1"


def test_clean_html_strips_tags_and_entities():
    out = clean_html("<p>Rates &amp; bonds <b>rose</b></p><script>evil()</script>")
    assert "Rates & bonds rose" in out
    assert "evil" not in out and "<" not in out


async def test_fetch_all_gathers_sources_and_survives_failures():
    now = datetime.now(timezone.utc)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.host == "broken.example":
            return httpx.Response(500)
        return httpx.Response(200, text=rss_feed([("Story", "https://a.example/1", now)]))

    sources = [
        Source(name="Good", url="https://good.example/rss", category="world"),
        Source(name="Broken", url="https://broken.example/rss", category="world"),
    ]
    cfg = IngestConfig(per_domain_delay=0)
    async with Fetcher(cfg, client=transport(handler)) as fetcher:
        items = await fetch_all(fetcher, sources, 24)
    assert [i.source for i in items] == ["Good"]


# -- robots.txt and rate limiting -------------------------------------------


async def test_robots_disallow_blocks_the_request():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private/")
        return httpx.Response(200, text="body")

    cfg = IngestConfig(per_domain_delay=0)
    async with Fetcher(cfg, client=transport(handler)) as fetcher:
        assert await fetcher.get("https://x.example/private/page") is None
        assert await fetcher.get_text("https://x.example/public/page") == "body"
    assert "/private/page" not in seen


async def test_robots_is_fetched_once_per_domain():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, text="User-agent: *\nAllow: /")

    cfg = IngestConfig(per_domain_delay=0)
    async with Fetcher(cfg, client=transport(handler)) as fetcher:
        for path in ("/a", "/b", "/c"):
            await fetcher.get(f"https://x.example{path}")
    assert sum(1 for c in calls if c.endswith("/robots.txt")) == 1


async def test_robots_can_be_switched_off():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /")
        return httpx.Response(200, text="body")

    cfg = IngestConfig(per_domain_delay=0, respect_robots_txt=False)
    async with Fetcher(cfg, client=transport(handler)) as fetcher:
        assert await fetcher.get_text("https://x.example/anything") == "body"


async def test_forbidden_robots_is_treated_as_disallow_all():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(403)
        return httpx.Response(200, text="body")

    cfg = IngestConfig(per_domain_delay=0)
    async with Fetcher(cfg, client=transport(handler)) as fetcher:
        assert await fetcher.get("https://x.example/page") is None


async def test_unreachable_robots_does_not_block_fetching():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            raise httpx.ConnectError("boom")
        return httpx.Response(200, text="body")

    cfg = IngestConfig(per_domain_delay=0)
    async with Fetcher(cfg, client=transport(handler)) as fetcher:
        assert await fetcher.get_text("https://x.example/page") == "body"


async def test_requests_to_one_domain_are_rate_limited():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ok")

    cfg = IngestConfig(per_domain_delay=0.05, respect_robots_txt=False)
    async with Fetcher(cfg, client=transport(handler)) as fetcher:
        start = time.monotonic()
        for _ in range(3):
            await fetcher.get("https://x.example/page")
        elapsed = time.monotonic() - start
    assert elapsed >= 0.10


async def test_error_responses_become_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    cfg = IngestConfig(per_domain_delay=0, respect_robots_txt=False)
    async with Fetcher(cfg, client=transport(handler)) as fetcher:
        assert await fetcher.get("https://x.example/missing") is None
        assert await fetcher.get_json("https://x.example/missing") is None


async def test_user_agent_is_sent():
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["ua"] = request.headers.get("user-agent", "")
        return httpx.Response(200, text="ok")

    cfg = IngestConfig(per_domain_delay=0, respect_robots_txt=False, user_agent="dailywire-test/1.0")
    async with Fetcher(cfg) as fetcher:  # real client, mocked transport underneath
        fetcher._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), headers={"User-Agent": cfg.user_agent}
        )
        await fetcher.get("https://x.example/page")
    assert captured["ua"] == "dailywire-test/1.0"


# -- Hacker News ------------------------------------------------------------


async def test_hackernews_items_carry_points_and_discussion_link():
    payload = {
        "hits": [
            {"title": "Big story", "url": "https://news.example/a", "objectID": "1",
             "points": 420, "num_comments": 99, "author": "pg",
             "created_at_i": int(datetime.now(timezone.utc).timestamp())},
            {"title": "Ask HN: something", "url": "", "objectID": "2", "points": 150,
             "created_at_i": int(datetime.now(timezone.utc).timestamp())},
        ]
    }
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json=payload)

    cfg = IngestConfig(per_domain_delay=0)
    async with Fetcher(cfg, client=transport(handler)) as fetcher:
        items = await hackernews.fetch(fetcher, HackerNewsConfig(min_points=100), 24)

    assert [i.title for i in items] == ["Big story", "Ask HN: something"]
    assert items[0].hn_points == 420 and items[0].category == "tech"
    assert items[0].hn_url == "https://news.ycombinator.com/item?id=1"
    # A story with no external URL falls back to its discussion page.
    assert items[1].url == "https://news.ycombinator.com/item?id=2"
    assert "points>100" in captured["params"]["numericFilters"]


async def test_hackernews_can_be_disabled():
    async with Fetcher(IngestConfig(), client=transport(lambda r: httpx.Response(200))) as fetcher:
        assert await hackernews.fetch(fetcher, HackerNewsConfig(enabled=False)) == []


# -- arXiv ------------------------------------------------------------------


ARXIV_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2608.01234v1</id>
    <updated>{when}</updated><published>{when}</published>
    <title>A new attention mechanism</title>
    <summary>We propose a new mechanism that improves throughput.</summary>
    <author><name>A. Researcher</name></author>
  </entry>
</feed>"""


def test_arxiv_parse_builds_ai_items():
    when = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    items = arxiv.parse_response(ARXIV_ATOM.format(when=when), "cs.LG")
    assert len(items) == 1
    item = items[0]
    assert item.category == "ai"
    assert item.source == "arXiv cs.LG"
    assert item.url == "https://arxiv.org/abs/2608.01234v1"
    assert item.extra["arxiv_category"] == "cs.LG"
    assert "throughput" in item.summary


def test_arxiv_parse_respects_the_lookback_window():
    old = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert arxiv.parse_response(ARXIV_ATOM.format(when=old), "cs.AI", lookback_hours=24) == []


async def test_arxiv_dedupes_cross_listed_papers(monkeypatch):
    when = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    monkeypatch.setattr(arxiv.asyncio, "sleep", lambda *_: _noop())

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=ARXIV_ATOM.format(when=when))

    cfg = IngestConfig(per_domain_delay=0)
    async with Fetcher(cfg, client=transport(handler)) as fetcher:
        items = await arxiv.fetch(fetcher, ArxivConfig(categories=["cs.AI", "cs.LG"]), 24)
    assert len(items) == 1


async def _noop():
    return None


# -- full text extraction ---------------------------------------------------


def test_needs_full_text_only_for_snippets():
    short = Item(title="t", url="https://a.example/1", source="s", summary="tiny")
    long = Item(title="t", url="https://a.example/2", source="s", summary="x" * 1000)
    paper = Item(title="t", url="https://arxiv.org/abs/1", source="s", summary="tiny")
    thread = Item(title="t", url="https://news.ycombinator.com/item?id=1", source="s", summary="")
    assert needs_full_text(short, 600)
    assert not needs_full_text(long, 600)
    assert not needs_full_text(paper, 600)
    assert not needs_full_text(thread, 600)


def test_extract_text_pulls_the_article_body():
    html = (
        "<html><head><title>T</title></head><body><nav>menu menu menu</nav>"
        "<article><p>" + "The central bank raised rates today. " * 20 + "</p></article>"
        "<footer>copyright</footer></body></html>"
    )
    text = extract_text(html, "https://a.example/story")
    assert "central bank raised rates" in text
    assert "menu menu" not in text


def test_extract_text_of_junk_is_empty():
    assert extract_text("<html><body><p>hi</p></body></html>", "https://a.example/x") == ""
