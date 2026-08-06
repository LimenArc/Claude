from __future__ import annotations

import shutil
from pathlib import Path

import fake_ffmpeg as fake_ffmpeg_mod
import pytest

from dailywire import audio
from dailywire.models import Episode, Segment
from dailywire.tts.base import TTSError, TTSProvider

FFMPEG = shutil.which("ffmpeg")

# Real ffmpeg output from a two-pass loudnorm measurement run.
FFMPEG_STDERR = """\
[Parsed_loudnorm_0 @ 0x55d4]
{
	"input_i" : "-21.28",
	"input_tp" : "-4.51",
	"input_lra" : "6.20",
	"input_thresh" : "-31.51",
	"output_i" : "-16.02",
	"output_tp" : "-1.50",
	"output_lra" : "5.90",
	"output_thresh" : "-26.24",
	"normalization_type" : "dynamic",
	"target_offset" : "0.02"
}
[out#0 @ 0x55d4] video:0kB audio:1720kB
"""


def test_parse_loudness_reads_the_measurement_block():
    measured = audio.parse_loudness(FFMPEG_STDERR)
    assert measured is not None
    assert measured["input_i"] == "-21.28"
    assert measured["target_offset"] == "0.02"


def test_parse_loudness_of_unrelated_output_is_none():
    assert audio.parse_loudness("ffmpeg version 6.0\nnothing to see here") is None


def test_concat_list_escapes_quotes(tmp_path):
    tricky = tmp_path / "it's here.wav"
    tricky.write_bytes(b"")
    listing = audio.write_concat_list([tricky], tmp_path / "list.txt").read_text()
    assert listing.startswith("file '")
    assert r"'\''" in listing


def test_probe_duration_of_a_missing_file_is_zero(tmp_path):
    assert audio.probe_duration(tmp_path / "nope.wav") == 0.0


def test_concat_with_no_chunks_raises(tmp_path):
    with pytest.raises(TTSError):
        audio.concat_and_normalize([], tmp_path / "out.mp3", None)


class SilentTTS(TTSProvider):
    """Writes a fixed-length silent WAV, so narration can run without a model."""

    name = "silent"
    suffix = ".wav"

    def __init__(self, seconds: float = 1.0, sample_rate: int = 22050):
        self.seconds = seconds
        self.sample_rate = sample_rate
        self.calls: list[str] = []

    def synthesize(self, text: str, out_path: Path) -> Path:
        self.calls.append(text)
        audio._run([
            audio.require_ffmpeg(), "-y", "-f", "lavfi",
            "-i", f"anullsrc=r={self.sample_rate}:cl=mono",
            "-t", f"{self.seconds}", str(out_path),
        ])
        return out_path


@pytest.fixture
def fake_ffmpeg(tmp_path, monkeypatch):
    """Put stub ffmpeg/ffprobe on PATH: one byte of file is one millisecond."""
    fake_ffmpeg_mod.prepend_to_path(fake_ffmpeg_mod.install(tmp_path / "bin"), monkeypatch)
    return tmp_path / "bin"


@pytest.fixture
def episode():
    return Episode(
        date="2026-08-06",
        script="Good morning. Rates rose. That's all.",
        segments=[
            Segment(title="Cold open", category="intro", text="Good morning."),
            Segment(title="World News", category="world", text="Rates rose today."),
            Segment(title="Sign-off", category="outro", text="That's all."),
        ],
    )


@pytest.mark.skipif(FFMPEG is None, reason="ffmpeg not installed")
def test_narrate_produces_an_mp3_with_chapter_timings(cfg, episode):
    provider = SilentTTS(seconds=1.0, sample_rate=cfg.tts.sample_rate)
    out = cfg.episodes_path / "2026-08-06.mp3"
    audio.narrate(episode, provider, cfg, out)

    assert out.exists() and out.stat().st_size > 0
    assert len(provider.calls) == 3
    assert episode.duration_ms > 0

    # Chapters must be contiguous, ordered, and inside the file.
    assert episode.segments[0].start_ms == 0
    for earlier, later in zip(episode.segments, episode.segments[1:]):
        assert earlier.end_ms <= later.start_ms
    assert episode.segments[-1].end_ms <= episode.duration_ms + 1500


