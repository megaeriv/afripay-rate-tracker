# AfriPay Rate Tracker: Automation Framework

Automates collecting Morning (9am) / Afternoon (2pm) / Closing (5pm) NGN
exchange rates from AfriPay, Lemfi, Remitly, TransferGo, Western Union and
MonieWorld across GBP, EUR and USD, and writes them straight into your
`AFRIPAY_PRICE_COMPARISON` Google Sheet in the correct cells.

## ⚠️ Status: ALL SITES CALIBRATED ✓ (July 2026)

Every scraper now uses **real, verified selectors** captured via
`playwright codegen` against the live sites. The rate-parsing logic has
been tested against the actual rate strings each site returned — all 13
site/currency combinations pass, including the dual-rate sites.

What's confirmed working per site:
- **TransferGo** (GBP, EUR): rate in a heading like "GBP = 1844.99726 NGN"
- **AfriPay** (GBP, EUR): two dropdowns (#ddlcountry value 6 = GBP,
  #ddlcountry_foreign value 37 = EUR); rate shows as "1872.0000"
- **Lemfi** (GBP, EUR, USD): shows TWO rates e.g. "GBP = 1,850 1,868.5
  NGN"; the lower (1,850) is standard, correctly selected
- **Remitly** (GBP, EUR, USD): explicitly labelled "Standard rate 1 GBP
  = 1858.57"
- **MonieWorld** (GBP): two rates jammed together "£1 = ₦1,865₦1,857";
  the lower (₦1,857) is standard, correctly selected
- **Western Union** (GBP, USD): "GBP = 1,824.2325 NGN" and "USD =
  1343.2800 NGN" (note the US page uses a dash, not equals — handled)

You still need to do the one-time setup below (install, Google Sheets
service account, scheduler). But the hard part, the selectors, is done.

**One caveat that remains true:** these are live websites, not APIs, so a
future redesign of any one site can still break that one scraper. When it
does, a run logs it to `logs/failures.log` and you re-run `playwright
codegen` for just that site and paste the new selector (same process you
just did). Expect this rarely, a couple of times a year at most.

---

## Original setup notes (still apply)

## 1. Install

```bash
cd rate_tracker
pip install -r requirements.txt
playwright install chromium
```

## 2. Google Sheets access (Service Account — no login prompts)

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → create
   a project (or reuse one) → enable the **Google Sheets API** and
   **Google Drive API**.
2. Go to *IAM & Admin → Service Accounts* → Create Service Account.
3. Create a key for it (JSON) → download it → save as
   `rate_tracker/service_account.json`.
4. Open your Google Sheet → click **Share** → paste the service account's
   email (looks like `xxx@xxx.iam.gserviceaccount.com`) → give it **Editor**
   access.
5. In `config.py`, set `GOOGLE_SHEET_ID` to the ID from your sheet's URL
   (the long string between `/d/` and `/edit`) — more reliable than
   matching by name.

## 3. Calibrating selectors (do this once per site)

For each site, run Playwright's built-in recorder, which opens a real
browser and shows you the exact selector for anything you click:

```bash
playwright codegen https://afripay.uk/send-money-to-nigeria
playwright codegen "https://lemfi.com/en-gb?amount=100&amountType=sending"
playwright codegen https://www.remitly.com/gb/en/money-transfer/send-money-to-nigeria
playwright codegen https://www.transfergo.com/currency-converter/gbp-to-ngn
playwright codegen "https://www.westernunion.com/gb/en/web/send-money/start?ReceiveCountry=NG&ISOCurrency=NGN&SendAmount=200.00&FundsOut=AG&FundsIn=WUPay"
playwright codegen https://www.westernunion.com/us/en/currency-converter/usd-to-ngn-rate.html
playwright codegen https://monieworld.com/
```

For each one: interact with the page the way you would manually (pick a
currency, type an amount) until the rate is visible, then copy the
selector Playwright shows you for that rate element into the matching
`SELECTORS` dict in `scrapers/<site>.py`.

**Tip:** if a site shows the rate through an amount you type rather than a
fixed number, right-click the rate value in the browser → Inspect → note
the class name or `data-testid` attribute, that's usually more stable
than a generic CSS path.

Once updated, test a single site in isolation, e.g.:

```python
# test_one.py
import asyncio
from playwright.async_api import async_playwright
from scrapers import afripay

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # headed = watch it work
        page = await browser.new_page()
        result = await afripay.get_rate(page, "GBP", "https://afripay.uk/send-money-to-nigeria")
        print(result)
        await browser.close()

asyncio.run(main())
```

Run with `headless=False` while calibrating so you can see what's
happening; switch back to `headless=True` in `main.py` for scheduled runs.

## 4. Run manually

```bash
python main.py morning
python main.py afternoon
python main.py closing
```

Each run prints a per-site log line (`[OK]` or `[SKIP]`/`FAILED`) so you
can see exactly what got written and what still needs fixing.

## 5. Scheduling: pick ONE of these

### Option A: Cron (if you have a small always-on server / Raspberry Pi / VPS)
```bash
crontab -e
```
```
0 9  * * * cd /path/to/rate_tracker && /usr/bin/python3 main.py morning   >> logs/morning.log 2>&1
0 14 * * * cd /path/to/rate_tracker && /usr/bin/python3 main.py afternoon >> logs/afternoon.log 2>&1
0 17 * * * cd /path/to/rate_tracker && /usr/bin/python3 main.py closing   >> logs/closing.log 2>&1
```
(Adjust the hour numbers for your server's timezone if it isn't UK time.)

### Option B: GitHub Actions (free, no server needed, recommended)
Create `.github/workflows/rate_tracker.yml`:
```yaml
name: Rate Tracker
on:
  schedule:
    - cron: '0 9 * * *'   # 9am UTC — adjust for BST (UK summer time is UTC+1)
    - cron: '0 14 * * *'  # 2pm
    - cron: '0 17 * * *'  # 5pm
  workflow_dispatch: {}     # lets you trigger manually from GitHub's UI too

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r rate_tracker/requirements.txt
      - run: playwright install --with-deps chromium
      - name: Determine run type from time
        id: run_type
        run: |
          HOUR=$(date -u +%H)
          if [ "$HOUR" = "09" ]; then echo "type=morning" >> $GITHUB_OUTPUT
          elif [ "$HOUR" = "14" ]; then echo "type=afternoon" >> $GITHUB_OUTPUT
          else echo "type=closing" >> $GITHUB_OUTPUT
          fi
      - run: python rate_tracker/main.py ${{ steps.run_type.outputs.type }}
        env:
          GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
```
Store your `service_account.json` contents as a GitHub Secret rather than
committing the file, then write it to disk as a step before `main.py` runs.
**Important:** GitHub Actions cron runs in UTC, remember to adjust for
British Summer Time (UTC+1) between late March and late October so 9am/
2pm/5pm stay accurate UK time.

### Option C: Google Cloud Scheduler + Cloud Run/Functions
More setup but keeps everything inside Google's ecosystem, useful if you
want tighter integration with the Sheet. Ask if you'd like this built out
, it's a bigger lift than A/B so I kept it out of this first pass.

## 6. The "standard rate" rule

`scrapers/base.py` → `pick_standard_rate()` does this:
1. Collects every rate-like number found on the page for that company.
2. Drops any whose nearby text contains a promo keyword (`boost`,
   `special`, `promo`, `flash`, `bonus`, `offer`, etc. — full list in
   `config.BOOSTED_RATE_KEYWORDS`).
3. Returns the **lowest** of what's left — matching your instruction that
   the standard rate is always the lower conversion figure.

If a site's wording for a promo rate isn't in that keyword list, add it,
that's the main thing worth watching in the first couple of weeks of runs.

## 7. Known flags to resolve before first live run

- **TransferGo EUR URL**: your original list repeated the GBP URL
  (`gbp-to-ngn`) for EUR. `config.py` currently points EUR to
  `eur-to-ngn`, which matches TransferGo's URL pattern, please confirm
  this is right.
- **USDNGN sheet, columns 18–20**: your sheet has a second, unlabeled
  Morning/Afternoon/Closing block after Western Union with no header
  text. Not wired up in `config.py`, let me know if this is a 5th
  company reserved for later (e.g. MonieWorld for USD?) so I can map it.
- **Western Union GB flow** is the most fragile page here, it's a
  multi-step transfer flow, not a simple rate page, and may hit a cookie
  banner or location check. Budget extra calibration time for this one.
- **Rolling reserve / promo terms**: none of this affects your data, just
  flagging that site redesigns will eventually break a selector or two,
  when a run logs `NEEDS_SELECTOR_FIX` for a site, that's your cue to
  re-run `playwright codegen` for that one site only.

## 8. Will you need to touch this again? (honest answer)

**One-time setup (unavoidable, has to happen once):**
- Calibrate selectors per site (~10–15 min each, see section 3)
- Google service account + sheet sharing (section 2)
- Point the scheduler at it (section 5)

**After that, genuinely nothing**, no logging in, no manual copying, no
checking three times a day. It runs itself and writes straight into your
sheet.

**The one honest caveat:** this is web scraping, not an official data
feed, none of these six companies publish a rate API for you to query.
That means if a site does a visual redesign (renames a CSS class, moves
the rate to a different part of the page), that ONE site's scraper will
stop finding a value until its selector is updated. This is true of any
scraping-based automation, not specific to how this was built — it's the
nature of relying on a website's front-end rather than a stable API.

How this is handled so it doesn't become a chore:
- Every failed extraction gets logged to `logs/failures.log` with a
  timestamp, you check one file, not six websites.
- The five sites without a public rate API are inherently the ones that
  can drift over time; TransferGo/AfriPay-style simple converter pages
  tend to change far less often than a full app flow like Western
  Union's GB transfer start page.
- In practice, expect maybe a couple of these a year, not monthly — most
  remittance sites don't redesign their rate widgets often. When it does
  happen, it's a 10-minute fix (same `playwright codegen` process from
  section 3), not a rebuild.

If you want true zero-maintenance long-term, the only way to fully avoid
this is if any of these providers offer an official rates API, worth
asking AfriPay's competitors directly, since a couple of remittance
companies do publish one for partners. Everything else here (scheduling,
writing to your sheet, choosing the standard rate over a boosted one) is
fully hands-off already.

## File structure
```
rate_tracker/
├── config.py              # sheet columns, URLs, schedule, promo keywords
├── main.py                 # orchestrator — run this on a schedule
├── sheets_writer.py         # writes results into the right Google Sheet cell
├── requirements.txt
├── service_account.json    # you provide this (not included)
└── scrapers/
    ├── base.py             # shared "pick standard rate" + text-parsing helpers
    ├── afripay.py
    ├── lemfi.py
    ├── remitly.py
    ├── transfergo.py
    ├── western_union.py
    └── monieworld.py
```
