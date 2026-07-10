"""
config.py — Central configuration for the AfriPay rate tracker automation.

Column mappings below were read directly from your uploaded
AFRIPAY_PRICE_COMPARISON.xlsx ( GBP/NGN / EUR/NGN / USD/NGN tabs).
Columns are 1-indexed to match gspread / Google Sheets convention (A=1).
"""

from datetime import time

# ---------------------------------------------------------------------------
# Run schedule (used by main.py to decide which column — M/A/C — to write to)
# ---------------------------------------------------------------------------
RUN_TIMES = {
    "morning": time(9, 0),
    "afternoon": time(14, 0),
    "closing": time(17, 0),
}

# ---------------------------------------------------------------------------
# Google Sheet target
# ---------------------------------------------------------------------------
GOOGLE_SHEET_NAME = "AFRIPAY_PRICE_COMPARISON"  # or use SHEET_ID below instead
GOOGLE_SHEET_ID = "1VB9NNLgppp8BDakV2MVwR67616ayvqoNCv-2bm3xfRk"  # paste the sheet ID from its URL for more reliable access
DATE_COLUMN = 1  # column A on every tab

# ---------------------------------------------------------------------------
# Per-currency sheet + company + column layout
# Each company maps to (morning_col, afternoon_col, closing_col)
# ---------------------------------------------------------------------------
SHEETS = {
    "GBP": {
        "tab_name":  "GBP/NGN",
        "companies": {
            "afripay":       (2, 3, 4),
            "lemfi":         (6, 7, 8),
            "remitly":       (10, 11, 12),
            "transfergo":    (14, 15, 16),
            "western_union": (18, 19, 20),
            "monieworld":    (22, 23, 24),
        },
    },
    "EUR": {
        "tab_name": "EUR/NGN",
        "companies": {
            "afripay":    (2, 3, 4),
            "lemfi":      (6, 7, 8),
            "remitly":    (10, 11, 12),
            "transfergo": (14, 15, 16),
        },
    },
    "USD": {
        "tab_name": "USD/NGN",
        "companies": {
            # NOTE: afripay USD has no rate source (the afripay.uk page only
            # exposes GBP + EUR corridors). Column mapping kept here so that
            # if AfriPay adds a USD corridor later, you only need to add a
            # USD url under SITE_URLS['afripay']. Until then this column
            # stays blank — the orchestrator skips any company with no URL.
            "afripay":       (2, 3, 4),
            "lemfi":         (6, 7, 8),
            "remitly":       (10, 11, 12),
            "western_union": (14, 15, 16),
            # CONFIRMED: columns 18-20 are reserved for a 5th company, not
            # yet named. Add it here (and add a matching site URL below +
            # a scrapers/<company>.py module) once you know who it is:
            # "company_name": (18, 19, 20),
        },
    },
}

# ---------------------------------------------------------------------------
# Site URLs per currency, as provided.
# NOTE flags below highlight things to double check before first live run.
# ---------------------------------------------------------------------------
SITE_URLS = {
    "afripay": {
        # Same URL for all three currencies. Currency is switched via the
        # #ddlcountry (GBP path) and #ddlcountry_foreign dropdowns:
        #   value "6"  = GBP send corridor (rate ~1872)
        #   value "37" = EUR corridor (rate ~1595)
        # CONFIRMED via codegen. USD not exposed on this page — AfriPay is
        # GBP+EUR only here, so USD is intentionally omitted for afripay.
        "GBP": "https://afripay.uk/send-money-to-nigeria",
        "EUR": "https://afripay.uk/send-money-to-nigeria",
    },
    "lemfi": {
        # Same URL for all three — currency switched via in-page dropdowns.
        # CONFIRMED via codegen (GBP/EUR/USD all reachable on this one page).
        "GBP": "https://lemfi.com/en-gb?amount=100&amountType=sending",
        "EUR": "https://lemfi.com/en-gb?amount=100&amountType=sending",
        "USD": "https://lemfi.com/en-gb?amount=100&amountType=sending",
    },
    "remitly": {
        # Country-locale-specific URLs; currency follows the URL, but the
        # in-page country switcher also works (captured in codegen).
        "GBP": "https://www.remitly.com/gb/en/money-transfer/send-money-to-nigeria",
        "EUR": "https://www.remitly.com/be/en/money-transfer/send-money-to-nigeria",
        "USD": "https://www.remitly.com/us/en/money-transfer/send-money-to-nigeria",
    },
    "transfergo": {
        # URL fully determines the pair. Both CONFIRMED via codegen.
        "GBP": "https://www.transfergo.com/currency-converter/gbp-to-ngn",
        "EUR": "https://www.transfergo.com/currency-converter/eur-to-ngn",
    },
    "western_union": {
        "GBP": "https://www.westernunion.com/gb/en/web/send-money/start?ReceiveCountry=NG&ISOCurrency=NGN&SendAmount=200.00&FundsOut=AG&FundsIn=WUPay",
        "USD": "https://www.westernunion.com/us/en/currency-converter/usd-to-ngn-rate.html",
    },
    "monieworld": {
        # Homepage widget, GBP only. CONFIRMED via codegen — rate shows as
        # "£1 = ₦1,865₦1,857" (standard is the lower figure, ₦1,857).
        "GBP": "https://monieworld.com/",
    },
}

# Words that flag a promotional / boosted rate rather than the standard one.
# Used by the "pick the standard (lower) rate" logic in scrapers/base.py
BOOSTED_RATE_KEYWORDS = [
    "boost", "boosted", "special", "promo", "promotional",
    "limited", "flash", "bonus", "offer",
]
