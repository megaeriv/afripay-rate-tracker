"""
scrapers/monieworld.py — CALIBRATED from live codegen (July 2026).

Captured flow:
    page.goto("https://monieworld.com/")
    page.get_by_role("button", name="Necessary only").click()
    -> rate shows as "£1 = ₦1,865₦1,857"

KEY: two figures shown with NO separator between them — ₦1,865 (boosted)
and ₦1,857 (standard). extract_all_rates() splits them correctly and
pick_standard_rate() returns the LOWER one (₦1,857). GBP only.
"""

import re
from playwright.async_api import Page
from .base import extract_all_rates, pick_standard_rate


async def get_rate(page: Page, currency: str, url: str) -> dict:
    await page.goto(url, wait_until="domcontentloaded", timeout=30000); await page.wait_for_timeout(3000)

    for name in ["Necessary only", "Accept", "Accept all"]:
        try:
            await page.get_by_role("button", name=name).click(timeout=3000)
            break
        except Exception:
            continue

    await page.wait_for_timeout(1500)

    # The rate line looks like "£1 = ₦1,865₦1,857"
    raw_text = ""
    try:
        locator = page.get_by_text(re.compile(r"£1\s*=\s*₦[\d,]+", re.I))
        raw_text = await locator.first.inner_text(timeout=6000)
    except Exception:
        pass

    rates = extract_all_rates(raw_text)
    standard_rate = pick_standard_rate(rates)  # lower of the two = standard

    return {
        "company": "monieworld",
        "currency": currency,
        "standard_rate": standard_rate,
        "raw_text_found": raw_text,
        "all_rates_seen": rates,
        "status": "ok" if standard_rate else "NEEDS_SELECTOR_FIX",
    }
