"""Shared test fixtures for prospector-jobs tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from prospector_jobs.models import JobPosting


@pytest.fixture
def sample_cpo_posting() -> JobPosting:
    return JobPosting(
        title="Chief Product Officer",
        company="Acme Corp",
        url="https://linkedin.com/jobs/123",
        source="linkedin",
        posted_date=datetime.now(UTC),
        location="Remote",
        description="Join our Series B startup as our first CPO. Build the product org from scratch.",
        score=0,
    )


@pytest.fixture
def sample_vp_posting() -> JobPosting:
    return JobPosting(
        title="VP of Product",
        company="TechStart Inc",
        url="https://indeed.com/jobs/456",
        source="indeed",
        posted_date=datetime.now(UTC),
        location="San Francisco, CA",
        description="Lead product strategy for our growth-stage SaaS platform.",
        score=0,
    )


@pytest.fixture
def sample_head_posting() -> JobPosting:
    return JobPosting(
        title="Head of Product",
        company="DataFlow",
        url="https://wellfound.com/jobs/789",
        source="wellfound",
        location="New York, NY (Hybrid)",
        description="Early-stage AI startup looking for a product leader.",
        score=0,
    )


@pytest.fixture
def sample_director_posting() -> JobPosting:
    return JobPosting(
        title="Director of Product Management",
        company="BigCorp",
        url="https://indeed.com/jobs/101",
        source="indeed",
        location="Chicago, IL",
        description="Manage a team of 10 PMs in our enterprise division.",
        score=0,
    )


@pytest.fixture
def sample_postings(
    sample_cpo_posting, sample_vp_posting, sample_head_posting, sample_director_posting
) -> list[JobPosting]:
    return [sample_cpo_posting, sample_vp_posting, sample_head_posting, sample_director_posting]


@pytest.fixture
def google_search_html() -> str:
    """Mock Google search results HTML."""
    return """
    <html><body>
    <div class="g">
        <a href="https://www.linkedin.com/jobs/view/chief-product-officer-at-acme-123">
            <h3>Chief Product Officer at Acme Corp - LinkedIn</h3>
        </a>
        <div class="VwiC3b">Join our team as CPO. Series B startup building the future.</div>
    </div>
    <div class="g">
        <a href="https://www.linkedin.com/jobs/view/cpto-at-techstart-456">
            <h3>CPTO at TechStart - LinkedIn</h3>
        </a>
        <div class="VwiC3b">Chief Product & Technology Officer role at early-stage startup.</div>
    </div>
    <div class="g">
        <a href="https://www.example.com/not-linkedin">
            <h3>Some Other Page</h3>
        </a>
        <div class="VwiC3b">This is not a LinkedIn job posting.</div>
    </div>
    </body></html>
    """


@pytest.fixture
def indeed_search_html() -> str:
    """Mock Indeed search results HTML."""
    return """
    <html><body>
    <div class="job_seen_beacon">
        <h2 class="jobTitle"><a class="jcs-JobTitle" href="/viewjob?jk=abc123">Chief Product Officer</a></h2>
        <span data-testid="company-name">StartupCo</span>
        <div data-testid="text-location">Remote</div>
        <div class="job-snippet">Build and lead the product organization at our Series A company.</div>
    </div>
    <div class="job_seen_beacon">
        <h2 class="jobTitle"><a class="jcs-JobTitle" href="/viewjob?jk=def456">VP of Product</a></h2>
        <span data-testid="company-name">GrowthCorp</span>
        <div data-testid="text-location">San Francisco, CA</div>
        <div class="job-snippet">Lead product strategy for our scale-up platform.</div>
    </div>
    </body></html>
    """


@pytest.fixture
def aboveboard_search_html() -> str:
    """Mock AboveBoard search results HTML."""
    return """
    <html><body>
    <div class="job-card">
        <h3>Chief Product Officer</h3>
        <span class="company-name">Enterprise Inc</span>
        <span class="location">New York, NY</span>
        <a href="/jobs/cpo-enterprise-123">View Job</a>
    </div>
    </body></html>
    """


@pytest.fixture
def wellfound_search_html() -> str:
    """Mock Wellfound search results HTML."""
    return """
    <html><body>
    <div class="job-listing">
        <a class="job-title" href="/jobs/head-of-product-at-aistart">Head of Product</a>
        <a class="company-name" href="/company/aistart">AI Start</a>
        <span class="location">Remote (US)</span>
    </div>
    <div class="job-listing">
        <a class="job-title" href="/jobs/pm-at-randomco">Product Manager</a>
        <a class="company-name" href="/company/randomco">RandomCo</a>
        <span class="location">Austin, TX</span>
    </div>
    </body></html>
    """
