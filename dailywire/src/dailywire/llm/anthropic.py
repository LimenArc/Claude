"""Anthropic Messages API provider.

Same interface as the OpenAI-compatible one; set provider = "anthropic" in
config.toml and point api_key_env at the variable holding your key.
"""

from __future__ import annotations

import logging
import os
import random
import time

import httpx

from ..config import LLMConfig
from .base import LLMError, LLMProvider

log = logging.getLogger(__name__)

_RETRY_STATUS = {408, 409, 429, 500, 502, 503, 504}
API_VERSION = "2023-06-01"


class AnthropicLLM(LLMProvider):
    name = "anthropic"

    def __init__(self, cfg: LLMConfig, client: httpx.Client | None = None):
        self.cfg = cfg
        self.api_key = os.environ.get(cfg.api_key_env, "") or os.environ.get("ANTHROPIC_API_KEY", "")
        self._client = client or httpx.Client(timeout=cfg.timeout)

    def available(self) -> bool:
        return bool(self.api_key and self.cfg.model)

    def describe(self) -> str:
        return f"{self.name}({self.cfg.model})"

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        base = (self.cfg.base_url or "https://api.anthropic.com/v1").rstrip("/")
        url = f"{base}/messages"
        headers = {
            "content-type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": API_VERSION,
        }
        payload = {
            "model": self.cfg.model,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "max_tokens": self.cfg.max_tokens if max_tokens is None else max_tokens,
            "temperature": self.cfg.temperature if temperature is None else temperature,
        }

        last_error = "unknown error"
        for attempt in range(self.cfg.max_retries):
            if attempt:
                time.sleep(min(30.0, 2**attempt) + random.uniform(0, 0.5))
            try:
                resp = self._client.post(url, json=payload, headers=headers)
            except httpx.HTTPError as exc:
                last_error = f"transport error: {exc}"
                continue
            if resp.status_code in _RETRY_STATUS:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                continue
            if resp.status_code >= 400:
                raise LLMError(f"{url} returned HTTP {resp.status_code}: {resp.text[:500]}")
            try:
                blocks = resp.json()["content"]
                return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
            except (ValueError, KeyError, TypeError) as exc:
                last_error = f"malformed response: {exc}"
                continue

        raise LLMError(f"LLM call failed after {self.cfg.max_retries} attempts: {last_error}")
