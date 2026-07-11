import gspread
from datetime import date, datetime, timedelta
from config import SHEETS, DATE_COLUMN, GOOGLE_SHEET_NAME, GOOGLE_SHEET_ID

SERVICE_ACCOUNT_FILE = "service_account.json"

COL_INDEX = {"morning": 0, "afternoon": 1, "closing": 2}


def _get_client():
    return gspread.service_account(filename=SERVICE_ACCOUNT_FILE)


def _open_sheet():
    gc = _get_client()
    if GOOGLE_SHEET_ID:
        return gc.open_by_key(GOOGLE_SHEET_ID)
    return gc.open(GOOGLE_SHEET_NAME)


def _normalise_date(cell_value):
    if cell_value is None or cell_value == "":
        return None
    if isinstance(cell_value, datetime):
        return (cell_value.year, cell_value.month, cell_value.day)
    if isinstance(cell_value, date):
        return (cell_value.year, cell_value.month, cell_value.day)
    if isinstance(cell_value, (int, float)):
        try:
            base = datetime(1899, 12, 30)
            d = base + timedelta(days=float(cell_value))
            return (d.year, d.month, d.day)
        except Exception:
            return None
    s = str(cell_value).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M:%S",
                "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            d = datetime.strptime(s, fmt)
            return (d.year, d.month, d.day)
        except ValueError:
            continue
    try:
        d = datetime.fromisoformat(s.split(" ")[0])
        return (d.year, d.month, d.day)
    except Exception:
        return None


def _find_or_create_today_row(worksheet, today):
    target = (today.year, today.month, today.day)
    date_values = worksheet.col_values(DATE_COLUMN)
    for i, cell_value in enumerate(date_values, start=1):
        if _normalise_date(cell_value) == target:
            return i
    last_dated = 0
    for i, cell_value in enumerate(date_values, start=1):
        if _normalise_date(cell_value) is not None:
            last_dated = i
    next_row = last_dated + 1
    worksheet.update_cell(next_row, DATE_COLUMN, today.strftime("%d/%m/%Y"))
    return next_row


def write_batch(results, run_type, today=None):
    today = today or date.today()
    col_offset = COL_INDEX[run_type]
    book = _open_sheet()
    by_currency = {}
    for r in results:
        by_currency.setdefault(r["currency"], []).append(r)
    for currency, items in by_currency.items():
        sheet_config = SHEETS.get(currency)
        if not sheet_config:
            print(f"[SKIP] no sheet config for currency {currency}")
            continue
        worksheet = book.worksheet(sheet_config["tab_name"])
        row = _find_or_create_today_row(worksheet, today)
        for r in items:
            company = r["company"]
            rate = r.get("standard_rate")
            company_cols = sheet_config["companies"].get(company)
            if not company_cols:
                print(f"[SKIP] unknown company '{company}' for {currency}")
                continue
            if rate is None:
                print(f"[SKIP] {currency}/{company}/{run_type}: no rate")
                continue
            target_col = company_cols[col_offset]
            worksheet.update_cell(row, target_col, rate)
            print(f"[OK] {sheet_config['tab_name']} row {row} col {target_col} ({company}/{run_type}) = {rate}")
