"""Main orchestrator: scrape → normalize → score → dedup → notify → store."""

from __future__ import annotations

import asyncio
import logging
import sys

from .config import get_config
from .dedup import deduplicate
from .models import JobPosting
from .notifier import notify_slack
from .scorer import score_posting
from .scrapers import AboveboardScraper, IndeedScraper, LinkedInScraper, WellfoundScraper
from .storage import append_postings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def run() -> list[JobPosting]:
    """Run the full prospecting pipeline."""
    config = get_config()

    # Build list of enabled scrapers
    scrapers = []
    if config.scraper_linkedin:
        scrapers.append(LinkedInScraper(serpapi_key=config.serpapi_key, delay=config.request_delay))
    if config.scraper_indeed:
        scrapers.append(IndeedScraper(delay=config.request_delay))
    if config.scraper_aboveboard:
        scrapers.append(AboveboardScraper(delay=config.request_delay))
    if config.scraper_wellfound:
        scrapers.append(WellfoundScraper(delay=config.request_delay))

    if not scrapers:
        logger.warning("No scrapers enabled!")
        return []

    logger.info("Running %d scrapers...", len(scrapers))

    # Run all scrapers concurrently
    results = await asyncio.gather(*[s.safe_scrape() for s in scrapers])

    # Flatten results
    all_postings: list[JobPosting] = []
    for batch in results:
        all_postings.extend(batch)

    logger.info("Collected %d raw postings", len(all_postings))

    # Score each posting
    for posting in all_postings:
        posting.score = score_posting(posting)

    # Deduplicate
    unique = deduplicate(all_postings)
    logger.info("After dedup: %d unique postings", len(unique))

    # Sort by score
    unique.sort(key=lambda p: p.score, reverse=True)

    # Notify via Slack
    if config.has_slack:
        sent = await notify_slack(
            unique,
            webhook_url=config.slack_webhook_url,
            bot_token=config.slack_bot_token,
            channel_id=config.slack_channel_id,
            min_score=config.min_score,
        )
        logger.info("Sent %d Slack notifications", sent)

    # Store results
    all_stored = append_postings(unique, config.storage_path)
    logger.info("Total stored postings: %d", len(all_stored))

    # Print summary
    print("\n" + "=" * 60)
    print(f"  Prospector Results: {len(unique)} unique postings found")
    print("=" * 60)
    for posting in unique[:20]:
        emoji = "🔥" if posting.score >= 70 else "⭐" if posting.score >= 50 else "  "
        print(f"  {emoji} [{posting.score:3d}] {posting.company} — {posting.title}")
        print(f"        {posting.source} | {posting.location or 'No location'}")
        print(f"        {posting.url}")
        print()

    if len(unique) > 20:
        print(f"  ... and {len(unique) - 20} more (see {config.storage_path})")

    return unique


def main():
    """Entry point."""
    try:
        postings = asyncio.run(run())
        logger.info("Done! Found %d postings.", len(postings))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    main()
