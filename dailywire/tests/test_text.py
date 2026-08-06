from __future__ import annotations

import pytest

from dailywire.text import (
    chunk_text,
    hamming,
    lint_speakable,
    normalize,
    simhash,
    speakable,
    spell_integer,
    spell_out_numbers,
    spell_year,
    strip_markup,
    strip_urls,
    url_hash,
)


def test_normalize_strips_accents_and_punctuation():
    assert normalize("Ürsula's Café -- OPEN!") == "ursula's cafe open"


def test_url_hash_ignores_tracking_and_trailing_slash():
    a = url_hash("https://example.com/story?utm_source=rss&utm_medium=feed")
    b = url_hash("http://www.example.com/story/")
    assert a == b


def test_url_hash_distinguishes_different_paths():
    assert url_hash("https://example.com/a") != url_hash("https://example.com/b")


def test_simhash_near_duplicate_titles_are_close():
    a = simhash("Acme acquires Beta Corp in cash deal")
    b = simhash("Acme acquires Beta Corp in a cash deal for $2 billion")
    c = simhash("Volcano erupts in Iceland, flights grounded")
    assert hamming(a, b) < hamming(a, c)


def test_simhash_of_empty_text_is_zero():
    assert simhash("   ") == 0


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, "zero"),
        (7, "seven"),
        (13, "thirteen"),
        (42, "forty-two"),
        (100, "one hundred"),
        (365, "three hundred sixty-five"),
        (1200, "one thousand two hundred"),
        (2_500_000, "two million five hundred thousand"),
    ],
)
def test_spell_integer(value, expected):
    assert spell_integer(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [(1998, "nineteen ninety-eight"), (2007, "two thousand seven"), (1900, "nineteen hundred")],
)
def test_spell_year(value, expected):
    assert spell_year(value) == expected


def test_spell_out_numbers_handles_currency_percent_and_ordinals():
    text = "The $2.5B deal closed on the 3rd, lifting revenue 12% to $1,200 a share."
    out = spell_out_numbers(text)
    assert "two point five billion dollars" in out
    assert "third" in out
    assert "twelve percent" in out
    assert not any(ch.isdigit() for ch in out)


def test_spell_out_numbers_leaves_model_names_alone():
    out = spell_out_numbers("They trained GPT-4 on H100 GPUs over 5G.")
    assert "GPT-4" in out and "H100" in out and "5G" in out


def test_spell_out_numbers_decimal_and_year():
    assert "three point one four" in spell_out_numbers("pi is about 3.14")
    assert "nineteen sixty-nine" in spell_out_numbers("Apollo landed in 1969.")


def test_strip_urls_removes_links_and_bare_domains():
    out = strip_urls("Read it at https://example.com/x or on arstechnica.com today")
    assert "http" not in out and "example.com" not in out and "arstechnica.com" not in out
    assert "arstechnica" in out


def test_strip_urls_leaves_arxiv_category_names_alone():
    """"cs.AI" is not a domain, however much it looks like one."""
    text = "arXiv cs.AI and cs.LG both list the paper."
    assert strip_urls(text) == text
    assert "cs.AI" in speakable(text)


def test_strip_markup_removes_bullets_and_emphasis():
    out = strip_markup("## Heading\n- **bold** point\n1. numbered\n[link](https://x.com)")
    assert "#" not in out and "**" not in out
    assert out.splitlines()[1].startswith("bold")
    assert "link" in out and "https" not in out


def test_speakable_is_clean_for_the_ear():
    raw = (
        "## Top story\n"
        "- Reuters reports a 12% rise, per https://reuters.com/x.\n"
        "- The deal is worth $3.4B & closes in 2026."
    )
    out = speakable(raw)
    assert lint_speakable(out) == []
    assert "twelve percent" in out
    assert "three point four billion dollars" in out
    assert " and " in out


def test_lint_flags_problems():
    problems = lint_speakable("See https://example.com for the 42 findings")
    assert any("URL" in p for p in problems)
    assert any("numerals" in p for p in problems)


def test_chunk_text_respects_limit_and_keeps_everything():
    text = " ".join(f"Sentence number {i} goes here." for i in range(200))
    chunks = chunk_text(text, max_chars=300)
    assert all(len(c) <= 300 for c in chunks)
    assert len(chunks) > 1
    assert " ".join(chunks).split() == text.split()


def test_chunk_text_splits_a_pathological_sentence():
    chunks = chunk_text("word " * 500, max_chars=200)
    assert all(len(c) <= 200 for c in chunks)


def test_chunk_text_short_text_is_one_chunk():
    assert chunk_text("Short enough.", 100) == ["Short enough."]
    assert chunk_text("   ") == []
