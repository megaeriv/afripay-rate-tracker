import re
from playwright.async_api import Page
from .base import extract_all_rates, pick_standard_rate


async def get_rate(page: Page, currency: str, url: str) -> dict:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception:
        try:
            await page.goto(url, timeout=30000)
        except Exception:
            pass
    await page.wait_for_timeout(3000)

    for name in ["Necessary only", "Accept", "Accept all"]:
        try:
            await page.get_by_role("button", name=name).click(timeout=3000)
            break
        except Exception:
            continue

    await page.wait_for_timeout(1500)

    raw_text = ""
    try:
        anchor = page.get_by_text(re.compile(r"£1\s*=", re.I)).first
        await anchor.wait_for(state="visible", timeout=6000)
        parent = anchor.locator("xpath=..")
        raw_text = await parent.inner_text(timeout=4000)
    except Exception:
        pass

    if len(extract_all_rates(raw_text)) < 2:
        try:
            body = await page.locator("body").inner_text(timeout=5000)
            m = re.search(r"£1\s*=\s*₦[\d,]+\s*₦?[\d,]+", body)
            if m:
                raw_text = m.group()
        except Exception:
            pass

    rates = extract_all_rates(raw_text)
    standard_rate = pick_standard_rate(rates)

    return {
        "company": "monieworld",
        "currency": currency,
        "standard_rate": standard_rate,
        "raw_text_found": raw_text,
        "all_rates_seen": rates,
        "status": "ok" if standard_rate else "NEEDS_SELECTOR_FIX",
    }
