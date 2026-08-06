from __future__ import annotations

from conftest import make_item

from dailywire.store import Store


def test_filter_new_drops_items_seen_before(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    first = make_item("Volcano erupts in Iceland", url="https://a.example/volcano")
    assert store.filter_new([first]) == [first]

    store.mark_seen([first])
    again = make_item("Volcano erupts in Iceland", url="https://a.example/volcano")
    assert store.filter_new([again]) == []


def test_filter_new_ignores_tracking_parameters(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    store.mark_seen([make_item("Story", url="https://a.example/x")])
    dupe = make_item("Story", url="https://a.example/x?utm_source=rss")
    assert store.filter_new([dupe]) == []


def test_filter_new_catches_near_duplicate_titles(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    store.mark_seen([make_item("Acme acquires Beta Corp in cash deal", url="https://a.example/1")])
    near = make_item("Acme acquires Beta Corp in cash deal today", url="https://b.example/2")
    far = make_item("Parliament debates new energy tariffs", url="https://c.example/3")
    assert store.filter_new([near, far]) == [far]


def test_filter_new_keeps_the_same_story_from_two_outlets(tmp_path):
    """Corroboration depends on these surviving to the clusterer."""
    store = Store(tmp_path / "db.sqlite")
    syndicated = [
        make_item("Wire story about a summit", url="https://a.example/s", source="A"),
        make_item("Wire story about a summit", url="https://b.example/s", source="B"),
    ]
    assert len(store.filter_new(syndicated)) == 2


def test_filter_new_drops_an_identical_url_twice_in_one_batch(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    same = [
        make_item("A story", url="https://a.example/s", source="A"),
        make_item("A story", url="https://a.example/s?utm_source=rss", source="A"),
    ]
    assert len(store.filter_new(same)) == 1


def test_filter_new_still_blocks_a_near_duplicate_from_a_previous_day(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    store.mark_seen([make_item("Wire story about a summit", url="https://a.example/s")])
    later = make_item("Wire story about the summit", url="https://b.example/s")
    assert store.filter_new([later]) == []


def test_mark_seen_is_idempotent_and_records_episode_date(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    item = make_item("Story", url="https://a.example/x")
    store.mark_seen([item])
    store.mark_seen([item], episode_date="2026-08-06")
    rows = store.conn.execute("SELECT episode_date FROM seen_items").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "2026-08-06"


def test_record_episode_and_stories_round_trip(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    store.record_episode(
        date="2026-08-06", audio_path="/e/2026-08-06.mp3", script_path="/e/2026-08-06.md",
        duration_ms=720_000, story_count=2, word_count=1800, title="Dailywire", summary="1. A\n2. B",
    )
    store.record_stories(
        "2026-08-06",
        [
            {"category": "world", "title": "A", "summary": "s", "outlets": ["BBC", "DW"],
             "links": ["https://x"], "score": 2.5},
            {"category": "ai", "title": "B", "summary": "s", "outlets": ["Ars"],
             "links": ["https://y"], "score": 1.5},
        ],
    )
    episodes = store.episodes()
    assert len(episodes) == 1 and episodes[0]["duration_ms"] == 720_000

    stories = store.episode_stories("2026-08-06")
    assert [s["title"] for s in stories] == ["A", "B"]
    assert stories[0]["outlets"] == "BBC; DW"


def test_record_episode_overwrites_on_rerun(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    for duration in (100, 200):
        store.record_episode(
            date="2026-08-06", audio_path="a.mp3", script_path="a.md", duration_ms=duration,
            story_count=1, word_count=10, title="t", summary="s",
        )
    episodes = store.episodes()
    assert len(episodes) == 1 and episodes[0]["duration_ms"] == 200


def test_prune_keeps_items_that_made_an_episode(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    used = make_item("Used", url="https://a.example/used")
    unused = make_item("Unused", url="https://a.example/unused")
    store.mark_seen([used], episode_date="2020-01-01")
    store.mark_seen([unused])
    store.conn.execute("UPDATE seen_items SET first_seen = '2019-01-01T00:00:00+00:00'")
    store.conn.commit()

    assert store.prune(keep_days=30) == 1
    remaining = [row[0] for row in store.conn.execute("SELECT title FROM seen_items")]
    assert remaining == ["Used"]
