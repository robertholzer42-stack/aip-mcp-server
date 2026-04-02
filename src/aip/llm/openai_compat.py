"""LiteLLM adapter for Gemini, GPT-4, Ollama, and other OpenAI-compatible models."""
from __future__ import annotations

import litellm

from aip.llm.base import LLMProvider


class LiteLLMProvider(LLMProvider):
    def __init__(self, model: str):
        self.model = model

    async def complete(
        self, prompt: str, system: str | None = None, max_tokens: int = 4096
    ) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = await litellm.acompletion(
            model=self.model, messages=messages, max_tokens=max_tokens
        )
        return response.choices[0].message.content
