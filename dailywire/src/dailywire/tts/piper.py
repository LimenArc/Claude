"""Piper: local, offline, CPU-only neural TTS. The default provider.

Install the binary from https://github.com/rhasspy/piper and a voice from
https://huggingface.co/rhasspy/piper-voices (you want the .onnx and the
matching .onnx.json side by side).
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from ..config import PiperConfig, TTSConfig
from .base import TTSError, TTSProvider

log = logging.getLogger(__name__)


class PiperTTS(TTSProvider):
    name = "piper"
    suffix = ".wav"

    def __init__(self, cfg: TTSConfig, piper: PiperConfig, root: Path | None = None):
        self.cfg = cfg
        self.piper = piper
        self.root = root or Path.cwd()

    @property
    def binary(self) -> str | None:
        return shutil.which(self.piper.binary) or (
            self.piper.binary if Path(self.piper.binary).exists() else None
        )

    @property
    def voice_path(self) -> Path:
        voice = Path(self.piper.voice).expanduser()
        return voice if voice.is_absolute() else (self.root / voice)

    def available(self) -> bool:
        if self.binary is None:
            log.warning("piper binary %r not found on PATH", self.piper.binary)
            return False
        if not self.voice_path.exists():
            log.warning("piper voice %s not found", self.voice_path)
            return False
        return True

    def describe(self) -> str:
        return f"piper({self.voice_path.name})"

    def synthesize(self, text: str, out_path: Path) -> Path:
        binary = self.binary
        if binary is None:
            raise TTSError(f"piper binary {self.piper.binary!r} not found")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            binary,
            "--model", str(self.voice_path),
            "--output_file", str(out_path),
            "--length_scale", str(self.piper.length_scale),
        ]
        if self.piper.speaker:
            cmd += ["--speaker", str(self.piper.speaker)]

        proc = subprocess.run(
            cmd, input=text.encode("utf-8"), capture_output=True, check=False
        )
        if proc.returncode != 0 or not out_path.exists():
            raise TTSError(
                f"piper failed (exit {proc.returncode}): {proc.stderr.decode('utf-8', 'replace')[:400]}"
            )
        return out_path
