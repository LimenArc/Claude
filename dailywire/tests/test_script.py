from __future__ import annotations

from datetime import date

import pytest
from conftest import make_cluster

from dailywire.llm.base import LLMError, LLMProvider
from dailywire.script import (
    build_offline_script,
    build_script,
    fallback_summary,
    parse_segments,
    show_notes,
    stitch_prompt,
    summarize_clusters,
    summary_prompt,
)
from dailywire.text import lint_speakable

WHEN = date(2026, 8, 6)


class FakeLLM(LLMProvider):
    """Records calls and returns canned output."""

    name = "fake"

    def __init__(self, summary: str = "A thing happened, the BBC reports.", script: str | None = None):
        self.summary = summary
        self.script = script
        self.calls: list[tuple[str, str]] = []

    def complete(self, system, user, *, max_tokens=None, temperature=None):
        self.calls.append((system, user))
        if "script editor" in system:
            if self.script is None:
                raise LLMError("no script configured")
            return self.script
        return self.summary


class BrokenLLM(LLMProvider):
    name = "broken"

    def complete(self, system, user, *, max_tokens=None, temperature=None):
        raise LLMError("upstream is down")


@pytest.fixture
def clusters():
    return [
        make_cluster("Central bank raises rates", category="world", outlets=3),
        make_cluster("Chipmaker unveils accelerator", category="tech", outlets=1),
        make_cluster("New model tops benchmark", category="ai", outlets=2),
    ]


def test_summary_prompt_carries_outlets_and_bodies(clusters):
    prompt = summary_prompt(clusters[0])
    assert "OUTLETS COVERING THIS STORY (3)" in prompt
    assert "Outlet 0" in prompt and "HEADLINE:" in prompt


def test_one_llm_call_per_cluster(clusters):
    llm = FakeLLM()
    summarize_clusters(clusters, llm)
    assert len(llm.calls) == len(clusters)
    assert all(c.summary == "A thing happened, the BBC reports." for c in clusters)


def test_summaries_fall_back_when_the_model_fails(clusters):
    summarize_clusters(clusters, BrokenLLM())
    assert all(c.summary for c in clusters)
    assert "reports:" in clusters[0].summary


def test_fallback_summary_mentions_corroborating_outlets():
    cluster = make_cluster("Rates rise", outlets=3)
    text = fallback_summary(cluster)
    assert "Outlet 0" in text and "and" in text


def test_fallback_summary_does_not_copy_body_text():
    cluster = make_cluster("Rates rise", outlets=1)
    cluster.items[0].full_text = "SECRET BODY PROSE that must not be reproduced verbatim."
    assert "SECRET BODY PROSE" not in fallback_summary(cluster)


def test_parse_segments_splits_on_markers_and_drops_them():
    script = (
        "[SEGMENT: Cold open]\nGood morning.\n\n"
        "[SEGMENT: World News]\nRates went up.\n\n"
        "[SEGMENT: Sign-off]\nThat's all."
    )
    segments = parse_segments(script)
    assert [s.title for s in segments] == ["Cold open", "World News", "Sign-off"]
    assert [s.category for s in segments] == ["intro", "world", "outro"]
    assert "SEGMENT" not in "".join(s.text for s in segments)


def test_parse_segments_keeps_text_before_the_first_marker():
    segments = parse_segments("Loose opener.\n[SEGMENT: World News]\nBody.")
    assert segments[0].title == "Cold open"
    assert segments[0].text == "Loose opener."


def test_parse_segments_without_markers_is_empty():
    assert parse_segments("Just prose with no markers.") == []


def test_build_script_uses_the_stitched_output(cfg, clusters):
    stitched = (
        "[SEGMENT: Cold open]\nIt is August 6th. Here is the news.\n\n"
        "[SEGMENT: World News]\nThe central bank raised rates by 25%, the BBC reports.\n\n"
        "[SEGMENT: Sign-off]\nThat's your briefing."
    )
    llm = FakeLLM(script=stitched)
    episode = build_script(clusters, cfg, llm, WHEN)

    assert episode.date == "2026-08-06"
    assert [s.title for s in episode.segments] == ["Cold open", "World News", "Sign-off"]
    assert "twenty-five percent" in episode.script
    assert episode.word_count > 0


def test_build_script_output_is_speakable(cfg, clusters):
    stitched = (
        "[SEGMENT: Cold open]\n## Good morning\n- Read https://bbc.co.uk/news for more.\n\n"
        "[SEGMENT: World News]\nRates rose 25% in 2026, per the BBC.\n\n"
        "[SEGMENT: Sign-off]\nDone."
    )
    episode = build_script(clusters, cfg, FakeLLM(script=stitched), WHEN)
    assert lint_speakable(episode.script) == []
    assert "http" not in episode.script


def test_build_script_falls_back_when_markers_are_missing(cfg, clusters):
    episode = build_script(clusters, cfg, FakeLLM(script="One long blob with no markers."), WHEN)
    assert len(episode.segments) >= 2
    assert any(s.category == "world" for s in episode.segments)


def test_build_script_without_an_llm_still_produces_an_episode(cfg, clusters):
    episode = build_script(clusters, cfg, None, WHEN)
    assert len(episode.segments) >= 4  # cold open + three categories + sign-off
    assert lint_speakable(episode.script) == []
    assert cfg.script.sign_off.split(".")[0] in episode.script


def test_offline_script_covers_every_story(cfg, clusters):
    summarize_clusters(clusters, None)
    script = build_offline_script(clusters, cfg, WHEN)
    for cluster in clusters:
        assert cluster.summary in script


def test_segments_carry_links_for_the_show_notes(cfg, clusters):
    episode = build_script(clusters, cfg, None, WHEN)
    world = next(s for s in episode.segments if s.category == "world")
    assert world.links and all(link.startswith("http") for link in world.links)


def test_stitch_prompt_lists_every_story_with_its_outlets(cfg, clusters):
    summarize_clusters(clusters, None)
    prompt = stitch_prompt(clusters, cfg, WHEN)
    assert prompt.count("- Story:") == len(clusters)
    assert "[SEGMENT: World News]" in prompt
    assert "[SEGMENT: Sign-off]" in prompt


def test_show_notes_include_sources_and_script(cfg, clusters):
    episode = build_script(clusters, cfg, None, WHEN)
    notes = show_notes(episode, cfg)
    assert "## Stories" in notes and "## Script" in notes
    assert "### World News" in notes
    for cluster in clusters:
        for item in cluster.items:
            assert item.url in notes
