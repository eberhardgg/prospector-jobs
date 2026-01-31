"""Persistent storage for job postings (JSON-based)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import JobPosting

logger = logging.getLogger(__name__)


def load_postings(path: Path) -> list[JobPosting]:
    """Load existing postings from JSON file."""
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text())
        return [JobPosting.from_dict(d) for d in data]
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Failed to load postings from %s: %s", path, e)
        return []


def save_postings(postings: list[JobPosting], path: Path) -> None:
    """Save postings to JSON file, creating directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [p.to_dict() for p in postings]
    path.write_text(json.dumps(data, indent=2, default=str))
    logger.info("Saved %d postings to %s", len(postings), path)


def append_postings(new_postings: list[JobPosting], path: Path) -> list[JobPosting]:
    """Append new postings to existing storage, avoiding duplicates.

    Returns the full list of all postings.
    """
    existing = load_postings(path)
    existing_keys = {p.dedup_key for p in existing}

    added = 0
    for posting in new_postings:
        if posting.dedup_key not in existing_keys:
            existing.append(posting)
            existing_keys.add(posting.dedup_key)
            added += 1

    if added > 0:
        save_postings(existing, path)
        logger.info("Added %d new postings (total: %d)", added, len(existing))
    else:
        logger.info("No new postings to add")

    return existing
