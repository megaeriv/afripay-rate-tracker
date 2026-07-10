import re
from playwright.async_api import Page
from .base import extract_all_rates, pick_standard_rate

SEND_COUNTRY = {
    "GBP": "United Kingdom",
    "EUR": "Austria",
    "USD": "United States",
}


async def get_rate(page: Page, currency: str, url: str) -> dict:
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2000)

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
        await page.wait_for_timeout(500)
        await page.locator("#options-box-recipient-gets").get_by_text(
            "Nigeria", exact=False
        ).first.click(timeout=5000)
        await page.wait_for_timeout(800)
    except Exception:
        pass

    try:
        await page.locator("div").filter(
            has_text=re.compile(r"^You send[A-Z]{3}$")
        ).locator("svg").first.click(timeout=5000)
        await page.wait_for_timeout(500)
        country = SEND_COUNTRY.get(currency, "United Kingdom")
        try:
            await page.get_by_text(country, exact=True).first.click(timeout=4000)
        except Exception:
            await page.get_by_text(re.compile(country, re.I)).first.click(timeout=4000)
        await page.wait_for_timeout(1500)
    except Exception:
        pass

    raw_text = ""
    try:
        locator = page.get_by_text(re.compile(rf"{currency}\s*=\s*[\d,.\s]+NGN", re.I))
        raw_text = await locator.first.inner_text(timeout=6000)
    except Exception:
        pass

    rates = extract_all_rates(raw_text)
    standard_rate = pick_standard_rate(rates)

    return {
        "company": "lemfi",
        "currency": currency,
        "standard_rate": standard_rate,
        "raw_text_found": raw_text,
        "all_rates_seen": rates,
        "status": "ok" if standard_rate else "NEEDS_SELECTOR_FIX",
    }