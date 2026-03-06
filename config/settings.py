from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

from config.state_config import StateConfig

load_dotenv()


@dataclass(frozen=True)
class Config:
    # API Keys
    anthropic_api_key: str
    perplexity_api_key: str
    firecrawl_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str

    # State (fully driven by env vars via StateConfig)
    state_config: object

    # Claude
    claude_model: str
    claude_max_tokens: int

    # Scheduling
    report_hour: int
    report_minute: int
    timezone: str

    # Delivery pacing
    message_delay_seconds: int

    # Deduplication
    dedup_lookback_days: int
    dedup_history_file: str

    # Runtime
    log_level: str


def load_config() -> Config:
    """Load and validate all configuration from environment variables."""
    return Config(
        anthropic_api_key=_require("ANTHROPIC_API_KEY"),
        perplexity_api_key=_require("PERPLEXITY_API_KEY"),
        firecrawl_api_key=_require("FIRECRAWL_API_KEY"),
        telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_require("TELEGRAM_CHAT_ID"),
        state_config=StateConfig(),
        claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
        claude_max_tokens=int(os.getenv("CLAUDE_MAX_TOKENS", "8192")),
        report_hour=int(os.getenv("REPORT_HOUR", "8")),
        report_minute=int(os.getenv("REPORT_MINUTE", "0")),
        timezone=os.getenv("TIMEZONE", "America/New_York"),
        message_delay_seconds=int(os.getenv("MESSAGE_DELAY_SECONDS", "120")),
        dedup_lookback_days=int(os.getenv("DEDUP_LOOKBACK_DAYS", "7")),
        dedup_history_file=os.getenv("DEDUP_HISTORY_FILE", "data/seen_articles.json"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. Check your .env file."
        )
    return value
