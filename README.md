# Dexcom LinkedIn Job Tracker

This project collects publicly rendered **Dexcom** LinkedIn Jobs postings worldwide and maintains a
single Excel tracker. It uses local/headless Chrome with Selenium—no LinkedIn login, credentials,
paid APIs, or access-control bypasses.

The workbook is the canonical dataset and always has exactly these columns:

```text
Country
Job Posted Date
Job Title
Direct URL
```

## Production architecture

```text
GitHub Actions → existing Python tracker → Dexcom_Job_Tracker.xlsx
                                             ↓
                                      web/jobs.json
                                             ↓
                                  static dashboard / Excel download
```

GitHub Actions runs the real tracker and commits the resulting workbook and dashboard JSON to the
repository. The static dashboard never attempts to run Python or Selenium.

### Schedule

GitHub Actions cron uses **UTC**:

| Day | UTC schedule | IST time | Filter |
| --- | --- | --- | --- |
| Thursday | 03:30 UTC | 09:00 IST | Past 7 Days (`7days`) |
| Friday | 03:30 UTC | 09:00 IST | Past 24 Hours (`24hours`) |

Scheduled runs are serialized, so two runs cannot update the workbook at the same time.

## Run the workflow manually

1. Open the GitHub repository’s **Actions** tab.
2. Choose **Dexcom LinkedIn Job Tracker**.
3. Select **Run workflow**.
4. Choose `7days` or `24hours` and run it.

After a successful run, the workflow validates the workbook, regenerates `web/jobs.json` from the
workbook, and commits both files only if they changed.

## Static dashboard and download

The dashboard reads the committed `web/jobs.json`, which is generated from—not maintained
separately from—the Excel workbook. It supports searching, country filtering, sorting, and
pagination. Its **Download Excel** link downloads the committed
[`Dexcom_Job_Tracker.xlsx`](Dexcom_Job_Tracker.xlsx).

Vercel, if used, is strictly a static host for this dashboard and workbook. It does not execute the
tracker.

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python app.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The local app retains its API and can run the
existing CLI on demand for development. Local Chrome is visible by default; set
`BROWSER_HEADLESS=true` for headless mode.

### CLI

```bash
PYTHONPATH=. python dexcom_tracker.py --filter 7days --output Dexcom_Job_Tracker.xlsx
PYTHONPATH=. python dexcom_tracker.py --filter 24hours --output Dexcom_Job_Tracker.xlsx
```

The tracker validates Dexcom employment, applies the selected date window, canonicalizes LinkedIn
job URLs, and deduplicates by LinkedIn job ID before updating Excel.

### Refresh static dashboard data locally

After any direct workbook update, regenerate the dashboard JSON:

```bash
PYTHONPATH=. python export_dashboard_data.py \
  --workbook Dexcom_Job_Tracker.xlsx \
  --output web/jobs.json
```

This command validates the workbook’s headers, direct URLs, and duplicate URLs before writing JSON.

## Optional Docker verification

`Dockerfile` remains available only for reproducible local/headless Chromium testing. Render is no
longer part of the application architecture, and `render.yaml` has been removed.

## Tests

```bash
PYTHONPATH=. pytest -q
PYTHONPATH=. python -m compileall app.py discovery.py dexcom_tracker.py tracker_engine.py query_matrix.py export_dashboard_data.py
```

## Limitations

The tracker uses only what LinkedIn publicly renders. If LinkedIn shows a verification, CAPTCHA,
or another access restriction, it stops without attempting to bypass it and leaves Excel unchanged.
