"""LLM providers.

`get_provider` returns None when nothing is configured -- the script builder
then falls back to a deterministic extractive assembly, so `dailywire run`
still produces an episode on a machine with no model access at all.
"""

from __future__ import annotations

import logging

from ..config import LLMConfig
from .anthropic import AnthropicLLM
from .base import LLMError, LLMProvider
from .openai_compat import OpenAICompatibleLLM

log = logging.getLogger(__name__)

__all__ = [
    "AnthropicLLM",
    "LLMError",
    "LLMProvider",
    "OpenAICompatibleLLM",
    "PROVIDERS",
    "get_provider",
]

PROVIDERS: dict[str, type[LLMProvider]] = {
    "openai_compatible": OpenAICompatibleLLM,
    "openai": OpenAICompatibleLLM,
    "anthropic": AnthropicLLM,
}


def get_provider(cfg: LLMConfig) -> LLMProvider | None:
    if cfg.provider in ("none", "off", ""):
        return None
    cls = PROVIDERS.get(cfg.provider)
    if cls is None:
        raise LLMError(
            f"unknown LLM provider {cfg.provider!r}; choose one of: {', '.join(sorted(PROVIDERS))}"
        )
    provider = cls(cfg)
    if not provider.available():
        log.warning(
            "LLM provider %s is not configured (is %s set?); falling back to extractive summaries",
            cfg.provider, cfg.api_key_env,
        )
        return None
    log.info("using LLM provider %s", provider.describe())
    return provider
