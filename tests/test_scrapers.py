"""Tests for scrapers using mocked HTTP responses."""

from __future__ import annotations

import httpx
import pytest
import respx

from prospector_jobs.scrapers.aboveboard import AboveboardScraper
from prospector_jobs.scrapers.indeed import IndeedScraper
from prospector_jobs.scrapers.linkedin import LinkedInScraper
from prospector_jobs.scrapers.wellfound import WellfoundScraper


class TestLinkedInScraper:
    def test_parse_google_results(self, google_search_html):
        scraper = LinkedInScraper(delay=0)
        results = scraper._parse_google_results(google_search_html)
        assert len(results) == 2  # 3rd result is not LinkedIn

        assert results[0].source == "linkedin"
        assert "Acme" in results[0].company or "acme" in results[0].title.lower()
        assert "linkedin.com" in results[0].url

    def test_extract_company(self):
        scraper = LinkedInScraper(delay=0)
        assert scraper._extract_company("CPO at Acme Corp - LinkedIn") == "Acme Corp"
        assert scraper._extract_company("VP Product at TechStart - LinkedIn") == "TechStart"

    def test_clean_title(self):
        scraper = LinkedInScraper(delay=0)
        assert (
            scraper._clean_title("Chief Product Officer at Acme - LinkedIn")
            == "Chief Product Officer at Acme"
        )
        assert scraper._clean_title("VP Product | LinkedIn") == "VP Product"

    @respx.mock
    @pytest.mark.asyncio
    async def test_scrape_google(self, google_search_html):
        respx.get("https://www.google.com/search").mock(
            return_value=httpx.Response(200, text=google_search_html)
        )
        scraper = LinkedInScraper(delay=0)
        results = await scraper.scrape()
        assert len(results) > 0
        for r in results:
            assert r.source == "linkedin"

    @respx.mock
    @pytest.mark.asyncio
    async def test_scrape_serpapi(self):
        serpapi_response = {
            "organic_results": [
                {
                    "title": "Chief Product Officer at TestCo - LinkedIn",
                    "link": "https://www.linkedin.com/jobs/view/123",
                    "snippet": "Join TestCo as CPO",
                },
                {
                    "title": "Random Page",
                    "link": "https://example.com/not-linkedin",
                    "snippet": "Not a job",
                },
            ]
        }
        respx.get("https://serpapi.com/search.json").mock(
            return_value=httpx.Response(200, json=serpapi_response)
        )
        scraper = LinkedInScraper(serpapi_key="test-key", delay=0)
        results = await scraper.scrape()
        # Only LinkedIn jobs should be returned
        assert len(results) >= 1
        assert all("linkedin.com" in r.url for r in results)

    @respx.mock
    @pytest.mark.asyncio
    async def test_handles_http_error(self):
        respx.get("https://www.google.com/search").mock(
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
        assert "aboveboard.com" in results[0].url

    @respx.mock
    @pytest.mark.asyncio
    async def test_scrape(self, aboveboard_search_html):
        respx.get("https://www.aboveboard.com/jobs").mock(
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
