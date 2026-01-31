"""Indeed job board scraper.

Note: Indeed aggressively blocks non-browser requests (403).
This scraper requires SerpAPI or Playwright to work reliably.
Without those, it will log a warning and return empty results.
"""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from ..models import JobPosting
from .base import BaseScraper

logger = logging.getLogger(__name__)

SEARCH_TERMS = [
    "chief product officer",
    "CPTO",
    "VP of Product",
    "Head of Product",
]


class IndeedScraper(BaseScraper):
    """Scrape Indeed for product leadership roles."""

    name = "indeed"

    async def scrape(self) -> list[JobPosting]:
        postings: list[JobPosting] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for term in SEARCH_TERMS:
                results = await self._search(client, term)
                postings.extend(results)

        return postings

    async def _search(self, client: httpx.AsyncClient, term: str) -> list[JobPosting]:
        """Search Indeed for a specific term."""
        encoded = quote_plus(term)
        url = f"https://www.indeed.com/jobs?q={encoded}&sort=date&fromage=14"

        try:
            resp = await self._get(client, url)
            return self._parse_results(resp.text)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.debug("[indeed] Blocked (403) — Indeed requires browser/SerpAPI")
            else:
                logger.error("[indeed] Search failed for '%s': %s", term, e)
            return []
        except httpx.HTTPError as e:
            logger.error("[indeed] Search failed for '%s': %s", term, e)
            return []

    def _parse_results(self, html: str) -> list[JobPosting]:
        """Parse Indeed search results page."""
        soup = BeautifulSoup(html, "html.parser")
        postings: list[JobPosting] = []

        for card in soup.select("div.job_seen_beacon, div.jobsearch-ResultsList > div"):
            title_el = card.select_one("h2.jobTitle a, a.jcs-JobTitle")
            company_el = card.select_one("span[data-testid='company-name'], span.companyName")
            location_el = card.select_one("div[data-testid='text-location'], div.companyLocation")
            snippet_el = card.select_one("div.job-snippet, td.snip")

            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            if isinstance(href, str) and href.startswith("/"):
                href = f"https://www.indeed.com{href}"

            postings.append(
                JobPosting(
                    title=title,
                    company=company_el.get_text(strip=True) if company_el else "Unknown",
                    url=href if isinstance(href, str) else "",
                    source="indeed",
                    location=location_el.get_text(strip=True) if location_el else "",
                    description=snippet_el.get_text(strip=True) if snippet_el else "",
                )
            )

        return postings
