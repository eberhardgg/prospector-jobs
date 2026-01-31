"""Tests for data models."""

from __future__ import annotations

from prospector_jobs.models import JobPosting


class TestJobPosting:
    def test_dedup_key_normalizes(self):
        posting = JobPosting(
            title="  Chief Product Officer  ",
            company="  Acme Corp  ",
            url="https://example.com",
            source="test",
        )
        assert posting.dedup_key == "acme corp|chief product officer"

    def test_dedup_key_case_insensitive(self):
        p1 = JobPosting(title="CPO", company="ACME", url="", source="a")
        p2 = JobPosting(title="cpo", company="acme", url="", source="b")
        assert p1.dedup_key == p2.dedup_key

    def test_to_dict(self, sample_cpo_posting):
        d = sample_cpo_posting.to_dict()
        assert d["title"] == "Chief Product Officer"
        assert d["company"] == "Acme Corp"
        assert d["source"] == "linkedin"
        assert d["posted_date"] is not None

    def test_from_dict_roundtrip(self, sample_cpo_posting):
        d = sample_cpo_posting.to_dict()
        restored = JobPosting.from_dict(d)
        assert restored.title == sample_cpo_posting.title
        assert restored.company == sample_cpo_posting.company
        assert restored.url == sample_cpo_posting.url
        assert restored.source == sample_cpo_posting.source

    def test_from_dict_no_date(self):
        d = {
            "title": "CPO",
            "company": "Test",
            "url": "https://test.com",
            "source": "test",
        }
        posting = JobPosting.from_dict(d)
        assert posting.posted_date is None
        assert posting.location == ""
        assert posting.score == 0

    def test_from_dict_with_date(self):
        d = {
            "title": "CPO",
            "company": "Test",
            "url": "https://test.com",
            "source": "test",
            "posted_date": "2024-01-15T10:30:00+00:00",
        }
        posting = JobPosting.from_dict(d)
        assert posting.posted_date is not None
        assert posting.posted_date.year == 2024
