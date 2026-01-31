"""Abstract base class for all job board scrapers."""

from __future__ import annotations

import asyncio
import logging
import random
from abc import ABC, abstractmethod

import httpx

from ..models import JobPosting

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base scraper with shared HTTP client management and rate limiting."""

    name: str = "base"

    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def _get(self, client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
        """Make a GET request with rate limiting and jitter."""
        jitter = random.uniform(0.5, 1.5)  # noqa: S311
        await asyncio.sleep(self.delay * jitter)

        logger.debug("[%s] GET %s", self.name, url)
        resp = await client.get(url, headers=self._headers, follow_redirects=True, **kwargs)
        resp.raise_for_status()
        return resp

    @abstractmethod
    async def scrape(self) -> list[JobPosting]:
        """Scrape job postings from this source. Must be implemented by subclasses."""
        ...

    async def safe_scrape(self) -> list[JobPosting]:
        """Scrape with error handling — never crashes the pipeline."""
        try:
            results = await self.scrape()
            logger.info("[%s] Found %d postings", self.name, len(results))
            return results
        except Exception:
            logger.exception("[%s] Scraper failed", self.name)
            return []
