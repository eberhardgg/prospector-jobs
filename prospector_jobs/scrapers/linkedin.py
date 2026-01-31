"""LinkedIn scraper via public job search (no login required)."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus, urlencode

import httpx
from bs4 import BeautifulSoup

from ..models import JobPosting
from .base import BaseScraper

logger = logging.getLogger(__name__)

# Multiple search queries to cast a wide net
SEARCH_QUERIES = [
    "chief product officer",
    "chief product and technology officer",
    "VP of Product",
    "Head of Product",
]

# LinkedIn public search base URL
BASE_URL = "https://www.linkedin.com/jobs/search/"


class LinkedInScraper(BaseScraper):
    """Scrape LinkedIn's public job search (no API key needed)."""

    name = "linkedin"

    def __init__(self, serpapi_key: str = "", delay: float = 3.0):
        super().__init__(delay=delay)
        self.serpapi_key = serpapi_key
        # LinkedIn needs these specific headers
        self._headers.update(
            {
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
                ),
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            }
        )

    async def scrape(self) -> list[JobPosting]:
        """Run all search queries and collect results."""
        postings: list[JobPosting] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for query in SEARCH_QUERIES:
                results = await self._search(client, query)
                postings.extend(results)

        return postings

    async def _search(self, client: httpx.AsyncClient, query: str) -> list[JobPosting]:
        """Search LinkedIn public jobs for a query."""
        params = {
            "keywords": query,
            "location": "United States",
            "f_TPR": "r604800",  # Past week
            "position": "1",
            "pageNum": "0",
        }
        url = f"{BASE_URL}?{urlencode(params)}"

        try:
            resp = await self._get(client, url)
            postings = self._parse_results(resp.text)
            logger.info("[linkedin] '%s' → %d results", query, len(postings))
            return postings
        except httpx.HTTPError as e:
            logger.error("[linkedin] Search failed for '%s': %s", query, e)
            return []

    def _parse_results(self, html: str) -> list[JobPosting]:
        """Parse LinkedIn public job search results."""
        soup = BeautifulSoup(html, "html.parser")
        postings: list[JobPosting] = []

        for card in soup.select("div.base-card"):
            title_el = card.select_one("h3.base-search-card__title, h3")
            company_el = card.select_one("h4.base-search-card__subtitle, h4 a")
            location_el = card.select_one("span.job-search-card__location")
            link_el = card.select_one("a.base-card__full-link, a[href*='/jobs/']")
            time_el = card.select_one("time")

            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            company = company_el.get_text(strip=True) if company_el else "Unknown"
            location = location_el.get_text(strip=True) if location_el else ""

            href = ""
            if link_el:
                raw = link_el.get("href", "")
                if isinstance(raw, str):
                    href = raw.split("?")[0]  # Clean tracking params

            posted_date = None
            if time_el:
                dt_str = time_el.get("datetime", "")
                if dt_str:
                    try:
                        posted_date = datetime.strptime(dt_str, "%Y-%m-%d").replace(
                            tzinfo=timezone.utc
                        )
                    except ValueError:
                        pass

            postings.append(
                JobPosting(
                    title=title,
                    company=company,
                    url=href,
                    source="linkedin",
                    location=location,
                    posted_date=posted_date,
                )
            )

        return postings

    # Keep backward-compat methods for tests
    @staticmethod
    def _extract_company(title: str) -> str:
        """Extract company name from 'Role at Company - LinkedIn' patterns."""
        patterns = [
            r"(?:at|@)\s+(.+?)(?:\s*[-|]|$)",
            r"[-|]\s*(.+?)\s*[-|]\s*LinkedIn",
        ]
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                company = match.group(1).strip()
                company = re.sub(r"\s*[-|]\s*LinkedIn.*$", "", company, flags=re.IGNORECASE)
                return company
        return "Unknown"

    @staticmethod
    def _clean_title(title: str) -> str:
        """Clean up a job title extracted from search results."""
        title = re.sub(r"\s*[-|].*LinkedIn.*$", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\s*[-|]\s*$", "", title)
        return title.strip()
