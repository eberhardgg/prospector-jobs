# 🔍 Prospector Jobs

**I built an agent to find my next client.**

When a company posts a "Chief Product Officer" or "VP of Product" role, it's a signal: they need product leadership. For someone offering fractional CPO services, that's a lead.

This agent scans job boards automatically, scores each posting on relevance, deduplicates across sources, and sends the best ones to Slack. It's a prospecting pipeline that runs while I sleep.

## Why This Works

Companies hiring for CPO/CPTO roles are telling you:
- They don't have product leadership yet (or just lost it)
- They're at a stage where they need it (Series A-C, growth stage)
- They have budget allocated for this role

Many of these companies would benefit more from a **fractional CPO** than a full-time hire — they just don't know it yet. This agent finds them so I can reach out.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   main.py                        │
│            (orchestrator pipeline)                │
│                                                  │
│  scrape → normalize → score → dedup → notify     │
│                                        → store   │
└────┬──────┬──────┬──────┬──────┬──────┬─────────┘
     │      │      │      │      │      │
     ▼      ▼      ▼      ▼      ▼      ▼
 scrapers/ scorer  dedup  notifier storage
     │
     ├── linkedin.py   (Google dorking / SerpAPI)
     ├── indeed.py     (Indeed search parsing)
     ├── aboveboard.py (Executive job board)
     └── wellfound.py  (Startup jobs)
```

### Scoring (0-100)

| Component      | Points | What it measures                          |
|---------------|--------|-------------------------------------------|
| Title match   | 0-40   | CPO=40, VP Product=30, Head of Product=28 |
| Description   | 0-30   | Startup signals, fractional, first hire   |
| Remote        | 0-10   | Remote/hybrid/distributed                 |
| Freshness     | 0-10   | Posted today=10, this week=6, old=0       |
| Base          | 10     | It's a product leadership role            |

## Setup

```bash
# Clone
git clone https://github.com/eberhardgg/prospector-jobs.git
cd prospector-jobs

# Install
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your Slack webhook URL (optional)

# Run
python -m prospector_jobs.main
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_WEBHOOK_URL` | No | Slack incoming webhook for notifications |
| `SERPAPI_KEY` | No | SerpAPI key for better Google results |
| `STORAGE_PATH` | No | Path for JSON database (default: `./data/jobs.json`) |
| `MIN_SCORE` | No | Minimum score for Slack notifications (default: 40) |
| `REQUEST_DELAY` | No | Seconds between requests (default: 2.0) |
| `SCRAPER_*` | No | Enable/disable scrapers (1/0) |

## Example Output

```
============================================================
  Prospector Results: 12 unique postings found
============================================================
  🔥 [ 85] Acme Corp — Chief Product Officer
        linkedin | Remote
        https://linkedin.com/jobs/view/123

  🔥 [ 78] TechStart — CPTO
        linkedin | San Francisco, CA
        https://linkedin.com/jobs/view/456

  ⭐ [ 62] GrowthCo — VP of Product
        indeed | New York, NY (Hybrid)
        https://indeed.com/viewjob?jk=789

  ⭐ [ 55] DataFlow — Head of Product
        wellfound | Remote (US)
        https://wellfound.com/jobs/101
```

## Adding a New Job Board

1. Create `prospector_jobs/scrapers/newboard.py`
2. Subclass `BaseScraper` and implement `scrape()`:

```python
from prospector_jobs.scrapers.base import BaseScraper
from prospector_jobs.models import JobPosting

class NewBoardScraper(BaseScraper):
    name = "newboard"

    async def scrape(self) -> list[JobPosting]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await self._get(client, "https://newboard.com/search")
            return self._parse_results(resp.text)

    def _parse_results(self, html: str) -> list[JobPosting]:
        # Parse HTML, return JobPosting objects
        ...
```

3. Add it to `main.py`'s scraper list
4. Add a toggle in `config.py`
5. Write tests with mocked HTTP responses

## Development

```bash
# Run tests
pytest -v

# Lint
ruff check .

# Format
ruff format .
```

## Tech Stack

- **Python 3.11+** — async all the way
- **httpx** — modern async HTTP client
- **BeautifulSoup4** — HTML parsing
- **respx** — HTTP mocking for tests
- **ruff** — linting and formatting
- **GitHub Actions** — CI pipeline

## License

MIT
