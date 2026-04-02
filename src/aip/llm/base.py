"""Abstract base class for LLM providers."""
from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    model: str

    @abstractmethod
    async def complete(
        self, prompt: str, system: str | None = None, max_tokens: int = 4096
    ) -> str:
        """Send a prompt and return the completion text."""

    def get_model_name(self) -> str:
        return self.model
