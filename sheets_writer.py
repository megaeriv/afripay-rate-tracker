"""
sheets_writer.py — Writes scraped rates into the correct cell of your
Google Sheet, matching the exact column layout read from your uploaded
AFRIPAY_PRICE_COMPARISON.xlsx.

Auth: uses a Google Service Account (recommended for unattended/scheduled
scripts — no browser login prompt, works headlessly on a server or in
GitHub Actions). Setup steps are in README.md.
"""

import gspread
from datetime import date
from config import SHEETS, DATE_COLUMN, GOOGLE_SHEET_NAME, GOOGLE_SHEET_ID

SERVICE_ACCOUNT_FILE = "service_account.json"  # see README for how to get this


def _get_client():
    return gspread.service_account(filename=SERVICE_ACCOUNT_FILE)


def _open_sheet():
    gc = _get_client()
    if GOOGLE_SHEET_ID:
        return gc.open_by_key(GOOGLE_SHEET_ID)
    return gc.open(GOOGLE_SHEET_NAME)


def _find_or_create_today_row(worksheet, today: date) -> int:
    """Return the row number for today's date, adding a new row if needed."""
    # UK format DD/MM/YYYY only — matches the existing sheet (e.g. 10/07/2026).
    # Deliberately NOT including the US MM/DD/YYYY variant, which would be
    # ambiguous on days where both are valid (e.g. 07/10 vs 10/07).
    today_str = today.strftime("%d/%m/%Y")
    date_values = worksheet.col_values(DATE_COLUMN)
    for i, cell_value in enumerate(date_values, start=1):
        if cell_value.strip() == today_str:
            return i

    # Not found — append a new row with today's date in the SAME UK format.
    next_row = len(date_values) + 1
    worksheet.update_cell(next_row, DATE_COLUMN, today_str)
    return next_row


def write_rate(currency: str, company: str, run_type: str, rate: float, today: date = None):
    """
    currency: 'GBP' | 'EUR' | 'USD'
    company: matches a key in config.SHEETS[currency]['companies']
    run_type: 'morning' | 'afternoon' | 'closing'
    rate: the standard rate value to write
    """
    if rate is None:
        print(f"[SKIP] {currency}/{company}/{run_type}: no rate to write (scraper returned None)")
        return

    today = today or date.today()
    sheet_config = SHEETS[currency]
    company_cols = sheet_config["companies"].get(company)
    if not company_cols:
        raise ValueError(f"Unknown company '{company}' for currency '{currency}'")

    col_index = {"morning": 0, "afternoon": 1, "closing": 2}[run_type]
    target_col = company_cols[col_index]

    book = _open_sheet()
    worksheet = book.worksheet(sheet_config["tab_name"])

    row = _find_or_create_today_row(worksheet, today)
    worksheet.update_cell(row, target_col, rate)
    print(f"[OK] {sheet_config['tab_name']} row {row} col {target_col} ({company}/{run_type}) = {rate}")


def write_batch(results: list[dict], run_type: str, today: date = None):
    """results: list of scraper output dicts (see scrapers/*.py get_rate())"""
    for r in results:
        write_rate(
            currency=r["currency"],
            company=r["company"],
            run_type=run_type,
            rate=r.get("standard_rate"),
            today=today,
        )
