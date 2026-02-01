"""Score job postings based on ICP fit for fractional CPO prospecting.

ICP (Ideal Customer Profile):
- Series A-C tech/SaaS companies (20-500 employees)
- Hiring their first or replacement CPO/CPTO
- US-based, remote-friendly
- NOT Fortune 500, NOT staffing agencies, NOT aggregator postings
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from .models import JobPosting

# ── Title scoring (0-40) ──────────────────────────────────────────────
# Exact C-level titles score highest — that's the fractional play
TITLE_PATTERNS: list[tuple[str, int]] = [
    (r"\bchief product officer\b", 50),
    (r"\bcpto\b", 50),
    (r"\bchief product (?:&|and) technology officer\b", 48),
    (r"\bsvp[,.]? (?:of )?product\b", 28),
    (r"\bvp[,.]? (?:of )?product\b", 25),
    (r"\bvice president[,.]? (?:of )?product\b", 25),
    (r"\bhead of product\b", 22),
    (r"\bproduct leader\b", 15),
    (r"\bdirector[,.]? (?:of )?product\b", 8),
]

# ── Company quality signals ──────────────────────────────────────────
# These are NEGATIVE signals — big corps and recruiters are not clients
FORTUNE_500_KEYWORDS = {
    "jpmorgan", "jpmorganchase", "jp morgan", "goldman sachs", "bank of america",
    "wells fargo", "citigroup", "citi", "morgan stanley", "u.s. bank", "us bank",
    "capital one", "american express", "amex", "visa", "mastercard",
    "google", "alphabet", "meta", "amazon", "apple", "microsoft", "netflix",
    "walmart", "target", "costco", "home depot", "lowes",
    "unitedhealth", "anthem", "cigna", "aetna", "humana", "kaiser",
    "pfizer", "johnson & johnson", "j&j", "merck", "abbvie",
    "at&t", "verizon", "t-mobile", "comcast",
    "boeing", "lockheed", "raytheon", "northrop",
    "exxon", "chevron", "shell", "bp",
    "ford", "gm", "general motors", "toyota", "tesla",
    "ibm", "oracle", "sap", "salesforce", "cisco", "intel", "nvidia",
    "accenture", "deloitte", "mckinsey", "bain", "bcg",
    "disney", "warner", "paramount", "fox",
    "procter & gamble", "p&g", "unilever", "coca-cola", "pepsi",
    "bny", "state street", "fidelity", "vanguard", "blackrock",
    "trane technologies", "honeywell", "3m", "ge", "general electric",
    "sharkninja", "teradata", "hyland",
}

# Staffing / recruiting firms — they're posting on behalf of others
RECRUITER_KEYWORDS = {
    "lensa", "talently", "talener", "heidrick", "korn ferry", "spencer stuart",
    "robert half", "randstad", "adecco", "manpower", "kelly services",
    "hays", "michael page", "page group", "coda search", "staffing",
    "recruiting", "talent acquisition", "executive search", "search firm",
    "daley and associates", "christian & timbers", "brydon group",
    "selby jennings", "nxt level", "droisys",
}

# Positive company signals — these are the target
STARTUP_SIGNALS: list[tuple[str, int]] = [
    (r"\bseries [a-c]\b", 15),
    (r"\bseed\b", 10),
    (r"\bstartup\b", 10),
    (r"\bearly[- ]stage\b", 12),
    (r"\bgrowth[- ]stage\b", 8),
    (r"\bscale[- ]up\b", 8),
    (r"\bfirst (?:product |)hire\b", 15),
    (r"\bbuild(?:ing)? (?:the |a )?product (?:team|org|function)\b", 12),
    (r"\bfractional\b", 15),
    (r"\binterim\b", 10),
    (r"\bcontract\b", 5),
    (r"\bpart[- ]time\b", 5),
    (r"\bventure[- ]backed\b", 8),
    (r"\bvc[- ]backed\b", 8),
    (r"\bsaas\b", 5),
    (r"\bb2b\b", 3),
    (r"\bfintech\b", 5),
    (r"\bhealthtech\b", 5),
    (r"\bedtech\b", 5),
    (r"\bproptech\b", 5),
    (r"\bmarketplace\b", 3),
]

# Remote-friendly signals
REMOTE_SIGNALS: list[tuple[str, int]] = [
    (r"\bremote\b", 8),
    (r"\bhybrid\b", 3),
    (r"\bwork from anywhere\b", 8),
    (r"\bdistributed\b", 5),
]


def score_title(title: str) -> int:
    """Score based on job title match. Returns 0-40."""
    title_lower = title.lower()
    best = 0
    for pattern, weight in TITLE_PATTERNS:
        if re.search(pattern, title_lower):
            best = max(best, weight)
    return best


def score_company(company: str, title: str, description: str) -> int:
    """Score company fit. Returns -30 to +25.

    Negative = big corp or recruiter (penalize hard)
    Positive = startup signals
    """
    combined = f"{company} {title} {description}".lower()
    company_lower = company.lower().strip()

    # Hard penalty: Fortune 500 / big public companies
    for kw in FORTUNE_500_KEYWORDS:
        if kw in company_lower:
            return -30

    # Hard penalty: Recruiting/staffing firms
    for kw in RECRUITER_KEYWORDS:
        if kw in company_lower:
            return -20

    # Positive: startup/growth signals in description
    total = 0
    for pattern, weight in STARTUP_SIGNALS:
        if re.search(pattern, combined):
            total += weight

    return min(total, 25)


def score_remote(text: str) -> int:
    """Score remote-friendliness. Returns 0-10."""
    text_lower = text.lower()
    total = 0
    for pattern, weight in REMOTE_SIGNALS:
        if re.search(pattern, text_lower):
            total += weight
    return min(total, 10)


def score_freshness(posted_date: datetime | None) -> int:
    """Score based on how recent the posting is. Returns 0-15."""
    if not posted_date:
        return 5  # Unknown date gets a moderate default

    now = datetime.now(UTC)
    if posted_date.tzinfo is None:
        posted_date = posted_date.replace(tzinfo=UTC)

    age_days = (now - posted_date).days

    if age_days <= 1:
        return 15
    elif age_days <= 3:
        return 12
    elif age_days <= 7:
        return 8
    elif age_days <= 14:
        return 4
    elif age_days <= 30:
        return 2
    else:
        return 0


def score_posting(posting: JobPosting) -> int:
    """Score a job posting on a 0-100 scale.

    Breakdown:
    - Title match: 0-50 (CPO/CPTO = 50, VP = 25, Director = 8)
    - Company fit: -30 to +25 (penalizes big corps, rewards startups)
    - Remote-friendly: 0-10
    - Freshness: 0-15
    - Base: 5

    A fresh CPO posting at an unknown company = ~70 (good lead)
    A fresh CPO posting at a startup = 80+ (hot lead)
    A VP posting at JPMorgan = ~10 (noise)
    """
    combined_text = f"{posting.title} {posting.location} {posting.description}"

    title_score = score_title(posting.title)
    company_score = score_company(posting.company, posting.title, posting.description)
    remote_score = score_remote(combined_text)
    freshness_score = score_freshness(posting.posted_date)
    base_score = 5

    total = title_score + company_score + remote_score + freshness_score + base_score
    return max(0, min(total, 100))
