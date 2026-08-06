"""Any OpenAI-compatible /chat/completions endpoint.

Works with OpenAI itself, vLLM, llama.cpp's server, LM Studio, Ollama's /v1
shim, Together, Groq, OpenRouter -- anything speaking that wire format.
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

# Retried: rate limits and transient server errors.
_RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


class OpenAICompatibleLLM(LLMProvider):
    name = "openai_compatible"

    def __init__(self, cfg: LLMConfig, client: httpx.Client | None = None):
        self.cfg = cfg
        self.api_key = os.environ.get(cfg.api_key_env, "")
        self._client = client or httpx.Client(timeout=cfg.timeout)

    def available(self) -> bool:
        # Local servers routinely need no key, so only the URL and model are
        # strictly required.
        return bool(self.cfg.base_url and self.cfg.model)

    def describe(self) -> str:
        return f"{self.name}({self.cfg.model} @ {self.cfg.base_url})"

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        url = self.cfg.base_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.cfg.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.cfg.temperature if temperature is None else temperature,
            "max_tokens": self.cfg.max_tokens if max_tokens is None else max_tokens,
        }

        last_error = "unknown error"
        for attempt in range(self.cfg.max_retries):
            if attempt:
                delay = min(30.0, 2**attempt) + random.uniform(0, 0.5)
                log.info("LLM retry %d/%d in %.1fs (%s)", attempt, self.cfg.max_retries - 1, delay, last_error)
                time.sleep(delay)
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
                data = resp.json()
                return (data["choices"][0]["message"]["content"] or "").strip()
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                last_error = f"malformed response: {exc}"
                continue

        raise LLMError(f"LLM call failed after {self.cfg.max_retries} attempts: {last_error}")
