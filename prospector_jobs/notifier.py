"""Slack webhook notifications for high-scoring job postings."""

from __future__ import annotations

import logging

import httpx

from .models import JobPosting

logger = logging.getLogger(__name__)


def format_posting(posting: JobPosting) -> dict:
    """Format a job posting as a Slack message block."""
    score_emoji = "🔥" if posting.score >= 70 else "⭐" if posting.score >= 50 else "📋"
    return {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"{score_emoji} *{posting.company}* — {posting.title}\n"
                        f"Score: *{posting.score}/100* | Source: {posting.source}\n"
                        f"Location: {posting.location or 'Not specified'}\n"
                        f"<{posting.url}|View posting>"
                    ),
                },
            },
            {"type": "divider"},
        ]
    }


async def notify_slack(
    postings: list[JobPosting],
    webhook_url: str,
    min_score: int = 40,
) -> int:
    """Send high-scoring postings to Slack. Returns count of notifications sent."""
    if not webhook_url:
        logger.warning("No Slack webhook URL configured, skipping notifications")
        return 0

    qualifying = [p for p in postings if p.score >= min_score]
    if not qualifying:
        logger.info("No postings above minimum score threshold (%d)", min_score)
        return 0

    # Sort by score descending
    qualifying.sort(key=lambda p: p.score, reverse=True)

    sent = 0
    async with httpx.AsyncClient() as client:
        for posting in qualifying:
            payload = format_posting(posting)
            try:
                resp = await client.post(webhook_url, json=payload)
                resp.raise_for_status()
                sent += 1
                logger.info(
                    "Notified: %s at %s (score: %d)", posting.title, posting.company, posting.score
                )
            except httpx.HTTPError as e:
                logger.error("Failed to notify for %s: %s", posting.company, e)

    return sent
