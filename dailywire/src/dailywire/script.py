"""Turn ranked clusters into a spoken-word script.

Two LLM stages: one call per cluster for a factual 2-4 sentence summary, then a
single call that stitches the lot into a script with a cold open, category
segments with verbal transitions, and a sign-off. Everything then goes through
a deterministic speakability pass (see text.py), because models drift on the
"no URLs, no bullets, spell the numbers" rules often enough to be worth
enforcing mechanically.
"""

from __future__ import annotations

import logging
import re
from datetime import date as date_cls

from .config import Config
from .llm import LLMError, LLMProvider
from .models import Cluster, Episode, Segment
from .rank import group_by_category
from .text import estimate_duration_seconds, lint_speakable, speakable

log = logging.getLogger(__name__)

CATEGORY_NAMES = {
    "world": "World News",
    "ai": "Artificial Intelligence",
    "tech": "Technology",
    "science": "Science",
    "business": "Business",
}

SEGMENT_MARKER = re.compile(r"^\s*\[SEGMENT:\s*(.+?)\]\s*$", re.MULTILINE)

STYLE_RULES = """\
Writing rules, all of them mandatory:
- This copy is spoken aloud by a text-to-speech voice. Write for the ear.
- No bullet points, no numbered lists, no headings, no markdown, no emoji.
- Never read out a web address, domain name, or file path.
- Spell numbers as words: say "twelve thousand", not "12,000"; "four point two \
percent", not "4.2%"; "nineteen ninety-eight", not "1998".
- Expand every acronym the first time it appears, with the short form after it, \
for example "large language model, or L L M". Use the short form afterwards.
- Attribute every claim to the outlet that reported it, by name.
- Write original prose. Do not reproduce sentences from the source material. \
A quoted phrase of a few words is fine when the wording itself is the news; \
anything longer is not.
- State only what the source material supports. No speculation, no invented \
numbers, no filler like "experts say" when no expert was quoted.
- Plain declarative sentences. No hype, no "buckle up", no "in a world where"."""

SUMMARY_SYSTEM = f"""\
You are a wire editor for a daily audio news briefing. You are given the \
coverage of a single story, sometimes from several outlets. Write a factual \
summary of two to four sentences that a listener with no prior context can \
follow.

Lead with what happened. If several outlets covered it, attribute the central \
claim to the outlet that reported it best and mention that other outlets \
corroborate. If the outlets disagree on a material fact, say so.

{STYLE_RULES}

Return only the summary text. No preamble, no title, no quotation marks around \
the whole thing."""

STITCH_SYSTEM = f"""\
You are the script editor for a daily audio news briefing. You are given \
pre-written story summaries grouped into segments. Assemble them into one \
continuous script to be read aloud by a single host.

Structure:
1. A cold open of two or three sentences: the date, the show name, and a \
hook naming the two or three biggest stories of the day. Do not say "welcome \
back" or "in today's episode we will".
2. Each segment in the order given. Begin every segment with a line containing \
only [SEGMENT: Title] and nothing else, using the segment title provided. That \
marker line is stripped before recording, so it must never appear inside a \
spoken sentence.
3. Inside a segment, introduce it in one short sentence, then move through the \
stories with verbal transitions ("Staying in Europe", "On the research side", \
"Closer to home"). Never say "story one" or "next up, number three".
4. A final [SEGMENT: Sign-off] with a two-sentence close.

Keep the summaries' facts and attributions intact. You may re-word for flow and \
trim redundancy, but do not add facts that are not in the material, and do not \
drop a story.

{STYLE_RULES}

Return only the script."""


def _spoken_date(when: date_cls) -> str:
    """Friday, August 6, 2026 -- no leading zero on the day."""
    return when.strftime("%A, %B %d, %Y").replace(" 0", " ")


def category_title(category: str) -> str:
    return CATEGORY_NAMES.get(category, category.replace("_", " ").title())


# --------------------------------------------------------------------------
# Stage 1: per-cluster summaries
# --------------------------------------------------------------------------


