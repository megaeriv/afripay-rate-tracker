import re
from playwright.async_api import Page
from .base import extract_all_rates, pick_standard_rate

SEND_COUNTRY = {
    "GBP": "United Kingdom",
    "EUR": "Austria",
    "USD": "United States",
}


async def _read_rate_text(page, currency):
    try:
        locator = page.get_by_text(re.compile(rf"{currency}\s*=\s*[\d,.\s]+NGN", re.I))
        return await locator.first.inner_text(timeout=4000)
    except Exception:
        return ""


async def _set_currencies(page, currency):
    for name in ["Decline cookies", "Accept cookies", "Accept"]:
        try:
            await page.get_by_role("button", name=name).click(timeout=3000)
            break
        except Exception:
            continue
    try:
        await page.locator("div").filter(
            has_text=re.compile(r"^Recipient gets[A-Z]{3}$")
        ).locator("svg").first.click(timeout=5000)
        await page.wait_for_timeout(600)
        await page.locator("#options-box-recipient-gets").get_by_text(
            "Nigeria", exact=False
        ).first.click(timeout=5000)
        await page.wait_for_timeout(1000)
    except Exception:
        pass
    try:
        await page.locator("div").filter(
            has_text=re.compile(r"^You send[A-Z]{3}$")
        ).locator("svg").first.click(timeout=5000)
        await page.wait_for_timeout(600)
        country = SEND_COUNTRY.get(currency, "United Kingdom")
        try:
            await page.get_by_text(country, exact=True).first.click(timeout=4000)
        except Exception:
            await page.get_by_text(re.compile(country, re.I)).first.click(timeout=4000)
        await page.wait_for_timeout(1500)
    except Exception:
        pass


async def get_rate(page: Page, currency: str, url: str) -> dict:
    raw_text = ""
    rates = []
    for attempt in range(2):
        try:
            await page.goto(url, wait_until="commit", timeout=60000)
            await page.wait_for_timeout(4000)
        except Exception:
            await page.wait_for_timeout(3000)
        await _set_currencies(page, currency)
        for _ in range(6):
            raw_text = await _read_rate_text(page, currency)
            rates = extract_all_rates(raw_text)
            if rates and max(rates) > 0:
                break
            await page.wait_for_timeout(3000)
        if rates and max(rates) > 0:
            break
    standard_rate = pick_standard_rate(rates) if rates else None
    return {
        "company": "lemfi",
        "currency": currency,
        "standard_rate": standard_rate,
        "raw_text_found": raw_text,
        "all_rates_seen": rates,
        "status": "ok" if standard_rate else "NEEDS_SELECTOR_FIX",
    }
