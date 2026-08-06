"""Publishing: ID3 tags with chapter markers, and the podcast RSS feed."""

from __future__ import annotations

import logging
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime, time, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.dom import minidom

from .config import Config
from .models import Episode
from .store import Store

log = logging.getLogger(__name__)

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
ATOM_NS = "http://www.w3.org/2005/Atom"

ET.register_namespace("itunes", ITUNES_NS)
ET.register_namespace("content", CONTENT_NS)
ET.register_namespace("atom", ATOM_NS)


# --------------------------------------------------------------------------
# ID3
# --------------------------------------------------------------------------


def tag_mp3(path: Path, episode: Episode, cfg: Config) -> None:
    """Write ID3v2 tags plus one chapter per segment.

    Chapters are CHAP frames indexed by a top-level CTOC, which is what
    Apple Podcasts, Pocket Casts, AntennaPod and friends read.
    """
    from mutagen.id3 import (
        APIC, CHAP, COMM, CTOC, CTOCFlags, ID3, TALB, TCON, TDRC, TIT2, TPE1, TRCK, WOAS,
    )
    from mutagen.mp3 import MP3

    audio = MP3(str(path))
    if audio.tags is None:
        audio.add_tags()
    tags: ID3 = audio.tags
    tags.delall("CHAP")
    tags.delall("CTOC")

    title = f"{cfg.podcast.title} — {episode.date}"
    tags.add(TIT2(encoding=3, text=title))
    tags.add(TPE1(encoding=3, text=cfg.podcast.author))
    tags.add(TALB(encoding=3, text=cfg.podcast.title))
    tags.add(TCON(encoding=3, text="Podcast"))
    tags.add(TDRC(encoding=3, text=episode.date))
    tags.add(TRCK(encoding=3, text=episode.date.replace("-", "")))
    tags.add(COMM(encoding=3, lang="eng", desc="desc", text=episode_summary(episode)))
    if cfg.podcast.base_url:
        tags.add(WOAS(url=cfg.podcast.base_url))

    artwork = cfg.path(cfg.podcast.artwork) if cfg.podcast.artwork else None
    if artwork and artwork.exists():
        mime = "image/png" if artwork.suffix.lower() == ".png" else "image/jpeg"
        tags.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=artwork.read_bytes()))

    child_ids: list[str] = []
    for index, segment in enumerate(episode.segments):
        if segment.end_ms <= segment.start_ms:
            continue
        element_id = f"chp{index}"
        child_ids.append(element_id)
        tags.add(
            CHAP(
                element_id=element_id,
                start_time=segment.start_ms,
                end_time=segment.end_ms,
                sub_frames=[TIT2(encoding=3, text=segment.title)],
            )
        )
    if child_ids:
        tags.add(
            CTOC(
                element_id="toc",
                flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED,
                child_element_ids=child_ids,
                sub_frames=[TIT2(encoding=3, text="Chapters")],
            )
        )

    audio.save(v2_version=3)
    log.info("tagged %s with %d chapters", path.name, len(child_ids))


def episode_summary(episode: Episode) -> str:
    """One-line-per-story summary used in tags and the feed."""
    lines = [f"{i + 1}. {c.title}" for i, c in enumerate(episode.clusters)]
    return "\n".join(lines) if lines else episode.script[:400]


# --------------------------------------------------------------------------
# RSS
# --------------------------------------------------------------------------


def _sub(parent: ET.Element, tag: str, text: str | None = None, **attrs) -> ET.Element:
    element = ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})
    if text is not None:
        element.text = text
    return element


def _itunes(parent: ET.Element, tag: str, text: str | None = None, **attrs) -> ET.Element:
    return _sub(parent, f"{{{ITUNES_NS}}}{tag}", text, **attrs)


def format_duration(ms: int) -> str:
    seconds = max(0, ms) // 1000
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:d}:{secs:02d}"


def _pub_datetime(date_str: str) -> datetime:
    """Publish at 6am UTC on the episode date -- stable across regenerations."""
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return datetime.now(timezone.utc)
    return datetime.combine(day, time(6, 0), tzinfo=timezone.utc)


def collect_episodes(cfg: Config, store: Store | None = None) -> list[dict]:
    """Every episode with audio still on disk, newest first."""
    episodes_dir = cfg.episodes_path
    rows = {row["date"]: row for row in store.episodes()} if store is not None else {}

    entries: list[dict] = []
    for mp3 in sorted(episodes_dir.glob("*.mp3"), reverse=True):
        date_str = mp3.stem
        row = rows.get(date_str)
        notes = mp3.with_suffix(".md")
        entries.append(
            {
                "date": date_str,
                "path": mp3,
                "size": mp3.stat().st_size,
                "duration_ms": int(row["duration_ms"]) if row else 0,
                "title": (row["title"] if row and row["title"] else f"{cfg.podcast.title} — {date_str}"),
                "summary": (row["summary"] if row and row["summary"] else ""),
                "notes": notes if notes.exists() else None,
            }
        )
    return entries


