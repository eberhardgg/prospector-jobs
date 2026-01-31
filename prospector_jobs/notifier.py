"""Slack notifications for high-scoring job postings.

Supports two modes:
1. Slack Bot Token + Channel ID (preferred) — posts to a specific channel via Slack API
2. Slack Webhook URL (fallback) — posts via incoming webhook
"""

from __future__ import annotations

import logging

import httpx

from .models import JobPosting

logger = logging.getLogger(__name__)

SLACK_API_URL = "https://slack.com/api/chat.postMessage"


def format_posting(posting: JobPosting) -> str:
    """Format a job posting as a Slack mrkdwn string."""
    score_emoji = "🔥" if posting.score >= 70 else "⭐" if posting.score >= 50 else "📋"
    return (
        f"{score_emoji} *{posting.company}* — {posting.title}\n"
        f"Score: *{posting.score}/100* | Source: {posting.source}\n"
        f"Location: {posting.location or 'Not specified'}\n"
        f"<{posting.url}|View posting>"
    )


def _build_blocks(posting: JobPosting) -> list[dict]:
    """Build Slack Block Kit payload for a single posting."""
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": format_posting(posting)},
        },
        {"type": "divider"},
    ]


async def _send_via_api(
    client: httpx.AsyncClient,
    posting: JobPosting,
    bot_token: str,
    channel_id: str,
) -> bool:
    """Send a posting via Slack Bot Token API."""
    try:
        resp = await client.post(
            SLACK_API_URL,
            headers={"Authorization": f"Bearer {bot_token}"},
            json={
                "channel": channel_id,
                "blocks": _build_blocks(posting),
                "text": f"{posting.company} — {posting.title} (Score: {posting.score})",
            },
        )
        data = resp.json()
        if not data.get("ok"):
            logger.error("Slack API error for %s: %s", posting.company, data.get("error"))
            return False
        return True
    except httpx.HTTPError as e:
        logger.error("Failed to notify for %s: %s", posting.company, e)
        return False


async def _send_via_webhook(
    client: httpx.AsyncClient,
    posting: JobPosting,
    webhook_url: str,
) -> bool:
    """Send a posting via Slack incoming webhook."""
    try:
        resp = await client.post(webhook_url, json={"blocks": _build_blocks(posting)})
        resp.raise_for_status()
        return True
    except httpx.HTTPError as e:
        logger.error("Failed to notify for %s: %s", posting.company, e)
        return False


async def notify_slack(
    postings: list[JobPosting],
    webhook_url: str = "",
    bot_token: str = "",
    channel_id: str = "C0AC2NEL32R",
    min_score: int = 40,
) -> int:
    """Send high-scoring postings to Slack. Returns count sent.

    Prefers bot_token + channel_id; falls back to webhook_url.
    """
    if not webhook_url and not bot_token:
        logger.warning("No Slack credentials configured, skipping notifications")
        return 0

    qualifying = sorted(
        (p for p in postings if p.score >= min_score),
        key=lambda p: p.score,
        reverse=True,
    )
    if not qualifying:
        logger.info("No postings above minimum score threshold (%d)", min_score)
        return 0

    sent = 0
    async with httpx.AsyncClient() as client:
        for posting in qualifying:
            if bot_token:
                ok = await _send_via_api(client, posting, bot_token, channel_id)
            else:
                ok = await _send_via_webhook(client, posting, webhook_url)
            if ok:
                sent += 1
                logger.info(
                    "Notified: %s at %s (score: %d)",
                    posting.title,
                    posting.company,
                    posting.score,
                )

    return sent
