"""TTS providers: Piper (default, local), Kokoro (local), hosted API."""

from __future__ import annotations

import logging
from pathlib import Path

from ..config import Config
from .base import TTSError, TTSProvider
from .hosted import HostedTTS
from .kokoro import KokoroTTS
from .piper import PiperTTS

log = logging.getLogger(__name__)

__all__ = ["HostedTTS", "KokoroTTS", "PiperTTS", "TTSError", "TTSProvider", "get_provider"]


def get_provider(cfg: Config, name: str | None = None) -> TTSProvider:
    """Build the configured TTS provider.

    Raises TTSError rather than silently substituting another voice: an
    episode narrated by an unexpected voice is worse than a loud failure.
    """
    name = (name or cfg.tts.provider).lower()
    if name == "piper":
        provider: TTSProvider = PiperTTS(cfg.tts, cfg.tts.piper, root=cfg.root)
    elif name == "kokoro":
        provider = KokoroTTS(cfg.tts, cfg.tts.kokoro)
    elif name in ("hosted", "openai", "api"):
        provider = HostedTTS(cfg.tts, cfg.tts.hosted)
    else:
        raise TTSError(f"unknown TTS provider {name!r}; choose piper, kokoro or hosted")

    if not provider.available():
        raise TTSError(
            f"TTS provider {provider.describe()} is not usable -- see the warnings above. "
            "Fix its configuration, or pick another with --tts."
        )
    log.info("using TTS provider %s", provider.describe())
    return provider
