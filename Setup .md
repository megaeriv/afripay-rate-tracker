# AfriPay Rate Tracker

This project automatically collects Nigerian Naira exchange rates from six remittance providers three times a day and writes them into a Google Sheet. It covers AfriPay, Lemfi, Remitly, TransferGo, Western Union and MonieWorld across GBP, EUR and USD.

Rates are captured at three points each day, timed to UK hours: morning at 9am, afternoon at 2pm and closing at 5pm. Each run finds the current day's row in the sheet, or creates it, then fills the correct Morning, Afternoon or Closing column for every provider and currency.

## Status

All sites are calibrated and live. Every scraper uses real, verified selectors captured with `playwright codegen` against the live pages, and the rate parsing has been tested against the actual rate strings each site returns. All thirteen site and currency combinations pass, including the sites that show two rates at once.

## How it works

The system has three parts working together.

The **scrapers** use Playwright to open each provider's live rate page in a headless browser, select the right currencies where a page needs it, read the displayed rate and extract the numeric value. Several providers show two rates at once, a standard rate and a higher promotional or boosted rate. In every case the tracker takes the lower standard rate, never the boosted one.

The **sheet writer** connects to Google Sheets through a service account and writes each rate into its designated cell. It matches the day's date regardless of how the date is formatted, and it resolves the target row once per tab per run so that a single day always produces one clean row rather than duplicates.

The **scheduler** runs on cron-job.org, a free external service. Three separate jobs fire at 9am, 2pm and 5pm UK time and trigger the GitHub Actions workflow, passing the exact slot name (morning, afternoon or closing) with each call. Because the slot is stated explicitly rather than guessed from the clock, a run that starts a few minutes late still lands in the correct column.

## Why cron-job.org instead of GitHub's built in scheduler

GitHub Actions has its own scheduled triggers, but on free accounts those triggers are best effort. In practice they can be delayed by anything from fifteen minutes to over an hour, and occasionally skipped. That level of drift caused runs to land in the wrong time slots or overlap.

cron-job.org fires punctually and lets each job specify its slot directly, which keeps morning, afternoon and closing cleanly separated. It also runs in the Europe/London timezone, so the switch between British Summer Time and GMT is handled automatically with no manual change needed when the clocks move.

## Provider notes

Each provider page behaves slightly differently, and the scrapers account for this.

**TransferGo** determines the currency pair entirely from the URL, so no in page interaction is needed. The rate appears in a heading such as "GBP = 1844.99726 NGN". It covers GBP and EUR.

**AfriPay** exposes GBP and EUR corridors only. The rate appears once both country dropdowns are set (the send dropdown and the receive dropdown), shown as a four decimal figure followed by the words "Exchange Rate".

**Lemfi** is a single page reachable for all three currencies. The receive currency must be set to Nigeria first, then the send currency is chosen. It displays two figures side by side, standard and boosted, and the tracker keeps the lower one. Because the page is slow to load on cloud servers, the scraper waits patiently and retries until a real, non zero rate appears.

**Remitly** uses a separate locale specific URL per currency (gb, be, us) and labels its standard rate explicitly, which makes it straightforward to read. It covers GBP, EUR and USD.

**MonieWorld** covers GBP only. It shows a boosted rate struck through against the standard rate. The scraper reads the wider block of text containing both figures and keeps the lower standard rate.

**Western Union** has two different page types. The GBP page is a transfer start flow and the USD page is a simpler converter. The USD page separates its numbers with a dash rather than an equals sign, which the scraper handles.

## Repository layout

```
rate_tracker/
  config.py            sheet tab names, column mapping, provider URLs, promo keywords
  main.py              orchestrates one run across all providers and currencies
  sheets_writer.py     matches the day's row and writes each rate into the right cell
  requirements.txt     Python dependencies
  scrapers/
    base.py            shared rate extraction and standard rate selection
    afripay.py
    lemfi.py
    remitly.py
    transfergo.py
    western_union.py
    monieworld.py
  .github/workflows/
    rate_tracker.yml   the GitHub Actions workflow, triggered by cron-job.org
```

The Google service account key is never stored in the repository. It is held as a GitHub Actions secret named `GOOGLE_SERVICE_ACCOUNT_JSON` and written to disk only during a run.

## Full setup guide (replicating from scratch)

The system is already set up and running. This section records the complete process so the whole thing can be rebuilt from nothing, whether on a new machine or for a different sheet.

### 1. Install

```bash
cd rate_tracker
pip install -r requirements.txt
playwright install chromium
```

### 2. Google Sheets access through a service account

1. In the Google Cloud Console, create a project (or reuse one) and enable the Google Sheets API and Google Drive API.
2. Under IAM and Admin, Service Accounts, create a service account.
3. Create a JSON key for it, download it, and save it as `rate_tracker/service_account.json` for local runs. For the scheduled cloud runs it is stored as a GitHub secret instead (see step 5).
4. Open the Google Sheet, click Share, paste the service account email (it looks like `name@project.iam.gserviceaccount.com`) and give it Editor access.
5. In `config.py`, set `GOOGLE_SHEET_ID` to the ID from the sheet's URL, which is the long string between `/d/` and `/edit`. This is more reliable than matching by name. Also confirm the tab names in `config.py` match the sheet exactly, including any slash, for example `GBP/NGN`.

