from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from test_publish import write_mp3

from dailywire.publish import write_feed, write_index
from dailywire.server import create_app
from dailywire.store import Store


@pytest.fixture
def client(cfg):
    write_mp3(cfg.episodes_path / "2026-08-06.mp3")
    (cfg.episodes_path / "2026-08-06.md").write_text("# Show notes")
    with Store(cfg.db_file) as store:
        store.record_episode(
            date="2026-08-06", audio_path="2026-08-06.mp3", script_path="2026-08-06.md",
            duration_ms=720_000, story_count=3, word_count=1800,
            title="Dailywire — 2026-08-06", summary="1. A story",
        )
        write_feed(cfg, store)
        write_index(cfg, store)
    return TestClient(create_app(cfg))


def test_healthz(client):
    assert client.get("/healthz").text == "ok"


def test_feed_is_served_from_public(client):
    resp = client.get("/feed.xml")
    assert resp.status_code == 200
    assert "<rss" in resp.text
    assert "2026-08-06.mp3" in resp.text


def test_index_is_served_at_the_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Dailywire" in resp.text


def test_audio_is_served_from_the_episodes_directory(client):
    resp = client.get("/episodes/2026-08-06.mp3")
    assert resp.status_code == 200
    assert len(resp.content) > 0


def test_audio_supports_range_requests(client):
    """Podcast apps and browsers seek with Range; without it, scrubbing breaks."""
    resp = client.get("/episodes/2026-08-06.mp3", headers={"Range": "bytes=0-99"})
    assert resp.status_code == 206
    assert len(resp.content) == 100
    assert resp.headers["content-range"].startswith("bytes 0-99/")


def test_show_notes_are_served(client):
    assert "Show notes" in client.get("/episodes/2026-08-06.md").text


def test_api_lists_episodes(client):
    data = client.get("/api/episodes").json()
    assert len(data) == 1
    assert data[0]["date"] == "2026-08-06"
    assert data[0]["duration"] == "12:00"
    assert data[0]["audio"] == "/episodes/2026-08-06.mp3"
    assert data[0]["notes"] == "/episodes/2026-08-06.md"


def test_api_refresh_rewrites_the_feed(cfg, client):
    (cfg.public_path / "feed.xml").unlink()
    assert client.post("/api/refresh").json()["status"] == "ok"
    assert (cfg.public_path / "feed.xml").exists()


def test_missing_paths_are_404(client):
    assert client.get("/episodes/1999-01-01.mp3").status_code == 404
    assert client.get("/nope.html").status_code == 404


def test_app_starts_with_empty_directories(cfg):
    """First run, before any episode exists."""
    app = create_app(cfg)
    assert TestClient(app).get("/healthz").status_code == 200
    assert cfg.public_path.exists() and cfg.episodes_path.exists()