def summary_prompt(cluster: Cluster) -> str:
    outlets = ", ".join(cluster.outlets)
    header = (
        f"STORY CATEGORY: {category_title(cluster.category)}\n"
        f"OUTLETS COVERING THIS STORY ({cluster.corroboration}): {outlets}\n"
    )
    if cluster.hn_points:
        header += f"HACKER NEWS SCORE: {cluster.hn_points}\n"
    return f"{header}\n{cluster.context()}"


def fallback_summary(cluster: Cluster) -> str:
    """Headline-only summary used when no LLM is configured.

    Deliberately does not lift body text from the source: without a model to
    rewrite it, copying prose would breach the "original prose" rule.
    """
    lead = cluster.lead
    title = lead.title.rstrip(".")
    text = f"{lead.source} reports: {title}."
    if cluster.corroboration > 1:
        others = [o for o in cluster.outlets if o != lead.source]
        text += f" The story is also being carried by {_join(others)}."
    if cluster.hn_points:
        text += " It is drawing discussion on Hacker News."
    return text


def _join(names: list[str]) -> str:
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + f" and {names[-1]}"


def summarize_clusters(clusters: list[Cluster], llm: LLMProvider | None) -> list[Cluster]:
    """Fill in cluster.summary, one LLM call per cluster."""
    for index, cluster in enumerate(clusters, 1):
        if llm is None:
            cluster.summary = fallback_summary(cluster)
            continue
        try:
            summary = llm.complete(SUMMARY_SYSTEM, summary_prompt(cluster), max_tokens=400)
        except LLMError as exc:
            log.warning("summary failed for %r (%s); using headline fallback", cluster.title, exc)
            cluster.summary = fallback_summary(cluster)
            continue
        cluster.summary = summary.strip() or fallback_summary(cluster)
        log.info("summarised %d/%d: %s", index, len(clusters), cluster.title[:70])
    return clusters


# --------------------------------------------------------------------------
# Stage 2: stitch
# --------------------------------------------------------------------------


def stitch_prompt(clusters: list[Cluster], cfg: Config, when: date_cls) -> str:
    lines = [
        f"SHOW NAME: {cfg.script.show_name}",
        f"DATE: {_spoken_date(when)}",
        f"TARGET LENGTH: about {int(cfg.ranking.target_runtime_minutes)} minutes when read aloud",
        "",
    ]
    for category, group in group_by_category(clusters, cfg.ranking):
        lines.append(f"[SEGMENT: {category_title(category)}]")
        for cluster in group:
            lines.append(f"- Story: {cluster.title}")
            lines.append(f"  Outlets: {', '.join(cluster.outlets)}")
            lines.append(f"  Summary: {cluster.summary}")
        lines.append("")
    lines.append("[SEGMENT: Sign-off]")
    lines.append(f"Close with, in your own words: {cfg.script.sign_off}")
    return "\n".join(lines)


def build_offline_script(clusters: list[Cluster], cfg: Config, when: date_cls) -> str:
    """Deterministic assembly, used when there's no LLM or the stitch call fails."""
    date_str = _spoken_date(when)
    groups = group_by_category(clusters, cfg.ranking)
    headline_titles = [g[1][0].title for g in groups[:2] if g[1]]

    parts = ["[SEGMENT: Cold open]"]
    opener = f"It is {date_str}, and this is {cfg.script.show_name}."
    if headline_titles:
        opener += f" Today: {_join([t.rstrip('.') for t in headline_titles])}."
    parts.append(opener)

    for index, (category, group) in enumerate(groups):
        parts.append(f"[SEGMENT: {category_title(category)}]")
        lead_in = "We start with" if index == 0 else "Turning to"
        parts.append(f"{lead_in} {category_title(category).lower()}.")
        for position, cluster in enumerate(group):
            if position == 1:
                parts.append("Also in this section.")
            elif position > 1:
                parts.append("Meanwhile.")
            parts.append(cluster.summary)

    parts.append("[SEGMENT: Sign-off]")
    parts.append(cfg.script.sign_off)
    return "\n\n".join(parts)


