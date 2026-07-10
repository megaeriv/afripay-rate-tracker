"""
scrapers/transfergo.py — CALIBRATED from live codegen (July 2026).

Captured flow:
    page.goto(".../currency-converter/gbp-to-ngn")
    page.get_by_role("button", name="Reject all").click()
    -> text shows "GBP = 1844.99726 NGN"
    EUR page shows "EUR = 1572.63845 NGN"

URL fully determines the currency pair (gbp-to-ngn / eur-to-ngn), so no
in-page switching needed. Single rate per page (no boosted variant seen).
"""

import re
from playwright.async_api import Page
from .base import extract_all_rates, pick_standard_rate

COOKIE_BUTTON_NAMES = ["Reject all", "Accept all", "Accept"]


async def get_rate(page: Page, currency: str, url: str) -> dict:
    await page.goto(url, wait_until="networkidle")

    for name in COOKIE_BUTTON_NAMES:
        try:
            await page.get_by_role("button", name=name).click(timeout=3000)
            break
        except Exception:
            continue

    raw_text = ""
    try:
        # e.g. "GBP = 1844.99726 NGN" — match by the currency-code heading text
        locator = page.get_by_text(re.compile(rf"{currency}\s*=\s*[\d,.]+\s*NGN", re.I))
        raw_text = await locator.first.inner_text(timeout=6000)
    except Exception:
        pass

    rates = extract_all_rates(raw_text)
    standard_rate = pick_standard_rate(rates)

    return {
        "company": "transfergo",
        "currency": currency,
        "standard_rate": standard_rate,
        "raw_text_found": raw_text,
        "status": "ok" if standard_rate else "NEEDS_SELECTOR_FIX",
    }
