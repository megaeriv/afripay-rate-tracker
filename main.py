"""
main.py — Orchestrates one scraping run across all sites/currencies and
writes the results into your Google Sheet.

Usage:
    python main.py morning
    python main.py afternoon
    python main.py closing

Designed to be called by a scheduler (cron / GitHub Actions / Cloud
Scheduler) at 09:00, 14:00 and 17:00 — see README.md for scheduling setup.
"""

import sys
import asyncio
import logging
from datetime import date

from playwright.async_api import async_playwright

from config import SITE_URLS, SHEETS
from sheets_writer import write_batch
from scrapers import afripay, lemfi, remitly, transfergo, western_union, monieworld

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("rate_tracker")

SCRAPER_MODULES = {
    "afripay": afripay,
    "lemfi": lemfi,
    "remitly": remitly,
    "transfergo": transfergo,
    "western_union": western_union,
    "monieworld": monieworld,
}


async def run_all(run_type: str):
    results = []
    failures = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        )

        for currency, sheet_config in SHEETS.items():
            for company in sheet_config["companies"]:
                url = SITE_URLS.get(company, {}).get(currency)
                if not url:
                    continue  # this company isn't tracked for this currency

                module = SCRAPER_MODULES.get(company)
                if not module:
                    log.warning(f"No scraper module for '{company}' — skipping")
                    continue

                page = await context.new_page()
                try:
                    log.info(f"Scraping {company} / {currency} ...")
                    result = await module.get_rate(page, currency, url)
                    results.append(result)
                    if result.get("status") != "ok":
                        failures.append(result)
                except Exception as e:
                    log.error(f"FAILED {company}/{currency}: {e}")
                    failures.append({"company": company, "currency": currency, "error": str(e)})
                finally:
                    await page.close()

        await browser.close()

    log.info(f"Scraped {len(results)} results, {len(failures)} need attention.")
    write_batch(results, run_type=run_type, today=date.today())

    if failures:
        log.warning("The following need selector calibration or manual review:")
        for f in failures:
            log.warning(f"  - {f}")
        _log_failures(run_type, failures)

    return results, failures


def _log_failures(run_type: str, failures: list[dict]) -> None:
    """
    Appends failures to failures.log with a timestamp, so you can check
    ONE file periodically (or hook up an email/Slack alert on top of it —
    see README) instead of reading every run's console output.
    """
    import os
    from datetime import datetime

    os.makedirs("logs", exist_ok=True)
    with open("logs/failures.log", "a") as f:
        ts = datetime.now().isoformat(timespec="seconds")
        for failure in failures:
            f.write(f"{ts} [{run_type}] {failure}\n")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("morning", "afternoon", "closing"):
        print("Usage: python main.py [morning|afternoon|closing]")
        sys.exit(1)

    run_type = sys.argv[1]
    asyncio.run(run_all(run_type))
