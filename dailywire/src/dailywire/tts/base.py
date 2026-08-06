"""Text-to-speech provider interface."""

from __future__ import annotations

import abc
from pathlib import Path


class TTSError(RuntimeError):
    """Raised when synthesis fails."""


class TTSProvider(abc.ABC):
    """Synthesises one chunk of text into one audio file.

    Chunking, concatenation and loudness normalisation are handled by
    audio.py, so an implementation only has to render the text it is handed.
    """

    name: str = "base"
    #: Suffix of the files this provider writes, including the dot.
    suffix: str = ".wav"

    @abc.abstractmethod
    def synthesize(self, text: str, out_path: Path) -> Path:
        """Render `text` to `out_path`, returning the path actually written."""

    def available(self) -> bool:
        """Whether this provider can run right now (binary present, key set)."""
        return True

    def describe(self) -> str:
        return self.name
