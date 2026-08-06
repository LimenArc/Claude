"""End-to-end run: ingest, dedupe, cluster, rank, script, narrate, publish."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date as date_cls
from pathlib import Path

from . import audio, publish, script as script_mod
from .cluster import cluster_items
from .config import Config
from .fetch import ingest
from .llm import get_provider as get_llm
from .models import Episode
from .rank import select
from .store import Store
from .tts import get_provider as get_tts

log = logging.getLogger(__name__)


@dataclass
class RunOptions:
    date: date_cls | None = None
    dry_run: bool = False        # no audio, no database writes
    skip_audio: bool = False     # script and show notes only
    tts_provider: str | None = None
    force: bool = False          # overwrite an episode that already exists


def _today(cfg: Config) -> date_cls:
    """Today in the configured timezone -- an episode is named for its morning."""
    from datetime import datetime
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    try:
        tz = ZoneInfo(cfg.general.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        log.warning("unknown timezone %r; using system local time", cfg.general.timezone)
        return date_cls.today()
    return datetime.now(tz).date()


def run(cfg: Config, options: RunOptions | None = None) -> Episode | None:
    options = options or RunOptions()
    when = options.date or _today(cfg)
    date_str = when.isoformat()

    episodes_dir = cfg.episodes_path
    episodes_dir.mkdir(parents=True, exist_ok=True)
    audio_path = episodes_dir / f"{date_str}.mp3"
    notes_path = episodes_dir / f"{date_str}.md"

    if audio_path.exists() and not options.force and not options.dry_run:
        log.error("%s already exists; pass --force to regenerate", audio_path)
        return None

    store = Store(cfg.db_file)
    try:
        # 1. Ingest -------------------------------------------------------
        items = asyncio.run(ingest(cfg))
        if not items:
            log.error("no items ingested -- check network access and the source list")
            return None

        # 2. Dedupe -------------------------------------------------------
        fresh = store.filter_new(items)
        log.info("%d of %d items are new", len(fresh), len(items))
        if not fresh:
            log.error("nothing new since the last run")
            return None

        # 3. Cluster and rank ---------------------------------------------
        clusters = cluster_items(fresh, cfg.cluster)
        selected = select(clusters, cfg.ranking)
        if not selected:
            log.error("ranking selected no stories")
            return None
        for position, cluster in enumerate(selected, 1):
            log.info(
                "%2d. [%s] %.2f (%d outlets) %s",
                position, cluster.category, cluster.score, cluster.corroboration, cluster.title[:80],
            )

        # 4. Script -------------------------------------------------------
        llm = get_llm(cfg.llm)
        episode = script_mod.build_script(selected, cfg, llm, when)

        notes_path.write_text(script_mod.show_notes(episode, cfg), encoding="utf-8")
        episode.script_path = str(notes_path)
        log.info("wrote %s", notes_path)

        if options.dry_run or options.skip_audio:
            log.info("skipping narration (%s)", "dry run" if options.dry_run else "--skip-audio")
            if not options.dry_run:
                _record(store, cfg, episode, date_str, items, notes_path)
            return episode

        # 5. Narrate ------------------------------------------------------
        provider = get_tts(cfg, options.tts_provider)
        audio.narrate(episode, provider, cfg, audio_path)

        # 6. Publish ------------------------------------------------------
        publish.tag_mp3(audio_path, episode, cfg)
        _record(store, cfg, episode, date_str, items, notes_path)
        publish.write_feed(cfg, store)
        publish.write_index(cfg, store)

        log.info(
            "episode %s ready: %s (%s)",
            date_str, audio_path, publish.format_duration(episode.duration_ms),
        )
        return episode
    finally:
        store.close()


def _record(store: Store, cfg: Config, episode: Episode, date_str: str, items, notes_path: Path) -> None:
    """Persist what we saw and what we shipped."""
    store.mark_seen(items)
    used = [item for cluster in episode.clusters for item in cluster.items]
    store.mark_seen(used, episode_date=date_str)
    store.record_episode(
        date=date_str,
        audio_path=episode.audio_path,
        script_path=str(notes_path),
        duration_ms=episode.duration_ms,
        story_count=len(episode.clusters),
        word_count=episode.word_count,
        title=f"{cfg.podcast.title} — {date_str}",
        summary=publish.episode_summary(episode),
    )
    store.record_stories(
        date_str,
        [
            {
                "category": c.category,
                "title": c.title,
                "summary": c.summary,
                "outlets": c.outlets,
                "links": [i.url for i in c.items],
                "score": c.score,
            }
            for c in episode.clusters
        ],
    )
