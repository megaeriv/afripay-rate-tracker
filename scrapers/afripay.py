import re
from playwright.async_api import Page
from .base import extract_all_rates, pick_standard_rate

COOKIE_BUTTON_NAMES = ["Allow Cookies", "Accept", "Accept Cookies"]

CURRENCY_CONTROLS = {
    "GBP": [("#ddlcountry", "6")],
    "EUR": [("#ddlcountry", "6"), ("#ddlcountry_foreign", "37")],
}


async def get_rate(page: Page, currency: str, url: str) -> dict:
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(1500)

    for name in COOKIE_BUTTON_NAMES:
        try:
            await page.get_by_role("button", name=name).click(timeout=2500)
            break
        except Exception:
            continue

    controls = CURRENCY_CONTROLS.get(currency, [])
    for selector, value in controls:
        try:
            await page.locator(selector).select_option(value, timeout=5000)
            await page.wait_for_timeout(800)
        except Exception:
            pass
    await page.wait_for_timeout(1200)

    raw_text = ""
    try:
        locator = page.get_by_text(re.compile(r"\d{3,5}\.\d{4}\s*Exchange Rate", re.I))
        raw_text = await locator.first.inner_text(timeout=5000)
    except Exception:
        pass

    if not extract_all_rates(raw_text):
        try:
            body = await page.locator("body").inner_text(timeout=5000)
            matches = re.findall(r"\b\d{3,5}\.\d{4}\b", body)
            band = [m for m in matches if 500 <= float(m) <= 5000]
            raw_text = band[0] if band else raw_text
        except Exception:
            pass

    rates = extract_all_rates(raw_text)
    standard_rate = pick_standard_rate(rates)

    return {
        "company": "afripay",
        "currency": currency,
        "standard_rate": standard_rate,
        "raw_text_found": raw_text[:120] if raw_text else "",
        "status": "ok" if standard_rate else "NEEDS_SELECTOR_FIX",
    }