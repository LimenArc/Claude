"""Score and select the stories that make today's episode."""

from __future__ import annotations

import logging
import math
from collections import Counter

from .config import Quota, RankingConfig
from .models import Cluster

log = logging.getLogger(__name__)

# Rough budget used to translate "target runtime" into a story count before any
# text exists. A summary lands at 55-75 words; transitions and the story's
# lead-in cost another ~20.
WORDS_PER_STORY = 90
# Cold open plus sign-off plus segment transitions.
OVERHEAD_WORDS = 180


def recency_score(age_hours: float, half_life: float) -> float:
    """1.0 for something just published, halving every `half_life` hours."""
    if half_life <= 0:
        return 1.0
    return 0.5 ** (max(0.0, age_hours) / half_life)


def score_cluster(cluster: Cluster, cfg: RankingConfig) -> float:
    age = min(item.age_hours for item in cluster.items)
    recency = recency_score(age, cfg.recency_half_life)
    source = max(item.source_weight for item in cluster.items)
    # One outlet is the baseline; the second and third are what matter.
    corroboration = math.log1p(max(0, cluster.corroboration - 1))
    hn = math.log1p(cluster.hn_points) / math.log(1000) if cluster.hn_points else 0.0

    breakdown = {
        "recency": cfg.weight_recency * recency,
        "source": cfg.weight_source * source,
        "corroboration": cfg.weight_corroboration * corroboration,
        "hn": cfg.weight_hn * hn,
    }
    cluster.score_breakdown = breakdown
    cluster.score = sum(breakdown.values())
    return cluster.score


def runtime_capacity(cfg: RankingConfig) -> int:
    """How many stories fit in the target runtime."""
    budget_words = cfg.target_runtime_minutes * cfg.words_per_minute - OVERHEAD_WORDS
    return max(1, int(budget_words // WORDS_PER_STORY))


def _quota(cfg: RankingConfig, category: str, limit: int) -> Quota:
    return cfg.quotas.get(category, Quota(0, limit))


def select(clusters: list[Cluster], cfg: RankingConfig) -> list[Cluster]:
    """Pick the top stories subject to runtime and per-category quotas.

    Category minimums are honoured first so a heavy AI news day cannot crowd
    world news out of the episode; remaining slots go to the global ranking,
    capped by each category's maximum.
    """
    if not clusters:
        return []

    for cluster in clusters:
        score_cluster(cluster, cfg)

    ranked = sorted(clusters, key=lambda c: c.score, reverse=True)
    limit = min(cfg.max_stories, runtime_capacity(cfg))
    log.info(
        "selecting up to %d stories (max_stories=%d, runtime allows %d) from %d clusters",
        limit, cfg.max_stories, runtime_capacity(cfg), len(ranked),
    )

    chosen: list[int] = []
    taken: set[int] = set()
    per_category: Counter[str] = Counter()

    # Pass 1: category minimums, best-scoring category first so that when the
    # minimums oversubscribe the episode the strongest categories still land.
    best_score: dict[str, float] = {}
    for cluster in ranked:
        best_score.setdefault(cluster.category, cluster.score)
    for category in sorted(best_score, key=lambda c: best_score[c], reverse=True):
        minimum = _quota(cfg, category, limit).min
        if minimum <= 0:
            continue
        for index, cluster in enumerate(ranked):
            if len(chosen) >= limit or per_category[category] >= minimum:
                break
            if index in taken or cluster.category != category:
                continue
            chosen.append(index)
            taken.add(index)
            per_category[category] += 1

    # Pass 2: fill what's left by score, respecting category maximums.
    for index, cluster in enumerate(ranked):
        if len(chosen) >= limit:
            break
        if index in taken:
            continue
        if per_category[cluster.category] >= _quota(cfg, cluster.category, limit).max:
            continue
        chosen.append(index)
        taken.add(index)
        per_category[cluster.category] += 1

    selected = [ranked[i] for i in chosen]
    log.info(
        "selected %d stories: %s",
        len(selected),
        ", ".join(f"{c}={n}" for c, n in sorted(per_category.items())) or "none",
    )
    return order_for_episode(selected, cfg)


def order_for_episode(clusters: list[Cluster], cfg: RankingConfig) -> list[Cluster]:
    """Group into category segments, in config order, best story first."""
    category_order = {name: i for i, name in enumerate(cfg.quotas)}
    return sorted(
        clusters,
        key=lambda c: (category_order.get(c.category, len(category_order)), -c.score),
    )


def group_by_category(clusters: list[Cluster], cfg: RankingConfig) -> list[tuple[str, list[Cluster]]]:
    """Ordered (category, clusters) pairs, for building script segments."""
    groups: dict[str, list[Cluster]] = {}
    for cluster in order_for_episode(clusters, cfg):
        groups.setdefault(cluster.category, []).append(cluster)
    return list(groups.items())
