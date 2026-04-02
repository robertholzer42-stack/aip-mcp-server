"""Router that auto-detects the available LLM and exposes a singleton provider."""
from __future__ import annotations

from aip.config import ANTHROPIC_API_KEY, detect_model
from aip.llm.base import LLMProvider
from aip.llm.claude import ClaudeProvider
from aip.llm.openai_compat import LiteLLMProvider

_provider: LLMProvider | None = None


def get_provider() -> LLMProvider:
    """Get or create the LLM provider based on environment config."""
    global _provider
    if _provider is None:
        model = detect_model()
        if model.startswith("claude") and ANTHROPIC_API_KEY:
            _provider = ClaudeProvider(model=model)
        else:
            _provider = LiteLLMProvider(model=model)
    return _provider


async def complete(
    prompt: str, system: str | None = None, max_tokens: int = 4096
) -> str:
    """Convenience function for direct completion."""
    provider = get_provider()
    return await provider.complete(prompt, system=system, max_tokens=max_tokens)


def get_active_model() -> str:
    return get_provider().get_model_name()
