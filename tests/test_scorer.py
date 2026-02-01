"""Tests for scoring logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from prospector_jobs.models import JobPosting
from prospector_jobs.scorer import (
    score_company,
    score_freshness,
    score_posting,
    score_remote,
    score_title,
)


class TestScoreTitle:
    def test_cpo_gets_max(self):
        assert score_title("Chief Product Officer") == 50

    def test_cpto_gets_max(self):
        assert score_title("CPTO") == 50

    def test_vp_product(self):
        assert score_title("VP of Product") == 25

    def test_vice_president_product(self):
        assert score_title("Vice President of Product") == 25

    def test_head_of_product(self):
        assert score_title("Head of Product") == 22

    def test_svp_product(self):
        assert score_title("SVP of Product") == 28

    def test_director_product(self):
        assert score_title("Director of Product") == 8

    def test_product_manager_gets_zero(self):
        assert score_title("Product Manager") == 0

    def test_software_engineer_gets_zero(self):
        assert score_title("Senior Software Engineer") == 0

    def test_case_insensitive(self):
        assert score_title("chief product officer") == 50
        assert score_title("CHIEF PRODUCT OFFICER") == 50


class TestScoreCompany:
    def test_fortune_500_penalized(self):
        score = score_company("JPMorganChase", "VP Product", "")
        assert score == -30

    def test_recruiter_penalized(self):
        score = score_company("Lensa", "VP Product", "")
        assert score == -20

    def test_staffing_firm_penalized(self):
        score = score_company("The Brydon Group", "CPO", "")
        assert score == -20

    def test_startup_boosted(self):
        score = score_company("Acme Corp", "CPO", "Series B startup building SaaS platform")
        assert score > 0

    def test_unknown_company_neutral(self):
        score = score_company("RandomCo", "CPO", "")
        assert score == 0

    def test_fractional_big_boost(self):
        score = score_company("Acme", "CPO", "Looking for a fractional CPO")
        assert score >= 15

    def test_first_hire_big_boost(self):
        score = score_company("Acme", "CPO", "This is our first product hire")
        assert score >= 15

    def test_vc_backed(self):
        score = score_company("Acme", "CPO", "Join our venture-backed startup")
        assert score > 0


class TestScoreRemote:
    def test_remote(self):
        assert score_remote("Remote position") == 8

    def test_hybrid(self):
        assert score_remote("Hybrid - NYC") == 3

    def test_distributed(self):
        assert score_remote("Distributed team") == 5

    def test_no_remote(self):
        assert score_remote("On-site in San Francisco") == 0

    def test_cap_at_10(self):
        text = "Remote work from anywhere, distributed hybrid team"
        assert score_remote(text) <= 10


class TestScoreFreshness:
    def test_today(self):
        now = datetime.now(UTC)
        assert score_freshness(now) == 15

    def test_three_days(self):
        date = datetime.now(UTC) - timedelta(days=2)
        assert score_freshness(date) == 12

    def test_one_week(self):
        date = datetime.now(UTC) - timedelta(days=5)
        assert score_freshness(date) == 8

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
        assert score_freshness(None) == 5

    def test_naive_datetime(self):
        """Naive datetimes should still work (treated as UTC)."""
        date = datetime.now(UTC).replace(tzinfo=None)
        score = score_freshness(date)
        assert score == 15


class TestScorePosting:
    def test_cpo_startup_fresh(self, sample_cpo_posting):
        """CPO at a startup should score high."""
        score = score_posting(sample_cpo_posting)
        # CPO (40) + startup signals (series B, first CPO, build org) + remote (8) + fresh (15) + base (10)
        assert score >= 70

    def test_vp_product_growth(self, sample_vp_posting):
        """VP Product at growth-stage should be decent."""
        score = score_posting(sample_vp_posting)
        assert score >= 40

    def test_director_scores_lower(self, sample_director_posting):
        """Director should score well below CPO."""
        score = score_posting(sample_director_posting)
        assert score < 40

    def test_fortune_500_crushed(self):
        """JPMorgan VP Product should be near zero."""
        posting = JobPosting(
            title="Vice President, Product Management",
            company="JPMorganChase",
            url="https://linkedin.com/jobs/999",
            source="linkedin",
            posted_date=datetime.now(UTC),
            location="New York, NY",
        )
        score = score_posting(posting)
        assert score <= 25

    def test_recruiter_posting_penalized(self):
        """Lensa aggregator posting should score low."""
        posting = JobPosting(
            title="VP, Product Management",
            company="Lensa",
            url="https://linkedin.com/jobs/888",
            source="linkedin",
            posted_date=datetime.now(UTC),
        )
        score = score_posting(posting)
        assert score <= 30

    def test_cpo_beats_vp(self, sample_cpo_posting, sample_vp_posting):
        """CPO title should always outscore VP."""
        cpo_score = score_posting(sample_cpo_posting)
        vp_score = score_posting(sample_vp_posting)
        assert cpo_score > vp_score

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
                "First product hire, building the product team. Distributed remote. "
                "VC-backed SaaS B2B fintech company."
            ),
        )
        score = score_posting(posting)
        assert score <= 100

    def test_score_never_negative(self):
        """Even worst case, score should be 0 not negative."""
        posting = JobPosting(
            title="Director of Product",
            company="JPMorganChase",
            url="https://test.com",
            source="linkedin",
            posted_date=datetime.now(UTC) - timedelta(days=60),
        )
        score = score_posting(posting)
        assert score >= 0
