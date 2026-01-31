"""Score job postings based on relevance for fractional CPO prospecting."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from .models import JobPosting

# Title patterns with weights (higher = more relevant)
TITLE_PATTERNS: list[tuple[str, int]] = [
    (r"\bchief product officer\b", 40),
    (r"\bcpto\b", 40),
    (r"\bchief product (?:&|and) technology officer\b", 38),
    (r"\bvp[,.]? (?:of )?product\b", 30),
    (r"\bvice president[,.]? (?:of )?product\b", 30),
    (r"\bhead of product\b", 28),
    (r"\bsvp[,.]? (?:of )?product\b", 32),
    (r"\bdirector[,.]? (?:of )?product\b", 15),
    (r"\bproduct leader\b", 20),
]

# Description signals that boost score
DESCRIPTION_SIGNALS: list[tuple[str, int]] = [
    (r"\bfractional\b", 10),
    (r"\binterim\b", 8),
    (r"\bpart[- ]time\b", 5),
    (r"\bcontract\b", 5),
    (r"\bseries [a-c]\b", 6),
    (r"\bstartup\b", 5),
    (r"\bearly[- ]stage\b", 6),
    (r"\bgrowth[- ]stage\b", 4),
    (r"\bscale[- ]up\b", 4),
    (r"\bfirst product hire\b", 8),
    (r"\bbuild(?:ing)? (?:the |a )?product (?:team|org|function)\b", 7),
]

# Remote-friendly signals
REMOTE_SIGNALS: list[tuple[str, int]] = [
    (r"\bremote\b", 5),
    (r"\bhybrid\b", 2),
    (r"\bwork from anywhere\b", 5),
    (r"\bdistributed\b", 3),
]

# Max age bonus (fresher = better)
MAX_FRESHNESS_BONUS = 10


def score_title(title: str) -> int:
    """Score based on job title match. Returns 0-40."""
    title_lower = title.lower()
    best = 0
    for pattern, weight in TITLE_PATTERNS:
        if re.search(pattern, title_lower):
            best = max(best, weight)
    return best


def score_description(description: str) -> int:
    """Score based on description signals. Returns 0-30."""
    desc_lower = description.lower()
    total = 0
    for pattern, weight in DESCRIPTION_SIGNALS:
        if re.search(pattern, desc_lower):
            total += weight
    return min(total, 30)


def score_remote(text: str) -> int:
    """Score remote-friendliness from title + location + description. Returns 0-10."""
    text_lower = text.lower()
    total = 0
    for pattern, weight in REMOTE_SIGNALS:
        if re.search(pattern, text_lower):
            total += weight
    return min(total, 10)


def score_freshness(posted_date: datetime | None) -> int:
    """Score based on how recent the posting is. Returns 0-10."""
    if not posted_date:
        return 3  # Unknown date gets a small default

    now = datetime.now(UTC)
    if posted_date.tzinfo is None:
        posted_date = posted_date.replace(tzinfo=UTC)

    age_days = (now - posted_date).days

    if age_days <= 1:
        return 10
    elif age_days <= 3:
        return 8
    elif age_days <= 7:
        return 6
    elif age_days <= 14:
        return 4
    elif age_days <= 30:
        return 2
    else:
        return 0


def score_posting(posting: JobPosting) -> int:
    """Score a job posting on a 0-100 scale.

    Breakdown:
    - Title match: 0-40 points
    - Description signals: 0-30 points
    - Remote-friendly: 0-10 points
    - Freshness: 0-10 points
    - Base: 10 points (it's a product leadership job if it got here)
    """
    combined_text = f"{posting.title} {posting.location} {posting.description}"

    title_score = score_title(posting.title)
    desc_score = score_description(posting.description)
    remote_score = score_remote(combined_text)
    freshness_score = score_freshness(posting.posted_date)
    base_score = 10

    total = title_score + desc_score + remote_score + freshness_score + base_score
    return min(total, 100)