def build_feed(cfg: Config, store: Store | None = None) -> str:
    """Regenerate the whole RSS 2.0 + itunes feed from what's on disk."""
    base = cfg.podcast.base_url.rstrip("/")
    rss = ET.Element("rss", {"version": "2.0"})
    channel = _sub(rss, "channel")

    _sub(channel, "title", cfg.podcast.title)
    _sub(channel, "link", base or "http://localhost")
    _sub(channel, "description", cfg.podcast.description.strip())
    _sub(channel, "language", cfg.podcast.language)
    _sub(channel, "generator", "dailywire")
    _sub(channel, "lastBuildDate", format_datetime(datetime.now(timezone.utc)))
    _sub(channel, "docs", "https://www.rssboard.org/rss-specification")
    _sub(channel, f"{{{ATOM_NS}}}link", None, href=f"{base}/feed.xml", rel="self",
         type="application/rss+xml")

    _itunes(channel, "author", cfg.podcast.author)
    _itunes(channel, "subtitle", cfg.podcast.subtitle)
    _itunes(channel, "summary", cfg.podcast.description.strip())
    _itunes(channel, "explicit", "yes" if cfg.podcast.explicit else "no")
    _itunes(channel, "type", "episodic")
    owner = _itunes(channel, "owner")
    _itunes(owner, "name", cfg.podcast.author)
    _itunes(owner, "email", cfg.podcast.email)
    # itunes:category carries the name in a "text" attribute, which collides
    # with the helper's text argument, so build these two directly.
    category = ET.SubElement(channel, f"{{{ITUNES_NS}}}category", {"text": cfg.podcast.category})
    if cfg.podcast.subcategory:
        ET.SubElement(category, f"{{{ITUNES_NS}}}category", {"text": cfg.podcast.subcategory})

    artwork = cfg.path(cfg.podcast.artwork) if cfg.podcast.artwork else None
    if artwork and artwork.exists():
        image_url = f"{base}/{artwork.name}"
        _itunes(channel, "image", None, href=image_url)
        image = _sub(channel, "image")
        _sub(image, "url", image_url)
        _sub(image, "title", cfg.podcast.title)
        _sub(image, "link", base or "http://localhost")

    for entry in collect_episodes(cfg, store):
        item = _sub(channel, "item")
        audio_url = f"{base}/episodes/{entry['path'].name}"
        _sub(item, "title", entry["title"])
        _sub(item, "link", audio_url)
        _sub(item, "guid", f"dailywire-{entry['date']}", isPermaLink="false")
        _sub(item, "pubDate", format_datetime(_pub_datetime(entry["date"])))
        _sub(item, "description", entry["summary"] or entry["title"])
        _sub(item, "enclosure", None, url=audio_url, length=entry["size"], type="audio/mpeg")
        _itunes(item, "author", cfg.podcast.author)
        _itunes(item, "summary", entry["summary"] or entry["title"])
        _itunes(item, "explicit", "yes" if cfg.podcast.explicit else "no")
        if entry["duration_ms"]:
            _itunes(item, "duration", format_duration(entry["duration_ms"]))
        if entry["notes"] is not None:
            html = f'<p><a href="{base}/episodes/{entry["notes"].name}">Show notes and sources</a></p>'
            content = _sub(item, f"{{{CONTENT_NS}}}encoded")
            content.text = html

    raw = ET.tostring(rss, encoding="utf-8", xml_declaration=True)
    return minidom.parseString(raw).toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "0.0.0.0", "[::1]")


def warn_if_unreachable(cfg: Config) -> bool:
    """A loopback base_url produces enclosure links no phone can fetch."""
    host = cfg.podcast.base_url.split("//")[-1].split("/")[0].split(":")[0]
    if host in LOOPBACK_HOSTS or not host:
        log.warning(
            "podcast.base_url is %r: enclosure links in feed.xml will only work on this "
            "machine. Set it to this host's LAN address so your phone can download episodes.",
            cfg.podcast.base_url,
        )
        return True
    return False


def write_feed(cfg: Config, store: Store | None = None) -> Path:
    warn_if_unreachable(cfg)
    public = cfg.public_path
    public.mkdir(parents=True, exist_ok=True)
    feed_path = public / "feed.xml"
    feed_path.write_text(build_feed(cfg, store), encoding="utf-8")

    artwork = cfg.path(cfg.podcast.artwork) if cfg.podcast.artwork else None
    if artwork and artwork.exists() and artwork.parent != public:
        shutil.copy2(artwork, public / artwork.name)

    log.info("wrote %s", feed_path)
    return feed_path


INDEX_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 16px/1.6 system-ui, sans-serif; max-width: 42rem; margin: 3rem auto; padding: 0 1rem; }}
  h1 {{ margin-bottom: .25rem; }}
  .sub {{ opacity: .7; margin-top: 0; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ padding: .75rem 0; border-bottom: 1px solid color-mix(in srgb, currentColor 15%, transparent); }}
  audio {{ width: 100%; margin-top: .5rem; }}
  code {{ background: color-mix(in srgb, currentColor 10%, transparent); padding: .1rem .3rem; border-radius: .2rem; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="sub">{subtitle}</p>
<p>Subscribe in any podcast app: <code>{base}/feed.xml</code></p>
<ul>
{items}
</ul>
</body>
</html>
"""


def write_index(cfg: Config, store: Store | None = None) -> Path:
    """A tiny landing page so the LAN URL is useful in a browser too."""
    base = cfg.podcast.base_url.rstrip("/")
    items = []
    for entry in collect_episodes(cfg, store):
        notes = (
            f' &middot; <a href="/episodes/{entry["notes"].name}">show notes</a>'
            if entry["notes"] is not None
            else ""
        )
        duration = f" ({format_duration(entry['duration_ms'])})" if entry["duration_ms"] else ""
        items.append(
            f'<li><strong>{entry["date"]}</strong>{duration}{notes}'
            f'<audio controls preload="none" src="/episodes/{entry["path"].name}"></audio></li>'
        )
    html = INDEX_TEMPLATE.format(
        title=cfg.podcast.title,
        subtitle=cfg.podcast.subtitle,
        base=base,
        items="\n".join(items) or "<li>No episodes yet.</li>",
    )
    public = cfg.public_path
    public.mkdir(parents=True, exist_ok=True)
    path = public / "index.html"
    path.write_text(html, encoding="utf-8")
    return path
