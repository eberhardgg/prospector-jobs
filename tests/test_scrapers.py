"""Tests for scrapers using mocked HTTP responses."""

from __future__ import annotations

import httpx
import pytest
import respx

from prospector_jobs.scrapers.aboveboard import AboveboardScraper
from prospector_jobs.scrapers.indeed import IndeedScraper
from prospector_jobs.scrapers.linkedin import LinkedInScraper
from prospector_jobs.scrapers.wellfound import WellfoundScraper


LINKEDIN_SEARCH_HTML = """
<html><body>
<div class="base-card">
    <h3 class="base-search-card__title">Chief Product Officer</h3>
    <h4 class="base-search-card__subtitle"><a>Acme Corp</a></h4>
    <span class="job-search-card__location">Remote</span>
    <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/cpo-at-acme-123">View</a>
    <time datetime="2026-01-30">1 day ago</time>
</div>
<div class="base-card">
    <h3 class="base-search-card__title">VP of Product</h3>
    <h4 class="base-search-card__subtitle"><a>TechStart Inc</a></h4>
    <span class="job-search-card__location">San Francisco, CA</span>
    <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/vp-product-techstart-456">View</a>
    <time datetime="2026-01-28">3 days ago</time>
</div>
</body></html>
"""


class TestLinkedInScraper:
    def test_parse_results(self):
        scraper = LinkedInScraper(delay=0)
        results = scraper._parse_results(LINKEDIN_SEARCH_HTML)
        assert len(results) == 2

        assert results[0].title == "Chief Product Officer"
        assert results[0].company == "Acme Corp"
        assert results[0].source == "linkedin"
        assert "linkedin.com" in results[0].url
        assert results[0].posted_date is not None

        assert results[1].title == "VP of Product"
        assert results[1].company == "TechStart Inc"

    def test_extract_company(self):
        assert LinkedInScraper._extract_company("CPO at Acme Corp - LinkedIn") == "Acme Corp"
        assert LinkedInScraper._extract_company("VP Product at TechStart - LinkedIn") == "TechStart"

    def test_clean_title(self):
        assert (
            LinkedInScraper._clean_title("Chief Product Officer at Acme - LinkedIn")
            == "Chief Product Officer at Acme"
        )
        assert LinkedInScraper._clean_title("VP Product | LinkedIn") == "VP Product"

    @respx.mock
    @pytest.mark.asyncio
    async def test_scrape(self):
        respx.get("https://www.linkedin.com/jobs/search/").mock(
            return_value=httpx.Response(200, text=LINKEDIN_SEARCH_HTML)
        )
        scraper = LinkedInScraper(delay=0)
        results = await scraper.scrape()
        assert len(results) > 0
        for r in results:
            assert r.source == "linkedin"

    @respx.mock
    @pytest.mark.asyncio
    async def test_handles_http_error(self):
        respx.get("https://www.linkedin.com/jobs/search/").mock(
            return_value=httpx.Response(429, text="Rate limited")
        )
        scraper = LinkedInScraper(delay=0)
        results = await scraper.safe_scrape()
        assert results == []


class TestIndeedScraper:
    def test_parse_results(self, indeed_search_html):
        scraper = IndeedScraper(delay=0)
        results = scraper._parse_results(indeed_search_html)
        assert len(results) == 2

        assert results[0].title == "Chief Product Officer"
        assert results[0].company == "StartupCo"
        assert results[0].source == "indeed"
        assert results[0].location == "Remote"
        assert results[0].url.startswith("https://www.indeed.com/")

        assert results[1].title == "VP of Product"
        assert results[1].company == "GrowthCorp"

    @respx.mock
    @pytest.mark.asyncio
    async def test_scrape(self, indeed_search_html):
        respx.get("https://www.indeed.com/jobs").mock(
            return_value=httpx.Response(200, text=indeed_search_html)
        )
        scraper = IndeedScraper(delay=0)
        results = await scraper.scrape()
        assert len(results) > 0

    @respx.mock
    @pytest.mark.asyncio
    async def test_handles_error(self):
        respx.get("https://www.indeed.com/jobs").mock(
            return_value=httpx.Response(503, text="Service Unavailable")
        )
        scraper = IndeedScraper(delay=0)
        results = await scraper.safe_scrape()
        assert results == []


class TestAboveboardScraper:
    def test_parse_results(self, aboveboard_search_html):
        scraper = AboveboardScraper(delay=0)
        results = scraper._parse_results(aboveboard_search_html)
        assert len(results) == 1
        assert results[0].title == "Chief Product Officer"
        assert results[0].company == "Enterprise Inc"
        assert results[0].source == "aboveboard"

    @respx.mock
    @pytest.mark.asyncio
    async def test_scrape(self, aboveboard_search_html):
        respx.get("https://trueplatform.com/search/").mock(
            return_value=httpx.Response(200, text=aboveboard_search_html)
        )
        scraper = AboveboardScraper(delay=0)
        results = await scraper.scrape()
        assert len(results) == 1


class TestWellfoundScraper:
    def test_parse_results(self, wellfound_search_html):
        scraper = WellfoundScraper(delay=0)
        results = scraper._parse_results(wellfound_search_html)
        # "Product Manager" should be filtered out
        assert len(results) == 1
        assert results[0].title == "Head of Product"
        assert results[0].company == "AI Start"
        assert results[0].source == "wellfound"

    @respx.mock
    @pytest.mark.asyncio
    async def test_scrape(self, wellfound_search_html):
        respx.get("https://wellfound.com/role/product-manager").mock(
            return_value=httpx.Response(200, text=wellfound_search_html)
        )
        scraper = WellfoundScraper(delay=0)
        results = await scraper.scrape()
        assert len(results) == 1
