"""Claude / Anthropic adapter using the anthropic SDK directly."""
from __future__ import annotations

import anthropic

from aip.llm.base import LLMProvider


class ClaudeProvider(LLMProvider):
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self.client = anthropic.AsyncAnthropic()

    async def complete(
        self, prompt: str, system: str | None = None, max_tokens: int = 4096
    ) -> str:
        messages = [{"role": "user", "content": prompt}]
        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        response = await self.client.messages.create(**kwargs)
        return response.content[0].text
