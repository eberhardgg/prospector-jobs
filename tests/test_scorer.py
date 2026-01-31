"""Tests for scoring logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from prospector_jobs.models import JobPosting
from prospector_jobs.scorer import (
    score_description,
    score_freshness,
    score_posting,
    score_remote,
    score_title,
)


class TestScoreTitle:
    def test_cpo_gets_max(self):
        assert score_title("Chief Product Officer") == 40

    def test_cpto_gets_max(self):
        assert score_title("CPTO") == 40

    def test_vp_product(self):
        assert score_title("VP of Product") == 30

    def test_vice_president_product(self):
        assert score_title("Vice President of Product") == 30

    def test_head_of_product(self):
        assert score_title("Head of Product") == 28

    def test_svp_product(self):
        assert score_title("SVP of Product") == 32

    def test_director_product(self):
        assert score_title("Director of Product") == 15

    def test_product_manager_gets_zero(self):
        assert score_title("Product Manager") == 0

    def test_software_engineer_gets_zero(self):
        assert score_title("Senior Software Engineer") == 0

    def test_case_insensitive(self):
        assert score_title("chief product officer") == 40
        assert score_title("CHIEF PRODUCT OFFICER") == 40


class TestScoreDescription:
    def test_startup_signals(self):
        desc = "Join our Series B startup as we build the product team from scratch."
        score = score_description(desc)
        assert score > 0

    def test_fractional_boost(self):
        desc = "Looking for a fractional product leader."
        score = score_description(desc)
        assert score >= 10

    def test_interim_boost(self):
        desc = "Interim Chief Product Officer needed for 6-month engagement."
        score = score_description(desc)
        assert score >= 8

    def test_no_signals(self):
        desc = "We are a Fortune 500 company looking for a product manager."
        assert score_description(desc) == 0

    def test_multiple_signals_cap_at_30(self):
        desc = (
            "Fractional interim part-time contract role at early-stage Series A "
            "startup. Building the product team as first product hire."
        )
        assert score_description(desc) <= 30


class TestScoreRemote:
    def test_remote(self):
        assert score_remote("Remote position") == 5

    def test_hybrid(self):
        assert score_remote("Hybrid - NYC") == 2

    def test_distributed(self):
        assert score_remote("Distributed team") == 3

    def test_no_remote(self):
        assert score_remote("On-site in San Francisco") == 0

    def test_cap_at_10(self):
        text = "Remote work from anywhere, distributed hybrid team"
        assert score_remote(text) <= 10


class TestScoreFreshness:
    def test_today(self):
        now = datetime.now(UTC)
        assert score_freshness(now) == 10

    def test_three_days(self):
        date = datetime.now(UTC) - timedelta(days=2)
        assert score_freshness(date) == 8

    def test_one_week(self):
        date = datetime.now(UTC) - timedelta(days=5)
        assert score_freshness(date) == 6

    def test_two_weeks(self):
        date = datetime.now(UTC) - timedelta(days=10)
        assert score_freshness(date) == 4

    def test_one_month(self):
        date = datetime.now(UTC) - timedelta(days=20)
        assert score_freshness(date) == 2

    def test_old(self):
        date = datetime.now(UTC) - timedelta(days=60)
        assert score_freshness(date) == 0

    def test_no_date(self):
        assert score_freshness(None) == 3

    def test_naive_datetime(self):
        """Naive datetimes should still work (treated as UTC)."""
        date = datetime.now(UTC).replace(tzinfo=None)
        score = score_freshness(date)
        assert score == 10


class TestScorePosting:
    def test_cpo_remote_fresh(self, sample_cpo_posting):
        score = score_posting(sample_cpo_posting)
        # CPO title (40) + startup/series B signals + remote (5) + fresh (10) + base (10)
        assert score >= 65

    def test_vp_product(self, sample_vp_posting):
        score = score_posting(sample_vp_posting)
        # VP title (30) + growth-stage signal + fresh (10) + base (10)
        assert score >= 50

    def test_director_scores_lower(self, sample_director_posting):
        score = score_posting(sample_director_posting)
        # Director (15) + base (10) + freshness
        assert score < 50

    def test_score_capped_at_100(self):
        """Even with all signals, score shouldn't exceed 100."""
        posting = JobPosting(
            title="Chief Product Officer",
            company="Test",
            url="https://test.com",
            source="test",
            posted_date=datetime.now(UTC),
            location="Remote - Work from anywhere",
            description=(
                "Fractional interim part-time contract at early-stage Series A startup. "
                "First product hire, building the product team. Distributed remote."
            ),
        )
        score = score_posting(posting)
        assert score <= 100
