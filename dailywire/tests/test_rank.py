from __future__ import annotations

from collections import Counter

from conftest import make_cluster

from dailywire.config import Quota, RankingConfig
from dailywire.rank import (
    group_by_category,
    order_for_episode,
    recency_score,
    runtime_capacity,
    score_cluster,
    select,
)


def test_recency_score_halves_at_the_half_life():
    assert recency_score(0, 10) == 1.0
    assert abs(recency_score(10, 10) - 0.5) < 1e-9
    assert abs(recency_score(20, 10) - 0.25) < 1e-9


def test_fresher_stories_score_higher():
    cfg = RankingConfig()
    fresh = make_cluster("Fresh story", age_hours=1)
    stale = make_cluster("Stale story", age_hours=30)
    assert score_cluster(fresh, cfg) > score_cluster(stale, cfg)


def test_corroboration_raises_the_score():
    cfg = RankingConfig()
    single = make_cluster("Single outlet story", outlets=1)
    many = make_cluster("Many outlet story", outlets=4)
    assert score_cluster(many, cfg) > score_cluster(single, cfg)


def test_hacker_news_points_raise_the_score():
    cfg = RankingConfig()
    quiet = make_cluster("Quiet story", category="tech", hn_points=0)
    loud = make_cluster("Loud story", category="tech", hn_points=900)
    assert score_cluster(loud, cfg) > score_cluster(quiet, cfg)


def test_score_breakdown_sums_to_the_score():
    cluster = make_cluster("Story", outlets=3, hn_points=200)
    total = score_cluster(cluster, RankingConfig())
    assert abs(sum(cluster.score_breakdown.values()) - total) < 1e-9
    assert set(cluster.score_breakdown) == {"recency", "source", "corroboration", "hn"}


def test_runtime_capacity_tracks_the_target():
    short = RankingConfig(target_runtime_minutes=5, words_per_minute=150)
    long = RankingConfig(target_runtime_minutes=20, words_per_minute=150)
    assert runtime_capacity(short) < runtime_capacity(long)
    assert runtime_capacity(short) >= 1


def test_selection_respects_max_stories():
    cfg = RankingConfig(max_stories=5, target_runtime_minutes=60)
    clusters = [make_cluster(f"World story {i}", category="world") for i in range(20)]
    assert len(select(clusters, cfg)) == 5


def test_runtime_budget_can_bind_before_max_stories():
    cfg = RankingConfig(max_stories=12, target_runtime_minutes=4, words_per_minute=150)
    clusters = [make_cluster(f"Story {i}", category="world") for i in range(20)]
    selected = select(clusters, cfg)
    assert len(selected) == runtime_capacity(cfg) < 12


def test_world_news_is_not_crowded_out_by_ai():
    """The quota minimum is the whole point: AI outscores world here."""
    cfg = RankingConfig(
        max_stories=8,
        target_runtime_minutes=60,
        quotas={"world": Quota(3, 5), "ai": Quota(2, 5), "tech": Quota(0, 4)},
    )
    clusters = [make_cluster(f"AI story {i}", category="ai", outlets=4, hn_points=800) for i in range(15)]
    clusters += [make_cluster(f"World story {i}", category="world", outlets=1, age_hours=20) for i in range(5)]

    counts = Counter(c.category for c in select(clusters, cfg))
    assert counts["world"] >= 3
    assert counts["ai"] <= 5


def test_category_maximum_is_enforced():
    cfg = RankingConfig(
        max_stories=10, target_runtime_minutes=60,
        quotas={"tech": Quota(0, 2), "world": Quota(0, 10)},
    )
    clusters = [make_cluster(f"Tech story {i}", category="tech") for i in range(8)]
    clusters += [make_cluster(f"World story {i}", category="world") for i in range(8)]
    counts = Counter(c.category for c in select(clusters, cfg))
    assert counts["tech"] == 2


def test_unknown_categories_still_get_selected():
    cfg = RankingConfig(max_stories=4, target_runtime_minutes=60, quotas={"world": Quota(1, 2)})
    clusters = [make_cluster(f"Sport story {i}", category="sport") for i in range(6)]
    assert len(select(clusters, cfg)) == 4


def test_episode_order_follows_config_categories_then_score():
    cfg = RankingConfig(quotas={"world": Quota(0, 9), "ai": Quota(0, 9), "tech": Quota(0, 9)})
    clusters = [
        make_cluster("Tech", category="tech"),
        make_cluster("AI", category="ai"),
        make_cluster("World", category="world"),
    ]
    for cluster in clusters:
        score_cluster(cluster, cfg)
    ordered = order_for_episode(clusters, cfg)
    assert [c.category for c in ordered] == ["world", "ai", "tech"]


def test_group_by_category_preserves_order():
    cfg = RankingConfig(quotas={"world": Quota(0, 9), "ai": Quota(0, 9)})
    clusters = [make_cluster("A", category="ai"), make_cluster("W", category="world")]
    for cluster in clusters:
        score_cluster(cluster, cfg)
    assert [name for name, _ in group_by_category(clusters, cfg)] == ["world", "ai"]


def test_select_of_nothing_is_nothing():
    assert select([], RankingConfig()) == []
