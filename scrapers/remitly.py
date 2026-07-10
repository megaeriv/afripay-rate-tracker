"""
scrapers/remitly.py — CALIBRATED from live codegen (July 2026).

Captured flow:
    page.goto(".../gb/en/money-transfer/send-money-to-nigeria")
    page.get_by_role("button", name="Decline all").click()
    -> "Standard rate 1 GBP = 1858.57"

    # switch country to change currency:
    page.get_by_role("button", name="United Kingdom").click()
    page.get_by_role("link", name="Belgium").click()
    -> "Standard rate 1 EUR = 1565.62"

    page.get_by_role("button", name="Belgium").click()
    page.get_by_role("option", name="United States").click()
    -> "Standard rate 1 USD = 1365.53"

Remitly helpfully labels the rate "Standard rate" explicitly, so we target
that text directly. Loading the right locale URL per currency (gb/be/us)
is the simplest path and avoids the country-switch dance — we do that,
and only fall back to switching if needed.
"""

import re
from playwright.async_api import Page
from .base import extract_all_rates, pick_standard_rate


async def get_rate(page: Page, currency: str, url: str) -> dict:
    await page.goto(url, wait_until="networkidle")

    for name in ["Decline all", "Accept all", "Accept"]:
        try:
            await page.get_by_role("button", name=name).click(timeout=3000)
            break
        except Exception:
            continue

    await page.wait_for_timeout(1500)

    # Target the explicit "Standard rate 1 XXX = ...." text.
    raw_text = ""
    try:
        locator = page.get_by_text(re.compile(rf"Standard rate\s*1\s*{currency}\s*=", re.I))
        raw_text = await locator.first.inner_text(timeout=6000)
    except Exception:
        pass

    # Fallback: any text with "1 XXX = <number>"
    if not raw_text:
        try:
            locator = page.get_by_text(re.compile(rf"1\s*{currency}\s*=\s*[\d,.]+", re.I))
            raw_text = await locator.first.inner_text(timeout=4000)
        except Exception:
            pass

    rates = extract_all_rates(raw_text)
    standard_rate = pick_standard_rate(rates)

    return {
        "company": "remitly",
        "currency": currency,
        "standard_rate": standard_rate,
        "raw_text_found": raw_text,
        "status": "ok" if standard_rate else "NEEDS_SELECTOR_FIX",
    }
