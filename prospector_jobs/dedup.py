"""Deduplication logic for job postings."""

from __future__ import annotations

from .models import JobPosting


def deduplicate(postings: list[JobPosting]) -> list[JobPosting]:
    """Remove duplicate postings by company+title combo.

    When duplicates are found, keeps the one with the highest score.
    If scores are equal, keeps the first one encountered.
    """
    seen: dict[str, JobPosting] = {}

    for posting in postings:
        key = posting.dedup_key
        if key not in seen or posting.score > seen[key].score:
            seen[key] = posting

    return list(seen.values())
