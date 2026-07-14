# AfriPay Rate Tracker

This project automatically collects Nigerian Naira exchange rates from six remittance providers three times a day and writes them into a Google Sheet. It covers AfriPay, Lemfi, Remitly, TransferGo, Western Union and MonieWorld across GBP, EUR and USD.

Rates are captured at three points each day, timed to UK hours: morning at 9am, afternoon at 2pm and closing at 5pm. Each run finds the current day's row in the sheet (or creates it), then fills the correct Morning, Afternoon or Closing column for every provider and currency.

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

**TransferGo** determines the currency pair entirely from the URL, so no in page interaction is needed. The rate appears in a heading such as "GBP = 1844.99726 NGN".

**AfriPay** exposes GBP and EUR corridors only. The rate appears once both country dropdowns are set, shown as a four decimal figure followed by the words "Exchange Rate".

**Lemfi** is a single page reachable for all three currencies. The receive currency must be set to Nigeria first, then the send currency is chosen. It displays two figures side by side, standard and boosted, and the tracker keeps the lower one. Because the page is slow to load on cloud servers, the scraper waits patiently and retries until a real, non zero rate appears.

**Remitly** uses a separate locale specific URL per currency and labels its standard rate explicitly, which makes it straightforward to read.

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

## Running a manual test

The workflow can be triggered by hand from the GitHub Actions tab using "Run workflow". A dropdown allows a specific slot to be forced (morning, afternoon or closing) for testing, rather than relying on the scheduled time. This writes to the current day's row in the chosen slot.

## Standard rate rule

Several providers advertise a boosted or promotional rate alongside their standard rate. The tracker always records the standard rate, which is the lower of the two figures. The extraction logic pulls every plausible rate figure from the relevant text, filters out anything flagged with promotional wording, and selects the lowest remaining value.

## Maintenance

The system is designed to run without daily attention, but a few things are worth knowing.

Each run appears in the GitHub Actions tab with a green tick on success. The cron-job.org dashboard shows the last execution status for each of the three daily jobs.

The scheduler authenticates to GitHub with a personal access token that has an expiry date. When that token expires the three cron jobs will begin to fail, at which point a new token is generated and pasted into the Authorization header of each job. This is the only recurring maintenance item.

These are live websites rather than official rate APIs. If a provider redesigns its rate page, that one scraper may stop finding a value and will log the issue rather than crash the whole run. Recalibrating it means recording the new page layout with `playwright codegen` and updating that scraper's selectors. In practice this is rare.
