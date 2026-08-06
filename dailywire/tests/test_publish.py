from __future__ import annotations

from pathlib import Path

import feedparser
import pytest
from conftest import make_cluster

from dailywire.models import Episode, Segment
from dailywire.publish import (
    build_feed,
    collect_episodes,
    episode_summary,
    format_duration,
    tag_mp3,
    warn_if_unreachable,
    write_feed,
    write_index,
)
from dailywire.store import Store

# 40 silent MPEG-1 Layer III frames: enough for mutagen to parse a real MP3.
_MP3_FRAME = bytes([0xFF, 0xFB, 0x90, 0x00]) + b"\x00" * 413


def write_mp3(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_MP3_FRAME * 40)
    return path


@pytest.fixture
def episode(cfg):
    clusters = [
        make_cluster("Central bank raises rates", category="world", outlets=2),
        make_cluster("New model tops benchmark", category="ai"),
    ]
    for cluster in clusters:
        cluster.summary = f"Summary of {cluster.title}."
    return Episode(
        date="2026-08-06",
        script="Good morning. Rates rose. A model got better. That's all.",
        segments=[
            Segment(title="Cold open", category="intro", text="Good morning.", start_ms=0, end_ms=4000),
            Segment(title="World News", category="world", text="Rates rose.", start_ms=4000, end_ms=30000),
            Segment(title="Sign-off", category="outro", text="That's all.", start_ms=30000, end_ms=36000),
        ],
        clusters=clusters,
        duration_ms=36000,
    )


@pytest.mark.parametrize(
    "ms,expected",
    [(0, "0:00"), (65_000, "1:05"), (720_000, "12:00"), (3_723_000, "1:02:03")],
)
def test_format_duration(ms, expected):
    assert format_duration(ms) == expected


def test_feed_is_valid_rss_with_itunes_namespace(cfg, episode):
    write_mp3(cfg.episodes_path / "2026-08-06.mp3")
    with Store(cfg.db_file) as store:
        store.record_episode(
            date="2026-08-06", audio_path="x.mp3", script_path="x.md", duration_ms=720_000,
            story_count=2, word_count=1500, title="Dailywire — 2026-08-06", summary="1. A\n2. B",
        )
        xml = build_feed(cfg, store)

    parsed = feedparser.parse(xml)
    assert not parsed.bozo, parsed.get("bozo_exception")
    assert parsed.version.startswith("rss")
    assert parsed.feed.title == "Dailywire"
    assert parsed.namespaces.get("itunes") == "http://www.itunes.com/dtds/podcast-1.0.dtd"
    assert len(parsed.entries) == 1

    entry = parsed.entries[0]
    assert entry.enclosures[0]["type"] == "audio/mpeg"
    assert entry.enclosures[0]["href"] == "http://192.168.1.10:8000/episodes/2026-08-06.mp3"
    assert int(entry.enclosures[0]["length"]) > 0
    assert entry.itunes_duration == "12:00"
    assert entry.published_parsed is not None
    assert entry.id == "dailywire-2026-08-06"


def test_feed_lists_newest_episode_first(cfg):
    for day in ("2026-08-04", "2026-08-05", "2026-08-06"):
        write_mp3(cfg.episodes_path / f"{day}.mp3")
    parsed = feedparser.parse(build_feed(cfg))
    assert [e.title.split("— ")[-1] for e in parsed.entries] == ["2026-08-06", "2026-08-05", "2026-08-04"]


def test_feed_is_valid_with_no_episodes(cfg):
    parsed = feedparser.parse(build_feed(cfg))
    assert not parsed.bozo
    assert parsed.entries == []


def test_feed_links_show_notes_when_present(cfg):
    write_mp3(cfg.episodes_path / "2026-08-06.mp3")
    (cfg.episodes_path / "2026-08-06.md").write_text("# notes")
    parsed = feedparser.parse(build_feed(cfg))
    html = next(c.value for c in parsed.entries[0].content if c.type == "text/html")
    assert "2026-08-06.md" in html


def test_write_feed_creates_the_public_directory(cfg):
    path = write_feed(cfg)
    assert path == cfg.public_path / "feed.xml"
    assert path.read_text().startswith("<?xml")


def test_write_index_lists_episodes(cfg):
    write_mp3(cfg.episodes_path / "2026-08-06.mp3")
    html = write_index(cfg).read_text()
    assert "/episodes/2026-08-06.mp3" in html
    assert "feed.xml" in html


def test_collect_episodes_ignores_missing_audio(cfg):
    with Store(cfg.db_file) as store:
        store.record_episode(
            date="2026-01-01", audio_path="gone.mp3", script_path="gone.md", duration_ms=1,
            story_count=1, word_count=1, title="t", summary="s",
        )
        assert collect_episodes(cfg, store) == []


def test_tag_mp3_writes_tags_and_one_chapter_per_segment(cfg, episode):
    from mutagen.id3 import ID3

    path = write_mp3(cfg.episodes_path / "2026-08-06.mp3")
    tag_mp3(path, episode, cfg)

    tags = ID3(str(path))
    assert tags["TIT2"].text[0] == "Dailywire — 2026-08-06"
    assert tags["TALB"].text[0] == "Dailywire"
    assert tags["TPE1"].text[0] == cfg.podcast.author

    chapters = tags.getall("CHAP")
    assert len(chapters) == 3
    assert {c.element_id for c in chapters} == {"chp0", "chp1", "chp2"}
    world = next(c for c in chapters if c.sub_frames["TIT2"].text[0] == "World News")
    assert (world.start_time, world.end_time) == (4000, 30000)

    toc = tags.getall("CTOC")[0]
    assert toc.child_element_ids == ["chp0", "chp1", "chp2"]


def test_tag_mp3_skips_untimed_segments(cfg, episode):
    from mutagen.id3 import ID3

    episode.segments[1].start_ms = episode.segments[1].end_ms = 0
    path = write_mp3(cfg.episodes_path / "2026-08-06.mp3")
    tag_mp3(path, episode, cfg)
    assert len(ID3(str(path)).getall("CHAP")) == 2


def test_tag_mp3_is_idempotent(cfg, episode):
    from mutagen.id3 import ID3

    path = write_mp3(cfg.episodes_path / "2026-08-06.mp3")
    tag_mp3(path, episode, cfg)
    tag_mp3(path, episode, cfg)
    assert len(ID3(str(path)).getall("CHAP")) == 3


def test_episode_summary_numbers_the_stories(episode):
    summary = episode_summary(episode)
    assert summary.startswith("1. ")
    assert len(summary.splitlines()) == 2


def test_loopback_base_url_is_flagged(cfg):
    """The commonest setup mistake: a feed no phone can download from."""
    cfg.podcast.base_url = "http://127.0.0.1:8000"
    assert warn_if_unreachable(cfg) is True
    cfg.podcast.base_url = "http://192.168.1.10:8000"
    assert warn_if_unreachable(cfg) is False
