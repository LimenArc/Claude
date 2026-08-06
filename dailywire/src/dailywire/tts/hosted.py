"""Hosted TTS over the OpenAI-compatible /audio/speech endpoint.

Keyed off an environment variable named in config ([tts.hosted].api_key_env);
the key itself never touches the config file. Any provider exposing that route
works -- OpenAI, DeepInfra, a local speech server, and so on.
"""

from __future__ import annotations

import logging
import os
import random
import time
from pathlib import Path

import httpx

from ..config import HostedTTSConfig, TTSConfig
from .base import TTSError, TTSProvider

log = logging.getLogger(__name__)

_RETRY_STATUS = {408, 429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3


class HostedTTS(TTSProvider):
    name = "hosted"

    def __init__(self, cfg: TTSConfig, hosted: HostedTTSConfig, client: httpx.Client | None = None):
        self.cfg = cfg
        self.hosted = hosted
        self.api_key = os.environ.get(hosted.api_key_env, "")
        self._client = client or httpx.Client(timeout=120.0)

    @property
    def suffix(self) -> str:
        return f".{self.hosted.response_format or 'mp3'}"

    def available(self) -> bool:
        if not self.api_key:
            log.warning("hosted TTS needs %s to be set", self.hosted.api_key_env)
            return False
        return bool(self.hosted.base_url and self.hosted.model)

    def describe(self) -> str:
        return f"hosted({self.hosted.model}/{self.hosted.voice})"

    def synthesize(self, text: str, out_path: Path) -> Path:
        url = self.hosted.base_url.rstrip("/") + "/audio/speech"
        payload = {
            "model": self.hosted.model,
            "voice": self.hosted.voice,
            "input": text,
            "response_format": self.hosted.response_format,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        last_error = "unknown error"
        for attempt in range(_MAX_ATTEMPTS):
            if attempt:
                time.sleep(min(20.0, 2**attempt) + random.uniform(0, 0.5))
            try:
                resp = self._client.post(url, json=payload, headers=headers)
            except httpx.HTTPError as exc:
                last_error = f"transport error: {exc}"
                continue
            if resp.status_code in _RETRY_STATUS:
                last_error = f"HTTP {resp.status_code}"
                continue
            if resp.status_code >= 400:
                raise TTSError(f"{url} returned HTTP {resp.status_code}: {resp.text[:300]}")
            if not resp.content:
                last_error = "empty response body"
                continue
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(resp.content)
            return out_path

        raise TTSError(f"hosted TTS failed after {_MAX_ATTEMPTS} attempts: {last_error}")
