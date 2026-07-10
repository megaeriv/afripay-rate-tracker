"""
scrapers/base.py — Shared helpers used by every site-specific scraper.

Key responsibility: given all the rate-like numbers found near a "boosted /
special" label vs a plain rate, always resolve to the STANDARD (lower)
rate — never the promotional one — per Mega's requirement.
"""

import re
from config import BOOSTED_RATE_KEYWORDS

RATE_PATTERN = re.compile(r"[\d]{2,5}(?:[.,]\d{1,4})?")

# Matches NGN rate figures specifically, handling comma thousands separators:
# e.g. "1,850", "1868.5", "1,865", "1343.2800". Requires the value to look
# like a plausible NGN-per-unit rate (3-5 leading digits) to avoid matching
# stray small numbers like amounts ("100") or years.
NGN_RATE_PATTERN = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d{3,5}(?:\.\d+)?")


def extract_all_rates(text: str, lo: float = 500, hi: float = 5000) -> list[float]:
    """
    Pull EVERY plausible NGN rate figure out of a string, de-comma'd, and
    filtered to a sane band. Critical for dual-rate sites where standard
    and boosted rates sit side by side in one string, e.g.:
      "GBP = 1,850 1,868.5 NGN"  -> [1850.0, 1868.5]
      "£1 = ₦1,865₦1,857"        -> [1865.0, 1857.0]
    """
    if not text:
        return []
    found = []
    for m in NGN_RATE_PATTERN.finditer(text):
        try:
            val = float(m.group().replace(",", ""))
        except ValueError:
            continue
        if lo <= val <= hi:
            found.append(val)
    return found


def parse_number(text: str) -> float | None:
    """Extract a single numeric rate from a text fragment like '₦1,988.45'.
    For strings that may contain MULTIPLE rates, use extract_all_rates()
    instead and feed the result to pick_standard_rate()."""
    if not text:
        return None
    cleaned = text.replace(",", "").replace("₦", "").strip()
    match = RATE_PATTERN.search(cleaned)
    if not match:
        return None
    try:
        return float(match.group().replace(",", ""))
    except ValueError:
        return None


def is_boosted_label(text: str) -> bool:
    """True if nearby text suggests this rate is a promo/boosted rate."""
    if not text:
        return False
    lowered = text.lower()
    return any(keyword in lowered for keyword in BOOSTED_RATE_KEYWORDS)


def pick_standard_rate(candidates: list) -> float | None:
    """
    Accepts EITHER:
      - a list of floats (rates already extracted), OR
      - a list of {"rate": float, "label_text": str} dicts.

    Rule: exclude anything whose nearby label text flags it as boosted/
    promotional, then return the LOWEST remaining rate (the standard rate
    is always the lower conversion figure per Mega's instruction). If
    every candidate looks boosted, fall back to the lowest of all.
    """
    if not candidates:
        return None

    # Normalise to dict form
    normalised = []
    for c in candidates:
        if isinstance(c, dict):
            normalised.append(c)
        else:
            normalised.append({"rate": c, "label_text": ""})

    non_boosted = [c["rate"] for c in normalised if not is_boosted_label(c.get("label_text", ""))]
    pool = non_boosted if non_boosted else [c["rate"] for c in normalised]
    pool = [r for r in pool if r is not None]
    if not pool:
        return None
    return min(pool)


async def try_selectors(page, selectors: list[str], timeout_ms: int = 4000) -> str:
    """
    Try a list of candidate selectors in order, return the inner_text of
    the first one that appears. This buys resilience against small DOM
    changes (a site renaming one class won't break the whole scraper if
    a second/third fallback selector still matches).
    Returns '' if none of them appear within the timeout.
    """
    for sel in selectors:
        try:
            locator = page.locator(sel).first
            await locator.wait_for(state="visible", timeout=timeout_ms)
            text = (await locator.inner_text()).strip()
            if text:
                return text
        except Exception:
            continue
    return ""


async def try_click(page, selectors: list[str], timeout_ms: int = 3000) -> bool:
    """Try clicking the first selector in the list that appears. Returns
    True if a click succeeded, False if none matched (non-fatal — caller
    should continue, since e.g. a cookie banner may simply not appear)."""
    for sel in selectors:
        try:
            await page.click(sel, timeout=timeout_ms)
            return True
        except Exception:
            continue
    return False


async def safe_text(locator, timeout_ms: int = 5000) -> str:
    """Return element text, or '' if it never appears (avoids hard crashes
    when a site changes its DOM — logs should be checked if this fires a lot)."""
    try:
        await locator.wait_for(state="visible", timeout=timeout_ms)
        return (await locator.inner_text()).strip()
    except Exception:
        return ""
