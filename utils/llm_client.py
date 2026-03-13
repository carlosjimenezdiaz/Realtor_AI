from __future__ import annotations
from openai import OpenAI


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Map short model names → OpenRouter model IDs (anthropic/ prefix required)
_MODEL_MAP: dict[str, str] = {
    "claude-sonnet-4-6":         "anthropic/claude-sonnet-4-5",
    "claude-opus-4-6":           "anthropic/claude-opus-4-5",
    "claude-haiku-4-5-20251001": "anthropic/claude-haiku-4-5",
}


def make_client(api_key: str) -> OpenAI:
    """Returns an OpenAI client configured for OpenRouter."""
    return OpenAI(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        default_headers={
            "HTTP-Referer": "https://github.com/realtor-ai",
            "X-Title": "Realtor AI Newsletter",
        },
    )


def model_id(name: str) -> str:
    """Resolves a short model name to its OpenRouter ID."""
    return _MODEL_MAP.get(name, f"anthropic/{name}")
