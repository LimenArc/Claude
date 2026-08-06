"""Clustering tests exercise the TF-IDF fallback path.

The embedding model is deliberately not downloaded in tests -- `load_embedder`
returning None is exactly the situation the fallback exists for.
"""

from __future__ import annotations

import pytest
from conftest import make_item

import dailywire.cluster as cluster_mod
from dailywire.cluster import _category, cluster_items
from dailywire.config import ClusterConfig


@pytest.fixture(autouse=True)
def no_embedder(monkeypatch):
    monkeypatch.setattr(cluster_mod, "load_embedder", lambda name: None)


def test_same_story_from_three_outlets_forms_one_cluster():
    items = [
        make_item(
            "Central bank raises interest rates to curb inflation",
            source="BBC", url="https://bbc.example/1",
            summary="The central bank raised interest rates today to curb inflation.",
        ),
        make_item(
            "Central bank raises rates in bid to curb inflation",
            source="Al Jazeera", url="https://aj.example/2",
            summary="Policymakers raised interest rates, aiming to curb inflation.",
        ),
        make_item(
            "Rate rise announced by central bank to fight inflation",
            source="DW", url="https://dw.example/3",
            summary="The central bank announced a rate rise to fight inflation.",
        ),
    ]
    clusters = cluster_items(items, ClusterConfig())
    assert len(clusters) == 1
    assert clusters[0].corroboration == 3
    assert set(clusters[0].outlets) == {"BBC", "Al Jazeera", "DW"}


def test_unrelated_stories_stay_apart():
    items = [
        make_item("Central bank raises interest rates", source="BBC",
                  summary="Interest rates went up."),
        make_item("Volcano erupts in Iceland grounding flights", source="DW",
                  summary="A volcano erupted, flights are grounded."),
        make_item("New transformer architecture cuts training cost", source="arXiv cs.LG",
                  category="ai", summary="A new architecture reduces training compute."),
    ]
    clusters = cluster_items(items, ClusterConfig())
    assert len(clusters) == 3


def test_items_far_apart_in_time_are_not_merged():
    cfg = ClusterConfig(max_cluster_span_hours=6)
    items = [
        make_item("Central bank raises interest rates to curb inflation", source="BBC",
                  url="https://a.example/1", age_hours=1,
                  summary="The central bank raised interest rates to curb inflation."),
        make_item("Central bank raises interest rates to curb inflation", source="DW",
                  url="https://b.example/2", age_hours=40,
                  summary="The central bank raised interest rates to curb inflation."),
    ]
    assert len(cluster_items(items, cfg)) == 2


def test_single_item_and_empty_input():
    assert cluster_items([], ClusterConfig()) == []
    one = cluster_items([make_item("Only story")], ClusterConfig())
    assert len(one) == 1 and one[0].category == "world"


def test_cluster_category_follows_the_majority():
    items = [
        make_item("Story", source="A", category="world"),
        make_item("Story", source="B", category="world"),
        make_item("Story", source="C", category="tech"),
    ]
    assert _category(items) == "world"


def test_cluster_category_ties_break_on_source_weight():
    items = [
        make_item("Story", source="A", category="world", weight=1.2),
        make_item("Story", source="B", category="tech", weight=0.8),
    ]
    assert _category(items) == "world"


def test_lead_item_is_the_heaviest_source():
    items = [
        make_item("Rates rise", source="Small blog", weight=0.5, url="https://s.example/1",
                  summary="Rates rose today across the board."),
        make_item("Rates rise", source="BBC", weight=1.5, url="https://b.example/2",
                  summary="Rates rose today across the board."),
    ]
    clusters = cluster_items(items, ClusterConfig())
    assert clusters[0].lead.source == "BBC"
