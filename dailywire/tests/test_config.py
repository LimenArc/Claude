from __future__ import annotations

from pathlib import Path

from dailywire.config import Config, load_config

SHIPPED = Path(__file__).parent.parent / "config.toml"


def test_shipped_config_loads():
    cfg = load_config(SHIPPED)
    assert cfg.podcast.title
    assert cfg.sources, "the shipped config should carry a default source list"


def test_shipped_config_covers_the_required_ground():
    cfg = load_config(SHIPPED)
    categories = {s.category for s in cfg.sources}
    assert {"ai", "tech", "world"} <= categories

    world = [s for s in cfg.sources if s.category == "world"]
    assert len(world) >= 2, "world news needs politically distinct outlets"
    assert cfg.ingest.hackernews.enabled and cfg.ingest.hackernews.min_points == 100
    assert set(cfg.ingest.arxiv.categories) == {"cs.AI", "cs.LG"}


def test_every_source_category_has_a_quota():
    cfg = load_config(SHIPPED)
    for source in cfg.sources:
        assert source.category in cfg.ranking.quotas, source.name


def test_quotas_parse_into_min_max():
    cfg = load_config(SHIPPED)
    assert cfg.ranking.quotas["world"].min == 3
    assert cfg.ranking.quotas["world"].max == 5


def test_missing_file_falls_back_to_defaults(tmp_path):
    cfg = load_config(tmp_path / "nope.toml") if (tmp_path / "nope.toml").exists() else Config()
    assert cfg.ranking.max_stories == 12
    assert cfg.tts.provider == "piper"


def test_partial_config_keeps_defaults(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[podcast]\ntitle = "My Show"\n\n[ranking]\nmax_stories = 5\n')
    cfg = load_config(path)
    assert cfg.podcast.title == "My Show"
    assert cfg.ranking.max_stories == 5
    assert cfg.ranking.words_per_minute == 155  # untouched default
    assert cfg.ranking.quotas["world"].min == 3  # default quotas survive
    assert cfg.tts.piper.binary == "piper"


def test_unknown_keys_are_ignored(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[podcast]\ntitle = "X"\nfuture_option = 42\n')
    assert load_config(path).podcast.title == "X"


def test_nested_tts_sections_load(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        '[tts]\nprovider = "hosted"\n\n[tts.hosted]\nmodel = "tts-2"\nvoice = "nova"\n'
    )
    cfg = load_config(path)
    assert cfg.tts.provider == "hosted"
    assert cfg.tts.hosted.model == "tts-2"
    assert cfg.tts.hosted.api_key_env == "DAILYWIRE_TTS_API_KEY"


def test_bare_integer_quota_means_maximum(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[ranking.quotas]\nworld = 4\n")
    cfg = load_config(path)
    assert cfg.ranking.quotas["world"].min == 0
    assert cfg.ranking.quotas["world"].max == 4


def test_relative_paths_resolve_against_the_config_directory(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[general]\nepisodes_dir = "eps"\ndb_path = "state/db.sqlite"\n')
    cfg = load_config(path)
    assert cfg.episodes_path == tmp_path / "eps"
    assert cfg.db_file == tmp_path / "state" / "db.sqlite"


def test_absolute_paths_are_left_alone(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(f'[general]\nepisodes_dir = "{tmp_path}/abs"\n')
    assert load_config(path).episodes_path == tmp_path / "abs"


def test_no_secrets_in_the_shipped_config():
    """Only env var *names* belong here, never keys."""
    text = SHIPPED.read_text()
    assert "api_key_env" in text
    for marker in ("sk-", "Bearer ", "api_key =", "apikey"):
        assert marker not in text
