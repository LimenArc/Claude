from __future__ import annotations

import pytest
from test_publish import write_mp3

from dailywire import cli


def test_help_exits_cleanly(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    assert "dailywire" in capsys.readouterr().out


def test_a_command_is_required():
    with pytest.raises(SystemExit):
        cli.main([])


def test_run_flags_reach_the_pipeline(cfg, monkeypatch, tmp_path):
    captured = {}

    def fake_run(config, options):
        captured["options"] = options
        return None

    monkeypatch.setattr(cli, "load_config", lambda path: cfg)
    monkeypatch.setattr("dailywire.pipeline.run", fake_run)

    assert cli.main(["run", "--date", "2026-08-06", "--skip-audio", "--tts", "kokoro", "--force"]) == 1
    options = captured["options"]
    assert options.date.isoformat() == "2026-08-06"
    assert options.skip_audio and options.force
    assert options.tts_provider == "kokoro"


def test_run_rejects_a_bad_date():
    with pytest.raises(SystemExit):
        cli.main(["run", "--date", "yesterday"])


def test_feed_command_writes_the_feed(cfg, monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_config", lambda path: cfg)
    assert cli.main(["feed"]) == 0
    assert (cfg.public_path / "feed.xml").exists()
    assert "feed.xml" in capsys.readouterr().out


def test_list_command_reports_episodes(cfg, monkeypatch, capsys):
    write_mp3(cfg.episodes_path / "2026-08-06.mp3")
    monkeypatch.setattr(cli, "load_config", lambda path: cfg)
    assert cli.main(["list"]) == 0
    assert "2026-08-06" in capsys.readouterr().out


def test_list_command_with_no_episodes(cfg, monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_config", lambda path: cfg)
    cli.main(["list"])
    assert "no episodes yet" in capsys.readouterr().out


def test_prune_command(cfg, monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_config", lambda path: cfg)
    assert cli.main(["prune", "--days", "30"]) == 0
    assert "forgot 0 items" in capsys.readouterr().out


def test_doctor_reports_missing_pieces(cfg, monkeypatch, capsys):
    """Piper has no voice in the test config, so doctor must fail loudly."""
    monkeypatch.setattr(cli, "load_config", lambda path: cfg)
    monkeypatch.setattr("dailywire.cluster.load_embedder", lambda name: None)
    code = cli.main(["doctor"])
    out = capsys.readouterr().out
    assert code == 1
    assert "ffmpeg" in out and "FAIL" in out
    assert "TF-IDF fallback" in out
