"""Kokoro: local neural TTS with a warmer voice than Piper, at more CPU cost.

Requires the optional extra: `uv sync --extra kokoro`.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..config import KokoroConfig, TTSConfig
from .base import TTSError, TTSProvider

log = logging.getLogger(__name__)

SAMPLE_RATE = 24000  # Kokoro always renders at 24 kHz


class KokoroTTS(TTSProvider):
    name = "kokoro"
    suffix = ".wav"

    def __init__(self, cfg: TTSConfig, kokoro: KokoroConfig):
        self.cfg = cfg
        self.kokoro = kokoro
        self._pipeline = None

    def available(self) -> bool:
        try:
            import kokoro  # noqa: F401
            import soundfile  # noqa: F401
        except ImportError:
            log.warning("kokoro not installed; try `uv sync --extra kokoro`")
            return False
        return True

    def describe(self) -> str:
        return f"kokoro({self.kokoro.voice})"

    def _get_pipeline(self):
        if self._pipeline is None:
            from kokoro import KPipeline

            self._pipeline = KPipeline(lang_code=self.kokoro.lang_code)
        return self._pipeline

    def synthesize(self, text: str, out_path: Path) -> Path:
        try:
            import numpy as np
            import soundfile as sf
        except ImportError as exc:
            raise TTSError(f"kokoro dependencies missing: {exc}") from exc

        pipeline = self._get_pipeline()
        chunks = []
        for result in pipeline(text, voice=self.kokoro.voice, speed=self.kokoro.speed):
            audio = result[-1] if isinstance(result, tuple) else result
            if audio is None:
                continue
            chunks.append(np.asarray(audio, dtype="float32"))
        if not chunks:
            raise TTSError("kokoro produced no audio")

        out_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_path), np.concatenate(chunks), SAMPLE_RATE)
        return out_path
