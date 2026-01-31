"""AboveBoard executive job board scraper."""

from __future__ import annotations

import logging

import httpx
from bs4 import BeautifulSoup

from ..models import JobPosting
from .base import BaseScraper

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.aboveboard.com/jobs"
SEARCH_PARAMS = {
    "q": "chief product officer",
    "function": "product",
}


class AboveboardScraper(BaseScraper):
    """Scrape AboveBoard for executive product roles."""

    name = "aboveboard"

    async def scrape(self) -> list[JobPosting]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await self._get(client, SEARCH_URL, params=SEARCH_PARAMS)
                return self._parse_results(resp.text)
            except httpx.HTTPError as e:
                logger.error("[aboveboard] Search failed: %s", e)
                return []

    def _parse_results(self, html: str) -> list[JobPosting]:
        """Parse AboveBoard job listing page."""
        soup = BeautifulSoup(html, "html.parser")
        postings: list[JobPosting] = []

        for card in soup.select("div.job-card, article.job-listing, div[data-job-id]"):
            title_el = card.select_one("h3, h2, a.job-title")
            company_el = card.select_one("span.company-name, div.company")
            location_el = card.select_one("span.location, div.location")
            link_el = card.select_one("a[href]")

            if not title_el:
                continue

            href = ""
            if link_el:
                raw_href = link_el.get("href", "")
                if isinstance(raw_href, str):
                    href = raw_href
                    if href.startswith("/"):
                        href = f"https://www.aboveboard.com{href}"

            postings.append(
                JobPosting(
                    title=title_el.get_text(strip=True),
                    company=company_el.get_text(strip=True) if company_el else "Unknown",
                    url=href,
                    source="aboveboard",
                    location=location_el.get_text(strip=True) if location_el else "",
                )
            )

        return postings
