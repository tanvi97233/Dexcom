# Dexcom Job Posting Link Preservation

This tool uses local Chrome to collect the publicly rendered LinkedIn Jobs search cards for
**Dexcom**, **Worldwide**. It does not use an API, credentials, or automated login.

The tracker maintains `Dexcom_Job_Tracker.xlsx` with exactly **Country**, **Job Posted Date**,
**Job Title**, and **Direct URL**. Job IDs canonicalize URLs for deduplication across runs; links
are written as clickable Excel hyperlinks.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Google Chrome must be installed. Chrome is visible by default.

## Start application

Start the local dashboard and API with one command:

```bash
PYTHONPATH=. python app.py
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000). The server starts the existing
tracker in a background process, so the dashboard remains responsive while Chrome performs the
public LinkedIn Jobs discovery.

## Use dashboard

1. Open the local dashboard.
2. Select **Past 7 Days** or **Past 24 Hours**.
3. Click **Run Tracker**.
4. Wait for the completion status and current run statistics.
5. Search, sort, or filter the loaded jobs.
6. Use **Download Excel** to download the actual generated workbook.

## CLI

```bash
PYTHONPATH=. python dexcom_tracker.py --filter 7days
PYTHONPATH=. python dexcom_tracker.py --filter 24hours
PYTHONPATH=. python dexcom_tracker.py --filter 7days --dry-run --verbose
```

`--dry-run` leaves the workbook unchanged. The public filter is represented in the search URL and
the engine applies its own exact relative-time filtering afterward.

## Architecture

```text
Dashboard (HTML/CSS/JavaScript) → local Python API → existing Python tracker
→ public LinkedIn Jobs discovery → validation/deduplication/date filtering → Excel
```

The web layer does not replicate tracker rules. It launches `dexcom_tracker.py`, reads the
workbook it produces, and serves that workbook unchanged from `/api/download`.

## Configuration

Copy `.env.example` to `.env` to change `RESULTS_PER_QUERY`, `BROWSER_HEADLESS`, output filename,
or company keyword. No API key is required.

## Limitations

The tool only uses content LinkedIn publicly renders. If LinkedIn displays a verification, CAPTCHA,
or other access restriction, it stops without attempting to bypass it and does not modify Excel.

## Tests

```bash
PYTHONPATH=. pytest -q
PYTHONPATH=. python -m compileall . -x '.venv'
```
