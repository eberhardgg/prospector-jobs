"""Data models for job postings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class JobPosting:
    """A normalized job posting from any source."""

    title: str
    company: str
    url: str
    source: str
    posted_date: datetime | None = None
    location: str = ""
    description: str = ""
    score: int = 0

    @property
    def dedup_key(self) -> str:
        """Key for deduplication: normalized company + title."""
        return f"{self.company.lower().strip()}|{self.title.lower().strip()}"

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "title": self.title,
            "company": self.company,
            "url": self.url,
            "source": self.source,
            "posted_date": self.posted_date.isoformat() if self.posted_date else None,
            "location": self.location,
            "description": self.description,
            "score": self.score,
        }

    @classmethod
    def from_dict(cls, data: dict) -> JobPosting:
        """Deserialize from dictionary."""
        posted_date = None
        if data.get("posted_date"):
            posted_date = datetime.fromisoformat(data["posted_date"])
        return cls(
            title=data["title"],
            company=data["company"],
            url=data["url"],
            source=data["source"],
            posted_date=posted_date,
            location=data.get("location", ""),
            description=data.get("description", ""),
            score=data.get("score", 0),
        )
