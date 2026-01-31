"""LinkedIn scraper via Google dorking or SerpAPI."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from ..models import JobPosting
from .base import BaseScraper

logger = logging.getLogger(__name__)

SEARCH_QUERIES = [
    'site:linkedin.com/jobs "chief product officer"',
    'site:linkedin.com/jobs "CPTO"',
    'site:linkedin.com/jobs "VP of Product"',
    'site:linkedin.com/jobs "Head of Product"',
]


class LinkedInScraper(BaseScraper):
    """Scrape LinkedIn job postings via Google search results."""

    name = "linkedin"

    def __init__(self, serpapi_key: str = "", delay: float = 3.0):
        super().__init__(delay=delay)
        self.serpapi_key = serpapi_key

    async def scrape(self) -> list[JobPosting]:
        """Run all search queries and collect results."""
        postings: list[JobPosting] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for query in SEARCH_QUERIES:
                if self.serpapi_key:
                    results = await self._search_serpapi(client, query)
                else:
                    results = await self._search_google(client, query)
                postings.extend(results)

        return postings

    async def _search_serpapi(self, client: httpx.AsyncClient, query: str) -> list[JobPosting]:
        """Search using SerpAPI (higher quality, requires API key)."""
        url = "https://serpapi.com/search.json"
        params = {
            "q": query,
            "api_key": self.serpapi_key,
            "num": 20,
        }

        try:
            resp = await self._get(client, url, params=params)
            data = resp.json()
            results = data.get("organic_results", [])
            return [self._parse_serpapi_result(r) for r in results if self._is_linkedin_job(r)]
        except httpx.HTTPError as e:
            logger.error("[linkedin/serpapi] Search failed: %s", e)
            return []

    async def _search_google(self, client: httpx.AsyncClient, query: str) -> list[JobPosting]:
        """Search Google directly (no API key needed, but may be rate-limited)."""
        encoded = quote_plus(query)
        url = f"https://www.google.com/search?q={encoded}&num=20"

        try:
            resp = await self._get(client, url)
            return self._parse_google_results(resp.text)
        except httpx.HTTPError as e:
            logger.error("[linkedin/google] Search failed: %s", e)
            return []

    def _parse_google_results(self, html: str) -> list[JobPosting]:
        """Parse Google search results HTML for LinkedIn job links."""
        soup = BeautifulSoup(html, "html.parser")
        postings: list[JobPosting] = []

        for result in soup.select("div.g"):
            link_el = result.select_one("a[href]")
            title_el = result.select_one("h3")
            snippet_el = result.select_one("div.VwiC3b") or result.select_one("span.st")

            if not link_el or not title_el:
                continue

            url = link_el.get("href", "")
            if not isinstance(url, str) or "linkedin.com/jobs" not in url:
                continue

            title = title_el.get_text(strip=True)
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""

            # Try to extract company from title pattern "Role at Company"
            company = self._extract_company(title)

            postings.append(
                JobPosting(
                    title=self._clean_title(title),
                    company=company,
                    url=url,
                    source="linkedin",
                    description=snippet,
                )
            )

        return postings

    def _parse_serpapi_result(self, result: dict) -> JobPosting:
        """Parse a single SerpAPI organic result."""
        title = result.get("title", "")
        return JobPosting(
            title=self._clean_title(title),
            company=self._extract_company(title),
            url=result.get("link", ""),
            source="linkedin",
            description=result.get("snippet", ""),
        )

    @staticmethod
    def _is_linkedin_job(result: dict) -> bool:
        link = result.get("link", "")
        return "linkedin.com/jobs" in link

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
