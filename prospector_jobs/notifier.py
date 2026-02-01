"""Slack notifications for prospector leads.

Two modes:
1. HOT LEAD (score 75+) — immediate individual notification
2. DAILY DIGEST — top 5 leads in a single message, everything else silenced

Supports Slack Bot Token + Channel ID (preferred) or webhook fallback.
"""

from __future__ import annotations

import logging

import httpx

from .models import JobPosting

logger = logging.getLogger(__name__)

SLACK_API_URL = "https://slack.com/api/chat.postMessage"

HOT_LEAD_THRESHOLD = 75
DIGEST_TOP_N = 5


def _tier_emoji(score: int) -> str:
    if score >= 85:
        return "🔥🔥"
    elif score >= 75:
        return "🔥"
    elif score >= 60:
        return "⭐"
    elif score >= 45:
        return "📋"
    else:
        return "◻️"


def format_hot_lead(posting: JobPosting) -> dict:
    """Format a hot lead as a rich Slack message."""
    return {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🔥 Hot Lead: {posting.company}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{posting.title}*\n"
                        f"Score: *{posting.score}/100* | {posting.source}\n"
                        f"Location: {posting.location or 'Not specified'}\n"
                        f"<{posting.url}|View on LinkedIn>"
                    ),
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            "💡 _This company is actively hiring product leadership "
                            "— potential fractional CPO client._"
                        ),
                    }
                ],
            },
            {"type": "divider"},
        ],
        "text": (
            f"🔥 Hot Lead: {posting.company} — {posting.title} "
            f"(Score: {posting.score})"
        ),
    }


def format_digest(postings: list[JobPosting], total_found: int) -> dict:
    """Format top N leads as a single digest message."""
    lines = []
    for i, p in enumerate(postings[:DIGEST_TOP_N], 1):
        emoji = _tier_emoji(p.score)
        lines.append(
            f"{i}. {emoji} *{p.company}* — {p.title}\n"
            f"    Score: *{p.score}* | {p.location or 'Remote/Unknown'} | "
            f"<{p.url}|View>"
        )

    body = "\n\n".join(lines)

    return {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 Daily Prospector — Top {min(len(postings), DIGEST_TOP_N)} Leads",
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": body},
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"_{total_found} total postings scanned · "
                            f"{len(postings)} above threshold · "
                            f"Showing top {min(len(postings), DIGEST_TOP_N)}_"
                        ),
                    }
                ],
            },
            {"type": "divider"},
        ],
        "text": (
            f"📊 Daily Prospector — Top {min(len(postings), DIGEST_TOP_N)} leads "
            f"from {total_found} postings"
        ),
    }


async def _post_to_slack(
    client: httpx.AsyncClient,
    payload: dict,
    bot_token: str = "",
    channel_id: str = "",
    webhook_url: str = "",
) -> bool:
    """Send a payload to Slack via API or webhook."""
    if bot_token and channel_id:
        try:
            resp = await client.post(
                SLACK_API_URL,
                headers={"Authorization": f"Bearer {bot_token}"},
                json={"channel": channel_id, **payload},
            )
            data = resp.json()
            if not data.get("ok"):
                logger.error("Slack API error: %s", data.get("error"))
                return False
            return True
        except httpx.HTTPError as e:
            logger.error("Slack API request failed: %s", e)
            return False
    elif webhook_url:
        try:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error("Slack webhook failed: %s", e)
            return False
    return False


async def notify_slack(
    postings: list[JobPosting],
    webhook_url: str = "",
    bot_token: str = "",
    channel_id: str = "C0AC2NEL32R",
    min_score: int = 40,
    total_scanned: int = 0,
) -> int:
    """Send notifications to Slack. Returns count of messages sent.

    Strategy:
    - Score 75+: Individual "Hot Lead" alert (immediate attention)
    - Score 40-74: Included in daily digest (top 5 only)
    - Score <40: Silenced completely
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

    hot_leads = [p for p in qualifying if p.score >= HOT_LEAD_THRESHOLD]
    digest_leads = [p for p in qualifying if p.score < HOT_LEAD_THRESHOLD]

    sent = 0
    async with httpx.AsyncClient() as client:
        # Send individual alerts for hot leads
        for posting in hot_leads:
            payload = format_hot_lead(posting)
            ok = await _post_to_slack(
                client, payload, bot_token, channel_id, webhook_url
            )
            if ok:
                sent += 1
                logger.info(
                    "🔥 Hot lead: %s at %s (score: %d)",
                    posting.title,
                    posting.company,
                    posting.score,
                )

        # Send a single digest for everything else
        if digest_leads:
            payload = format_digest(
                digest_leads,
                total_found=total_scanned or len(postings),
            )
            ok = await _post_to_slack(
                client, payload, bot_token, channel_id, webhook_url
            )
            if ok:
                sent += 1
                logger.info(
                    "📊 Digest sent: top %d of %d qualifying leads",
                    min(len(digest_leads), DIGEST_TOP_N),
                    len(digest_leads),
                )

    return sent
