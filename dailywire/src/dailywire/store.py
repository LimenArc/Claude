"""SQLite store of every item ever seen, so nothing repeats across days."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import Item
from .text import from_signed64, hamming, simhash, to_signed64, url_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_items (
    url_hash    TEXT PRIMARY KEY,
    url         TEXT NOT NULL,
    title       TEXT NOT NULL,
    simhash     INTEGER NOT NULL,
    source      TEXT NOT NULL,
    category    TEXT NOT NULL,
    published   TEXT,
    first_seen  TEXT NOT NULL,
    episode_date TEXT
);
CREATE INDEX IF NOT EXISTS idx_seen_first_seen ON seen_items(first_seen);
CREATE INDEX IF NOT EXISTS idx_seen_episode ON seen_items(episode_date);

CREATE TABLE IF NOT EXISTS episodes (
    date         TEXT PRIMARY KEY,
    audio_path    TEXT,
    script_path   TEXT,
    duration_ms   INTEGER DEFAULT 0,
    story_count   INTEGER DEFAULT 0,
    word_count    INTEGER DEFAULT 0,
    title         TEXT,
    summary       TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS episode_stories (
    episode_date TEXT NOT NULL,
    position     INTEGER NOT NULL,
    category     TEXT NOT NULL,
    title        TEXT NOT NULL,
    summary      TEXT,
    outlets      TEXT,
    links        TEXT,
    score        REAL,
    PRIMARY KEY (episode_date, position)
);
"""

# Titles within this Hamming distance (of 64 bits) are treated as the same story.
# See the calibration note on text.simhash: near-duplicates measure under 11
# bits apart, unrelated headlines over 27, so 16 sits in the gap.
SIMHASH_THRESHOLD = 16


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- dedupe -----------------------------------------------------------

    def known_url_hashes(self) -> set[str]:
        with closing(self.conn.execute("SELECT url_hash FROM seen_items")) as cur:
            return {row[0] for row in cur}

    def recent_simhashes(self, days: int = 14) -> list[int]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with closing(
            self.conn.execute("SELECT simhash FROM seen_items WHERE first_seen >= ?", (cutoff,))
        ) as cur:
            return [from_signed64(row[0]) for row in cur]

    def filter_new(self, items: list[Item], *, lookback_days: int = 14) -> list[Item]:
        """Drop items carried in a previous episode's ingest.

        Two kinds of duplicate, handled differently on purpose:

        * Against *history*, both URL and near-duplicate title are grounds for
          dropping -- that is what stops a story recurring across days.
        * Within *this batch*, only an identical URL is. Two outlets covering
          the same story have near-identical titles, and those items have to
          survive to the clusterer: merging them is how corroboration gets
          counted, and dropping one here would silently weaken the ranking.
        """
        known_urls = self.known_url_hashes()
        history = self.recent_simhashes(lookback_days)
        batch_urls: set[str] = set()
        fresh: list[Item] = []
        for item in items:
            uh = url_hash(item.url)
            if uh in known_urls or uh in batch_urls:
                continue
            sh = simhash(item.title)
            if sh and any(hamming(sh, other) <= SIMHASH_THRESHOLD for other in history):
                continue
            batch_urls.add(uh)
            fresh.append(item)
        return fresh

    def mark_seen(self, items: list[Item], episode_date: str | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            (
                url_hash(item.url),
                item.url,
                item.title,
                to_signed64(simhash(item.title)),
                item.source,
                item.category,
                item.published.isoformat() if item.published else None,
                now,
                episode_date,
            )
            for item in items
        ]
        self.conn.executemany(
            """INSERT INTO seen_items
                 (url_hash, url, title, simhash, source, category, published, first_seen, episode_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(url_hash) DO UPDATE SET
                 episode_date = COALESCE(excluded.episode_date, seen_items.episode_date)""",
            rows,
        )
        self.conn.commit()

    # -- episodes ---------------------------------------------------------

    def record_episode(
        self,
        *,
        date: str,
        audio_path: str,
        script_path: str,
        duration_ms: int,
        story_count: int,
        word_count: int,
        title: str,
        summary: str,
    ) -> None:
        self.conn.execute(
            """INSERT INTO episodes
                 (date, audio_path, script_path, duration_ms, story_count, word_count, title, summary, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(date) DO UPDATE SET
                 audio_path=excluded.audio_path, script_path=excluded.script_path,
                 duration_ms=excluded.duration_ms, story_count=excluded.story_count,
                 word_count=excluded.word_count, title=excluded.title,
                 summary=excluded.summary, created_at=excluded.created_at""",
            (date, audio_path, script_path, duration_ms, story_count, word_count, title, summary,
             datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    def record_stories(self, episode_date: str, stories: list[dict]) -> None:
        self.conn.execute("DELETE FROM episode_stories WHERE episode_date = ?", (episode_date,))
        self.conn.executemany(
            """INSERT INTO episode_stories
                 (episode_date, position, category, title, summary, outlets, links, score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    episode_date,
                    i,
                    s.get("category", ""),
                    s.get("title", ""),
                    s.get("summary", ""),
                    "; ".join(s.get("outlets", [])),
                    "\n".join(s.get("links", [])),
                    float(s.get("score", 0.0)),
                )
                for i, s in enumerate(stories)
            ],
        )
        self.conn.commit()

    def episodes(self) -> list[sqlite3.Row]:
        with closing(
            self.conn.execute("SELECT * FROM episodes ORDER BY date DESC")
        ) as cur:
            return cur.fetchall()

    def episode_stories(self, episode_date: str) -> list[sqlite3.Row]:
        with closing(
            self.conn.execute(
                "SELECT * FROM episode_stories WHERE episode_date = ? ORDER BY position",
                (episode_date,),
            )
        ) as cur:
            return cur.fetchall()

    def prune(self, keep_days: int = 365) -> int:
        """Forget items older than keep_days that never made an episode."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).isoformat()
        cur = self.conn.execute(
            "DELETE FROM seen_items WHERE first_seen < ? AND episode_date IS NULL", (cutoff,)
        )
        self.conn.commit()
        return cur.rowcount
