"""Configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration loaded from environment."""

    slack_webhook_url: str = field(default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL", ""))
    slack_channel_id: str = field(
        default_factory=lambda: os.getenv("SLACK_CHANNEL_ID", "C0AC2NEL32R")
    )
    slack_bot_token: str = field(default_factory=lambda: os.getenv("SLACK_BOT_TOKEN", ""))
    serpapi_key: str = field(default_factory=lambda: os.getenv("SERPAPI_KEY", ""))
    storage_path: Path = field(
        default_factory=lambda: Path(os.getenv("STORAGE_PATH", "./data/jobs.json"))
    )
    min_score: int = field(default_factory=lambda: int(os.getenv("MIN_SCORE", "40")))
    request_delay: float = field(default_factory=lambda: float(os.getenv("REQUEST_DELAY", "2.0")))

    # Scraper toggles
    scraper_linkedin: bool = field(
        default_factory=lambda: os.getenv("SCRAPER_LINKEDIN", "1") == "1"
    )
    scraper_indeed: bool = field(default_factory=lambda: os.getenv("SCRAPER_INDEED", "1") == "1")
    scraper_aboveboard: bool = field(
        default_factory=lambda: os.getenv("SCRAPER_ABOVEBOARD", "1") == "1"
    )
    scraper_wellfound: bool = field(
        default_factory=lambda: os.getenv("SCRAPER_WELLFOUND", "1") == "1"
    )

    @property
    def has_serpapi(self) -> bool:
        return bool(self.serpapi_key)

    @property
    def has_slack(self) -> bool:
        return bool(self.slack_webhook_url) or bool(self.slack_bot_token)


def get_config() -> Config:
    return Config()