def parse_segments(script: str) -> list[Segment]:
    """Split marker-delimited script text into segments, dropping the markers."""
    matches = list(SEGMENT_MARKER.finditer(script))
    if not matches:
        return []
    segments: list[Segment] = []
    preamble = script[: matches[0].start()].strip()
    if preamble:
        segments.append(Segment(title="Cold open", category="intro", text=preamble))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(script)
        body = script[match.end() : end].strip()
        if not body:
            continue
        title = match.group(1).strip()
        segments.append(Segment(title=title, category=_category_for(title), text=body))
    return segments


def _category_for(title: str) -> str:
    lowered = title.lower()
    for key, name in CATEGORY_NAMES.items():
        if lowered == name.lower() or lowered == key:
            return key
    if "sign" in lowered:
        return "outro"
    if "open" in lowered:
        return "intro"
    return "other"


def attach_links(segments: list[Segment], clusters: list[Cluster], cfg: Config) -> None:
    """Give each segment the source links for its category, for the show notes."""
    by_category: dict[str, list[str]] = {}
    for cluster in clusters:
        links = by_category.setdefault(cluster.category, [])
        links.extend(item.url for item in cluster.items)
    for segment in segments:
        segment.links = by_category.get(segment.category, [])


def build_script(
    clusters: list[Cluster],
    cfg: Config,
    llm: LLMProvider | None,
    when: date_cls,
) -> Episode:
    """Full stage 1 + stage 2 pass, returning a ready-to-narrate Episode."""
    summarize_clusters(clusters, llm)

    raw = ""
    if llm is not None:
        try:
            raw = llm.complete(
                STITCH_SYSTEM,
                stitch_prompt(clusters, cfg, when),
                max_tokens=max(cfg.llm.max_tokens, 220 * len(clusters)),
            )
        except LLMError as exc:
            log.warning("stitch call failed (%s); assembling script deterministically", exc)

    segments = parse_segments(raw) if raw else []
    if len(segments) < 2:
        if raw:
            log.warning("stitched script had no usable segment markers; falling back")
        raw = build_offline_script(clusters, cfg, when)
        segments = parse_segments(raw)

    for segment in segments:
        segment.text = speakable(
            segment.text,
            numbers=cfg.script.spell_out_numbers,
            urls=cfg.script.strip_urls,
        )
    segments = [s for s in segments if s.text.strip()]
    attach_links(segments, clusters, cfg)

    script = "\n\n".join(s.text for s in segments)
    for problem in lint_speakable(script):
        log.warning("script speakability: %s", problem)

    episode = Episode(
        date=when.isoformat() if hasattr(when, "isoformat") else str(when),
        script=script,
        segments=segments,
        clusters=clusters,
    )
    log.info(
        "script: %d words across %d segments, roughly %.1f minutes",
        episode.word_count,
        len(segments),
        estimate_duration_seconds(script, cfg.ranking.words_per_minute) / 60.0,
    )
    return episode


# --------------------------------------------------------------------------
# Show notes
# --------------------------------------------------------------------------


def show_notes(episode: Episode, cfg: Config) -> str:
    """Markdown emitted next to the audio."""
    lines = [
        f"# {cfg.podcast.title} — {episode.date}",
        "",
        f"*{len(episode.clusters)} stories · about "
        f"{estimate_duration_seconds(episode.script, cfg.ranking.words_per_minute) / 60:.0f} minutes*",
        "",
        "## Stories",
        "",
    ]
    for category, group in group_by_category(episode.clusters, cfg.ranking):
        lines.append(f"### {category_title(category)}")
        lines.append("")
        for cluster in group:
            lines.append(f"**{cluster.title}**")
            lines.append("")
            lines.append(cluster.summary)
            lines.append("")
            for item in sorted(cluster.items, key=lambda i: -i.source_weight):
                lines.append(f"- [{item.source}]({item.url})")
            lines.append("")
    lines += ["## Script", "", episode.script, ""]
    return "\n".join(lines)
