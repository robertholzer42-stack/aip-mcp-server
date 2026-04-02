"""Configuration for the AIP MCP server."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Resolve paths relative to the project root (one level up from src/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _resolve_path(env_key: str, default: str) -> Path:
    raw = os.getenv(env_key, default)
    p = Path(raw)
    if not p.is_absolute():
        p = _PROJECT_ROOT / p
    return p.resolve()


# --- Paths ---
SKILLS_DIR: Path = _resolve_path("AIP_SKILLS_DIR", "../applied-innovation-platform/skills")
ENGAGEMENTS_DIR: Path = _resolve_path("AIP_ENGAGEMENTS_DIR", "../applied-innovation-platform/engagements")

# --- LLM ---
AIP_MODEL: str | None = os.getenv("AIP_MODEL")
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
OLLAMA_BASE_URL: str | None = os.getenv("OLLAMA_BASE_URL")

# --- Server ---
HOST: str = os.getenv("AIP_HOST", "127.0.0.1")
PORT: int = int(os.getenv("AIP_PORT", "8100"))


def detect_model() -> str:
    """Return the model identifier to use, based on env configuration."""
    if AIP_MODEL:
        return AIP_MODEL
    if ANTHROPIC_API_KEY:
        return "claude-sonnet-4-20250514"
    if GOOGLE_API_KEY:
        return "gemini/gemini-2.0-flash"
    if OPENAI_API_KEY:
        return "gpt-4o"
    if OLLAMA_BASE_URL:
        return "ollama/llama3"
    return "claude-sonnet-4-20250514"  # default fallback
