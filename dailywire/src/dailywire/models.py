"""Core data structures shared across the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Item:
    """A single article as harvested from one source."""

    title: str
    url: str
    source: str
    category: str = "tech"
    source_weight: float = 1.0
    summary: str = ""          # feed-provided snippet
    full_text: str = ""        # extracted article body, when we could get one
    published: datetime = field(default_factory=utcnow)
    author: str = ""
    hn_points: int = 0
    hn_comments: int = 0
    hn_url: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def text(self) -> str:
        """Best available body text for embedding and summarisation."""
        return self.full_text or self.summary or self.title

    @property
    def age_hours(self) -> float:
        return max(0.0, (utcnow() - self.published).total_seconds() / 3600.0)

    def context_block(self, max_chars: int = 4000) -> str:
        """Rendered form handed to the language model."""
        body = self.text.strip()
        if len(body) > max_chars:
            body = body[:max_chars].rsplit(" ", 1)[0] + " ..."
        head = f"OUTLET: {self.source}\nHEADLINE: {self.title}"
        if self.published:
            head += f"\nPUBLISHED: {self.published.isoformat(timespec='minutes')}"
        if self.hn_points:
            head += f"\nHACKER NEWS POINTS: {self.hn_points}"
        return f"{head}\nBODY: {body}"


@dataclass
class Cluster:
    """A group of items telling the same story from different outlets."""

    items: list[Item]
    category: str = "tech"
    score: float = 0.0
    summary: str = ""            # LLM-written, 2-4 sentences
    score_breakdown: dict[str, float] = field(default_factory=dict)

    @property
    def lead(self) -> Item:
        """Representative item: highest source weight, then newest."""
        return max(self.items, key=lambda i: (i.source_weight, i.published))

    @property
    def title(self) -> str:
        return self.lead.title

    @property
    def outlets(self) -> list[str]:
        seen: list[str] = []
        for item in self.items:
            if item.source not in seen:
                seen.append(item.source)
        return seen

    @property
    def corroboration(self) -> int:
        return len(self.outlets)

    @property
    def hn_points(self) -> int:
        return max((i.hn_points for i in self.items), default=0)

    @property
    def published(self) -> datetime:
        return max(i.published for i in self.items)

    def context(self, max_items: int = 4) -> str:
        ordered = sorted(self.items, key=lambda i: (-i.source_weight, i.published))
        return "\n\n---\n\n".join(i.context_block() for i in ordered[:max_items])


@dataclass
class Segment:
    """One spoken segment of the finished script (used for chapter markers)."""

    title: str
    category: str
    text: str
    start_ms: int = 0
    end_ms: int = 0
    links: list[str] = field(default_factory=list)


@dataclass
class Episode:
    date: str                      # YYYY-MM-DD
    script: str
    segments: list[Segment]
    clusters: list[Cluster] = field(default_factory=list)
    audio_path: str = ""
    script_path: str = ""
    duration_ms: int = 0

    @property
    def word_count(self) -> int:
        return len(self.script.split())
