"""LLM provider interface."""

from __future__ import annotations

import abc


class LLMError(RuntimeError):
    """Raised when a provider cannot produce a completion."""


class LLMProvider(abc.ABC):
    """Anything that can turn a system+user prompt into text.

    Implementations are synchronous: the pipeline makes a dozen calls per run,
    and keeping this blocking keeps retry and rate-limit handling simple.
    """

    name: str = "base"

    @abc.abstractmethod
    def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Return the assistant's reply as plain text."""

    def available(self) -> bool:
        """Whether this provider is configured well enough to be used."""
        return True

    def describe(self) -> str:
        return self.name
