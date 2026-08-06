"""End-to-end pipeline runs, with the network and the encoder stubbed out."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import fake_ffmpeg as fake_ffmpeg_mod
import pytest
from conftest import make_item
from test_audio import SilentTTS

from dailywire import pipeline
from dailywire.models import Item
from dailywire.store import Store

WHEN = date(2026, 8, 6)


def sample_items() -> list[Item]:
    """Enough coverage to satisfy the default quotas, with one duplicate story."""
    now = datetime.now(timezone.utc)
    items = [
        make_item("Central bank raises interest rates to curb inflation", source="BBC World",
                  url="https://bbc.example/rates", category="world", weight=1.2,
                  summary="The central bank raised interest rates to curb inflation."),
        make_item("Central bank raises rates in bid to curb inflation", source="Al Jazeera",
                  url="https://aj.example/rates", category="world", weight=1.1,
                  summary="Policymakers raised interest rates, aiming to curb inflation."),
        make_item("Peace talks resume in the region after months of delay", source="Deutsche Welle",
                  url="https://dw.example/talks", category="world",
                  summary="Negotiators returned to the table after months of delay."),
        make_item("Floods displace thousands as monsoon rains intensify", source="France 24",
                  url="https://f24.example/floods", category="world",
                  summary="Heavy rains forced mass evacuations."),
        make_item("New model tops the reasoning benchmark", source="MIT Technology Review",
                  url="https://mit.example/model", category="ai", weight=1.2,
                  summary="A new model set a record on a reasoning benchmark."),
        make_item("Chip maker unveils accelerator for training", source="Ars Technica",
                  url="https://ars.example/chip", category="ai",
                  summary="The accelerator targets large model training."),
        make_item("Browser ships a long-awaited privacy feature", source="The Verge",
                  url="https://verge.example/browser", category="tech",
                  summary="The feature blocks cross-site tracking by default."),
        make_item("Open source project reaches version two", source="Hacker News",
                  url="https://hn.example/project", category="tech", hn_points=430,
                  summary="The release adds a plugin system."),
    ]
    for offset, item in enumerate(items):
        item.published = now - timedelta(hours=offset)
    return items


@pytest.fixture
def stub_run(monkeypatch, tmp_path):
    """Stub ingest, TTS and ffmpeg; the rest of the pipeline is the real thing."""
    monkeypatch.setattr(pipeline, "ingest", _fake_ingest)
    monkeypatch.setattr(pipeline, "get_tts", lambda cfg, name=None: SilentTTS(seconds=1.0))
    monkeypatch.setattr(pipeline, "get_llm", lambda cfg: None)
    monkeypatch.setattr("dailywire.cluster.load_embedder", lambda name: None)
    fake_ffmpeg_mod.prepend_to_path(fake_ffmpeg_mod.install(tmp_path / "bin"), monkeypatch)


async def _fake_ingest(cfg):
    return sample_items()


def test_run_produces_audio_notes_and_feed(cfg, stub_run):
    episode = pipeline.run(cfg, pipeline.RunOptions(date=WHEN))

    assert episode is not None
    audio_path = cfg.episodes_path / "2026-08-06.mp3"
    notes_path = cfg.episodes_path / "2026-08-06.md"
    assert audio_path.exists() and audio_path.stat().st_size > 0
    assert notes_path.exists()
    assert (cfg.public_path / "feed.xml").exists()
    assert (cfg.public_path / "index.html").exists()

    notes = notes_path.read_text()
    assert "## Script" in notes and "https://bbc.example/rates" in notes


def test_run_writes_id3_chapters(cfg, stub_run):
    from mutagen.id3 import ID3

    pipeline.run(cfg, pipeline.RunOptions(date=WHEN))
    tags = ID3(str(cfg.episodes_path / "2026-08-06.mp3"))
    assert len(tags.getall("CHAP")) >= 3
    assert tags["TIT2"].text[0].endswith("2026-08-06")


def test_run_records_the_episode_and_its_stories(cfg, stub_run):
    episode = pipeline.run(cfg, pipeline.RunOptions(date=WHEN))
    with Store(cfg.db_file) as store:
        rows = store.episodes()
        assert len(rows) == 1
        assert rows[0]["date"] == "2026-08-06"
        assert rows[0]["story_count"] == len(episode.clusters)
        assert rows[0]["duration_ms"] > 0
        assert len(store.episode_stories("2026-08-06")) == len(episode.clusters)


def test_feed_enclosure_points_at_the_episode(cfg, stub_run):
    import feedparser

    pipeline.run(cfg, pipeline.RunOptions(date=WHEN))
    parsed = feedparser.parse((cfg.public_path / "feed.xml").read_text())
    assert not parsed.bozo
    assert parsed.entries[0].enclosures[0]["href"].endswith("/episodes/2026-08-06.mp3")


def test_syndicated_duplicates_are_clustered_not_repeated(cfg, stub_run):
    episode = pipeline.run(cfg, pipeline.RunOptions(date=WHEN))
    titles = [c.title for c in episode.clusters]
    assert len(titles) == len(set(titles))
    rates = [c for c in episode.clusters if "rates" in c.title.lower()]
    assert len(rates) == 1
    assert rates[0].corroboration == 2  # BBC and Al Jazeera merged


def test_second_run_finds_nothing_new(cfg, stub_run):
    assert pipeline.run(cfg, pipeline.RunOptions(date=WHEN)) is not None
    assert pipeline.run(cfg, pipeline.RunOptions(date=date(2026, 8, 7))) is None


def test_existing_episode_is_not_overwritten_without_force(cfg, stub_run):
    assert pipeline.run(cfg, pipeline.RunOptions(date=WHEN)) is not None
    (cfg.episodes_path / "2026-08-06.mp3").write_bytes(b"original")
    assert pipeline.run(cfg, pipeline.RunOptions(date=WHEN)) is None
    assert (cfg.episodes_path / "2026-08-06.mp3").read_bytes() == b"original"


def test_dry_run_writes_no_audio_and_no_database_rows(cfg, stub_run):
    episode = pipeline.run(cfg, pipeline.RunOptions(date=WHEN, dry_run=True))
    assert episode is not None and episode.script
    assert not (cfg.episodes_path / "2026-08-06.mp3").exists()
    with Store(cfg.db_file) as store:
        assert store.episodes() == []
        assert store.known_url_hashes() == set()


def test_skip_audio_keeps_the_notes_and_the_record(cfg, stub_run):
    episode = pipeline.run(cfg, pipeline.RunOptions(date=WHEN, skip_audio=True))
    assert episode is not None
    assert (cfg.episodes_path / "2026-08-06.md").exists()
    assert not (cfg.episodes_path / "2026-08-06.mp3").exists()
    with Store(cfg.db_file) as store:
        assert len(store.episodes()) == 1


def test_run_with_no_items_returns_none(cfg, monkeypatch, stub_run):
    async def empty(cfg):
        return []

    monkeypatch.setattr(pipeline, "ingest", empty)
    assert pipeline.run(cfg, pipeline.RunOptions(date=WHEN)) is None


def test_quotas_hold_across_a_real_run(cfg, stub_run):
    cfg.ranking.max_stories = 4
    episode = pipeline.run(cfg, pipeline.RunOptions(date=WHEN))
    categories = [c.category for c in episode.clusters]
    assert categories.count("world") >= 3  # the configured minimum
    assert len(episode.clusters) == 4


def test_script_is_speakable_after_a_full_run(cfg, stub_run):
    from dailywire.text import lint_speakable

    episode = pipeline.run(cfg, pipeline.RunOptions(date=WHEN))
    assert lint_speakable(episode.script) == []
