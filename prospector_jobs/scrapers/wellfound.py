"""Wellfound (formerly AngelList) startup jobs scraper."""

from __future__ import annotations

import logging

import httpx
from bs4 import BeautifulSoup

from ..models import JobPosting
from .base import BaseScraper

logger = logging.getLogger(__name__)

SEARCH_URL = "https://wellfound.com/role/product-manager"


class WellfoundScraper(BaseScraper):
    """Scrape Wellfound for startup product leadership roles."""

    name = "wellfound"

    async def scrape(self) -> list[JobPosting]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await self._get(client, SEARCH_URL)
                return self._parse_results(resp.text)
            except httpx.HTTPError as e:
                logger.error("[wellfound] Search failed: %s", e)
                return []

    def _parse_results(self, html: str) -> list[JobPosting]:
        """Parse Wellfound job listing page."""
        soup = BeautifulSoup(html, "html.parser")
        postings: list[JobPosting] = []

        for card in soup.select(
            "div.styles_jobListing__title, div[data-test='StartupResult'], div.job-listing"
        ):
            title_el = card.select_one("a.job-title, h4, a[href*='/jobs/']")
            company_el = card.select_one("a.company-name, h2, a[href*='/company/']")
            location_el = card.select_one("span.location, div.text-neutral-400")
            link_el = card.select_one("a[href*='/jobs/']")

            if not title_el:
                continue

            title = title_el.get_text(strip=True)

            # Filter for senior product roles only
            title_lower = title.lower()
            if not any(
                kw in title_lower
                for kw in [
                    "chief product",
                    "cpto",
                    "vp product",
                    "vp of product",
                    "head of product",
                    "product leader",
                    "svp product",
                    "director product",
                ]
            ):
                continue

            href = ""
            if link_el:
                raw_href = link_el.get("href", "")
                if isinstance(raw_href, str):
                    href = raw_href
                    if href.startswith("/"):
                        href = f"https://wellfound.com{href}"

            postings.append(
                JobPosting(
                    title=title,
                    company=company_el.get_text(strip=True) if company_el else "Unknown",
                    url=href,
                    source="wellfound",
                    location=location_el.get_text(strip=True) if location_el else "",
                )
            )

        return postings