### 3. Calibrating a site's selectors

Each scraper is already calibrated, but if a page changes or a new provider is added, the selectors are captured like this. Playwright's recorder opens a real browser and prints the exact selector for anything clicked:

```bash
playwright codegen https://afripay.uk/send-money-to-nigeria
playwright codegen "https://lemfi.com/en-gb?amount=100&amountType=sending"
playwright codegen https://www.remitly.com/gb/en/money-transfer/send-money-to-nigeria
playwright codegen https://www.transfergo.com/currency-converter/gbp-to-ngn
playwright codegen "https://www.westernunion.com/gb/en/web/send-money/start?ReceiveCountry=NG&ISOCurrency=NGN&SendAmount=200.00&FundsOut=AG&FundsIn=WUPay"
playwright codegen https://www.westernunion.com/us/en/currency-converter/usd-to-ngn-rate.html
playwright codegen https://monieworld.com/
```

For each one, interact with the page the way a person would (dismiss the cookie banner, pick a currency, enter an amount) until the rate is visible, then copy the recorded actions into the matching scraper in `scrapers/`. The recorded selectors are more reliable than hand written CSS paths because they come from the live page.

### 4. Testing a single site

Before relying on a scraper, test it on its own in a visible browser so its behaviour can be watched:

```python
# test_one.py
import asyncio
from playwright.async_api import async_playwright
from scrapers import transfergo

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # visible browser
        page = await browser.new_page()
        result = await transfergo.get_rate(page, "GBP", "https://www.transfergo.com/currency-converter/gbp-to-ngn")
        print(result)
        await browser.close()

asyncio.run(main())
```

A result containing a `standard_rate` value means that site works. The scheduled runs use a headless (invisible) browser automatically.

### 5. Storing the key as a GitHub secret

For the cloud runs the service account key is not committed to the repository. Instead:

1. Open the JSON key file and copy its entire contents.
2. In the repository, go to Settings, Secrets and variables, Actions, New repository secret.
3. Name it `GOOGLE_SERVICE_ACCOUNT_JSON` and paste the JSON as the value.

The workflow writes this secret to `service_account.json` at the start of each run.

### 6. Running manually from the command line

```bash
python main.py morning
python main.py afternoon
python main.py closing
```

Each run prints a line per site (`[OK]`, `[SKIP]` or a failure) showing exactly what was written and what needs attention.

### 7. Scheduling with cron-job.org

The scheduler is external, using the free service cron-job.org. Three jobs, one per slot, trigger the workflow at the right times. A GitHub personal access token with Actions read and write permission on the repository is required first (created under Settings, Developer settings, Personal access tokens, Fine grained tokens).

Each job is configured as follows:

- Request method: POST
- URL: `https://api.github.com/repos/megaeriv/afripay-rate-tracker/actions/workflows/rate_tracker.yml/dispatches`
- Timezone: Europe/London
- Schedule: 09:00 for morning, 14:00 for afternoon, 17:00 for closing
- Headers:
  - `Authorization` set to the word `Bearer`, a space, then the personal access token
  - `Accept` set to `application/vnd.github+json`
  - `Content-Type` set to `application/json`
- Request body, with the slot name changed per job:
  - Morning: `{"ref":"main","inputs":{"slot_override":"morning"}}`
  - Afternoon: `{"ref":"main","inputs":{"slot_override":"afternoon"}}`
  - Closing: `{"ref":"main","inputs":{"slot_override":"closing"}}`

GitHub's own `schedule` triggers are intentionally left out of the workflow so that only cron-job.org drives the runs, which avoids duplicate or mistimed executions.

### 8. Running a manual test from GitHub

The workflow can also be triggered by hand from the GitHub Actions tab using Run workflow. A dropdown allows a specific slot to be forced (morning, afternoon or closing) for testing rather than relying on the scheduled time. This writes to the current day's row in the chosen slot.

## Standard rate rule

Several providers advertise a boosted or promotional rate alongside their standard rate. The tracker always records the standard rate, which is the lower of the two figures.

The logic in `scrapers/base.py` pulls every plausible rate figure from the relevant text, drops any figure whose nearby text contains a promotional keyword (boost, special, promo, flash, bonus, offer and similar, with the full list in `config.BOOSTED_RATE_KEYWORDS`), and returns the lowest remaining value. If a site introduces new promotional wording, adding that word to the keyword list keeps the rule working.

## Maintenance

The system is designed to run without daily attention, but a few things are worth knowing.

Each run appears in the GitHub Actions tab with a green tick on success. The cron-job.org dashboard shows the last execution status for each of the three daily jobs.

The scheduler authenticates to GitHub with a personal access token that has an expiry date. When that token expires the three cron jobs will begin to fail, at which point a new token is generated and pasted into the Authorization header of each job. This is the only recurring maintenance item.

These are live websites rather than official rate APIs. If a provider redesigns its rate page, that one scraper may stop finding a value and will log the issue rather than crash the whole run. Recalibrating it means recording the new page layout with `playwright codegen` and updating that scraper's selectors, as described in the setup guide above. In practice this is rare, since remittance sites do not redesign their rate widgets often, and simple converter pages like TransferGo change far less than a full transfer flow like Western Union's.
