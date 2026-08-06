"""Narration and audio assembly: chunk, synthesize, concatenate, normalise.

ffmpeg does the joining and EBU R128 loudness normalisation (two-pass
loudnorm, so the measured values feed the applied filter rather than letting
it guess in one pass).
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .config import Config
from .models import Episode, Segment
from .text import chunk_text
from .tts.base import TTSError, TTSProvider

log = logging.getLogger(__name__)

# Beat of silence between segments, so chapter boundaries don't sound abrupt.
SEGMENT_GAP_SECONDS = 0.7


def ffmpeg_bin() -> str | None:
    return shutil.which("ffmpeg")


def ffprobe_bin() -> str | None:
    return shutil.which("ffprobe")


def require_ffmpeg() -> str:
    binary = ffmpeg_bin()
    if binary is None:
        raise TTSError("ffmpeg not found on PATH -- install it (apt install ffmpeg / brew install ffmpeg)")
    return binary


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    log.debug("running: %s", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, check=False)


def probe_duration(path: Path) -> float:
    """Duration in seconds, via ffprobe, or 0.0 if it can't be determined."""
    probe = ffprobe_bin()
    if probe is None:
        return 0.0
    proc = _run([
        probe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ])
    try:
        return float(proc.stdout.decode().strip())
    except (ValueError, AttributeError):
        return 0.0


def make_silence(path: Path, seconds: float, sample_rate: int) -> Path:
    _run([
        require_ffmpeg(), "-y", "-f", "lavfi",
        "-i", f"anullsrc=r={sample_rate}:cl=mono",
        "-t", f"{seconds:.3f}", str(path),
    ])
    return path


def write_concat_list(files: list[Path], list_path: Path) -> Path:
    """ffmpeg concat demuxer manifest. Single quotes are escaped, not banned."""
    lines = []
    for file in files:
        escaped = str(file.resolve()).replace("'", r"'\''")
        lines.append(f"file '{escaped}'")
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return list_path


_LOUDNORM_JSON = re.compile(r"\{[^{}]*\"input_i\"[^{}]*\}", re.DOTALL)


def parse_loudness(stderr: str) -> dict[str, str] | None:
    """Pull the loudnorm JSON block out of ffmpeg's stderr."""
    match = _LOUDNORM_JSON.search(stderr)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except ValueError:
        return None


def measure_loudness(list_path: Path, cfg: Config) -> dict[str, str] | None:
    """Pass one: measure the concatenated audio."""
    proc = _run([
        require_ffmpeg(), "-hide_banner", "-nostats", "-y",
        "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-af",
        f"loudnorm=I={cfg.tts.loudness_i}:TP={cfg.tts.loudness_tp}:"
        f"LRA={cfg.tts.loudness_lra}:print_format=json",
        "-f", "null", "-",
    ])
    measured = parse_loudness(proc.stderr.decode("utf-8", "replace"))
    if measured is None:
        log.warning("could not parse loudnorm measurement; falling back to single-pass")
    return measured


def concat_and_normalize(files: list[Path], out_path: Path, cfg: Config) -> float:
    """Join chunks into a loudness-normalised MP3. Returns duration in seconds."""
    if not files:
        raise TTSError("no audio chunks to concatenate")
    ffmpeg = require_ffmpeg()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="dailywire-concat-") as tmp:
        list_path = write_concat_list(files, Path(tmp) / "chunks.txt")
        measured = measure_loudness(list_path, cfg)

        loudnorm = (
            f"loudnorm=I={cfg.tts.loudness_i}:TP={cfg.tts.loudness_tp}:LRA={cfg.tts.loudness_lra}"
        )
        if measured:
            loudnorm += (
                f":measured_I={measured['input_i']}:measured_TP={measured['input_tp']}"
                f":measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}"
                f":offset={measured.get('target_offset', '0.0')}:linear=true:print_format=summary"
            )

        proc = _run([
            ffmpeg, "-hide_banner", "-nostats", "-y",
            "-f", "concat", "-safe", "0", "-i", str(list_path),
            "-af", loudnorm,
            "-ar", str(cfg.tts.sample_rate), "-ac", "1",
            "-c:a", "libmp3lame", "-b:a", cfg.tts.bitrate,
            str(out_path),
        ])
        if proc.returncode != 0 or not out_path.exists():
            raise TTSError(
                "ffmpeg failed to render the episode: "
                + proc.stderr.decode("utf-8", "replace")[-600:]
            )

    duration = probe_duration(out_path)
    log.info("wrote %s (%.1f MB, %.1f minutes)", out_path, out_path.stat().st_size / 1e6, duration / 60)
    return duration


def narrate(episode: Episode, provider: TTSProvider, cfg: Config, out_path: Path) -> Episode:
    """Synthesize every segment, assemble the MP3, and time the chapters.

    Chapter offsets come from the per-chunk durations, rescaled to the final
    file length so that any drift introduced by re-encoding is spread evenly
    rather than accumulating at the end.
    """
    require_ffmpeg()
    with tempfile.TemporaryDirectory(prefix="dailywire-tts-") as tmp:
        workdir = Path(tmp)
        silence = make_silence(workdir / "gap.wav", SEGMENT_GAP_SECONDS, cfg.tts.sample_rate)

        files: list[Path] = []
        spans: list[tuple[Segment, float, float]] = []
        cursor = 0.0

        for seg_index, segment in enumerate(episode.segments):
            chunks = chunk_text(segment.text, cfg.tts.chunk_chars)
            if not chunks:
                continue
            start = cursor
            for chunk_index, chunk in enumerate(chunks):
                path = workdir / f"seg{seg_index:02d}_{chunk_index:03d}{provider.suffix}"
                provider.synthesize(chunk, path)
                files.append(path)
                cursor += probe_duration(path)
                log.debug("segment %d chunk %d: %.1fs", seg_index, chunk_index, cursor - start)
            spans.append((segment, start, cursor))
            if seg_index < len(episode.segments) - 1:
                files.append(silence)
                cursor += SEGMENT_GAP_SECONDS
            log.info("narrated %r (%d chunks)", segment.title, len(chunks))

        if not files:
            raise TTSError("script produced no audio")

        duration = concat_and_normalize(files, out_path, cfg)

    scale = (duration / cursor) if cursor > 0 and duration > 0 else 1.0
    for segment, start, end in spans:
        segment.start_ms = int(start * scale * 1000)
        segment.end_ms = int(end * scale * 1000)

    episode.audio_path = str(out_path)
    episode.duration_ms = int((duration or cursor) * 1000)
    return episode
