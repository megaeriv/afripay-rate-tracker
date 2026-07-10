"""
scrapers/western_union.py — CALIBRATED from live codegen (July 2026).

Both flows turned out simpler than feared — the rate is on the first page
after dismissing cookies, no multi-step click-through needed.

GBP flow:
    page.goto(".../gb/en/web/send-money/start?ReceiveCountry=NG&...")
    page.get_by_role("button", name="Reject all").click()
    -> "GBP = 1,824.2325 NGN"

USD flow:
    page.goto(".../us/en/currency-converter/usd-to-ngn-rate.html")
    page.get_by_role("button", name="Reject all").click()
    -> "USD – 1343.2800 NGN"   (note: en-dash, not equals sign)

Single rate per page, no boosted variant.
"""

import re
from playwright.async_api import Page
from .base import extract_all_rates, pick_standard_rate

COOKIE_BUTTON_NAMES = ["Reject all", "Accept all", "Accept", "I Agree"]


async def get_rate(page: Page, currency: str, url: str) -> dict:
    await page.goto(url, wait_until="networkidle", timeout=25000)

    for name in COOKIE_BUTTON_NAMES:
        try:
            await page.get_by_role("button", name=name).click(timeout=3000)
            break
        except Exception:
            continue

    await page.wait_for_timeout(2000)

    # GBP page uses "GBP = 1,824.2325 NGN"; USD page uses "USD – 1343.2800 NGN"
    # Accept either '=' or an en/em dash between code and number.
    raw_text = ""
    try:
        locator = page.get_by_text(re.compile(rf"{currency}\s*[=\u2013\u2014-]\s*[\d,.]+\s*NGN", re.I))
        raw_text = await locator.first.inner_text(timeout=6000)
    except Exception:
        pass

    # one retry if nothing found (WU can be slow)
    if not raw_text:
        try:
            await page.reload(wait_until="networkidle")
            await page.wait_for_timeout(2000)
            locator = page.get_by_text(re.compile(rf"{currency}\s*[=\u2013\u2014-]\s*[\d,.]+\s*NGN", re.I))
            raw_text = await locator.first.inner_text(timeout=6000)
        except Exception:
            pass

    rates = extract_all_rates(raw_text)
    standard_rate = pick_standard_rate(rates)

    return {
        "company": "western_union",
        "currency": currency,
        "standard_rate": standard_rate,
        "raw_text_found": raw_text,
        "status": "ok" if standard_rate else "NEEDS_SELECTOR_FIX",
    }
