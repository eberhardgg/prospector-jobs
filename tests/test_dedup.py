"""Tests for deduplication logic."""

from __future__ import annotations

from prospector_jobs.dedup import deduplicate
from prospector_jobs.models import JobPosting


class TestDeduplicate:
    def test_no_duplicates(self, sample_postings):
        result = deduplicate(sample_postings)
        assert len(result) == len(sample_postings)

    def test_exact_duplicates(self):
        p1 = JobPosting(title="CPO", company="Acme", url="url1", source="linkedin", score=80)
        p2 = JobPosting(title="CPO", company="Acme", url="url2", source="indeed", score=60)
        result = deduplicate([p1, p2])
        assert len(result) == 1
        assert result[0].score == 80  # Keeps higher score

    def test_case_insensitive_dedup(self):
        p1 = JobPosting(
            title="Chief Product Officer", company="ACME", url="url1", source="a", score=70
        )
        p2 = JobPosting(
            title="chief product officer", company="acme", url="url2", source="b", score=50
        )
        result = deduplicate([p1, p2])
        assert len(result) == 1

    def test_keeps_higher_score(self):
        p1 = JobPosting(title="CPO", company="Test", url="url1", source="a", score=30)
        p2 = JobPosting(title="CPO", company="Test", url="url2", source="b", score=90)
        result = deduplicate([p1, p2])
        assert len(result) == 1
        assert result[0].score == 90
        assert result[0].url == "url2"

    def test_different_titles_not_deduped(self):
        p1 = JobPosting(title="CPO", company="Acme", url="url1", source="a", score=80)
        p2 = JobPosting(title="VP Product", company="Acme", url="url2", source="a", score=70)
        result = deduplicate([p1, p2])
        assert len(result) == 2

    def test_empty_list(self):
        assert deduplicate([]) == []

    def test_whitespace_normalized(self):
        p1 = JobPosting(title="  CPO  ", company=" Acme ", url="url1", source="a", score=80)
        p2 = JobPosting(title="CPO", company="Acme", url="url2", source="b", score=60)
        result = deduplicate([p1, p2])
        assert len(result) == 1