@pytest.mark.skipif(FFMPEG is None, reason="ffmpeg not installed")
def test_narrate_chunks_long_segments(cfg, episode):
    cfg.tts.chunk_chars = 40
    episode.segments = [
        Segment(title="World News", category="world",
                text="Rates rose today. " * 20)
    ]
    provider = SilentTTS(seconds=0.2, sample_rate=cfg.tts.sample_rate)
    audio.narrate(episode, provider, cfg, cfg.episodes_path / "x.mp3")
    assert len(provider.calls) > 1
    assert all(len(c) <= 40 for c in provider.calls)


def test_narrate_chapter_timings_are_exact(cfg, episode, fake_ffmpeg):
    """Three one-second segments with 0.7s gaps land on known boundaries."""
    provider = SilentTTS(seconds=1.0)
    out = cfg.episodes_path / "2026-08-06.mp3"
    audio.narrate(episode, provider, cfg, out)

    gap = int(audio.SEGMENT_GAP_SECONDS * 1000)
    starts = [s.start_ms for s in episode.segments]
    ends = [s.end_ms for s in episode.segments]
    assert starts == [0, 1000 + gap, 2 * (1000 + gap)]
    assert ends == [1000, 2000 + gap, 3000 + 2 * gap]
    assert episode.duration_ms == 3000 + 2 * gap
    assert episode.audio_path == str(out)


def test_narrate_scales_timings_to_the_rendered_duration(cfg, episode, fake_ffmpeg, monkeypatch):
    """If the encoder shortens the file, chapters shrink with it proportionally."""
    real_concat = audio.concat_and_normalize
    monkeypatch.setattr(
        audio, "concat_and_normalize",
        lambda files, out, config: real_concat(files, out, config) / 2,
    )
    audio.narrate(episode, SilentTTS(seconds=1.0), cfg, cfg.episodes_path / "x.mp3")

    gap = int(audio.SEGMENT_GAP_SECONDS * 1000)
    assert episode.segments[0].end_ms == 500
    assert episode.segments[-1].end_ms == (3000 + 2 * gap) // 2


def test_narrate_uses_two_pass_loudnorm(cfg, episode, fake_ffmpeg, monkeypatch):
    commands: list[list[str]] = []
    real_run = audio._run
    monkeypatch.setattr(audio, "_run", lambda cmd: (commands.append(cmd), real_run(cmd))[1])

    audio.narrate(episode, SilentTTS(seconds=1.0), cfg, cfg.episodes_path / "x.mp3")

    loudnorm_calls = [c for c in commands if any("loudnorm" in str(a) for a in c)]
    assert len(loudnorm_calls) == 2, "expected a measurement pass and an apply pass"
    measure, apply = loudnorm_calls
    assert "null" in measure
    applied = next(a for a in apply if "loudnorm" in str(a))
    assert "measured_I=-21.28" in applied and "linear=true" in applied
    assert "-16.0" in applied  # the configured target
    assert "libmp3lame" in apply


def test_narrate_skips_empty_segments(cfg, episode, fake_ffmpeg):
    episode.segments.insert(1, Segment(title="Empty", category="other", text="   "))
    provider = SilentTTS(seconds=1.0)
    audio.narrate(episode, provider, cfg, cfg.episodes_path / "x.mp3")
    assert len(provider.calls) == 3


def test_narrate_of_an_empty_script_raises(cfg, fake_ffmpeg):
    episode = Episode(date="2026-08-06", script="", segments=[])
    with pytest.raises(TTSError, match="no audio"):
        audio.narrate(episode, SilentTTS(), cfg, cfg.episodes_path / "x.mp3")


def test_narrate_without_ffmpeg_fails_loudly(cfg, episode, monkeypatch):
    monkeypatch.setattr(audio, "ffmpeg_bin", lambda: None)
    with pytest.raises(TTSError, match="ffmpeg"):
        audio.narrate(episode, SilentTTS(), cfg, cfg.episodes_path / "x.mp3")
