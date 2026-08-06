from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from dailywire.config import Config, PodcastConfig, Source
from dailywire.models import Cluster, Item


def make_item(
    title: str,
    *,
    source: str = "Example News",
    url: str | None = None,
    category: str = "world",
    weight: float = 1.0,
    age_hours: float = 1.0,
    summary: str = "",
    hn_points: int = 0,
) -> Item:
    return Item(
        title=title,
        url=url or f"https://example.com/{abs(hash((title, source))):x}",
        source=source,
        category=category,
        source_weight=weight,
        summary=summary or title,
        published=datetime.now(timezone.utc) - timedelta(hours=age_hours),
        hn_points=hn_points,
    )


def make_cluster(title: str, *, category: str = "world", outlets: int = 1, **kwargs) -> Cluster:
    items = [
        make_item(title, source=f"Outlet {i}", url=f"https://outlet{i}.example/{title[:12]}",
                  category=category, **kwargs)
        for i in range(outlets)
    ]
    return Cluster(items=items, category=category)


@pytest.fixture
def cfg(tmp_path) -> Config:
    config = Config()
    config.root = tmp_path
    config.general.episodes_dir = "episodes"
    config.general.public_dir = "public"
    config.general.db_path = "dailywire.db"
    config.podcast = PodcastConfig(
        title="Dailywire",
        base_url="http://192.168.1.10:8000",
        description="Test briefing.",
        email="test@localhost",
    )
    config.sources = [
        Source(name="Example News", url="https://example.com/rss", category="world", weight=1.0)
    ]
    return config
