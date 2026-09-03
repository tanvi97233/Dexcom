# Task: Dexcom Job Posting Tracker (LinkedIn — Manual Collection)

## Context

Recurring SOP. Thursdays = "Past 7 Days" filter, Fridays = "Past 24 Hours" filter.
Output: `Dexcom_Job_Tracker.xlsx`, columns: Country | Job Posted Date | Job Title | Direct URL.

## Important constraint

LinkedIn blocks automated scraping/browser automation on its job search pages (against their
Terms of Service, and they actively detect + rate-limit/ban it). Do **not** write a Playwright/
Selenium script that logs in and scrapes automatically — it risks the account. Instead, use the
**human-browses, Claude-structures** pattern below. The human (5–10 min of browsing) stays fast
because Claude does 100% of the formatting, dedup, and validation.

## Workflow

### Step 1 — Human browses LinkedIn (5–10 min)

1. LinkedIn → Jobs → search "Dexcom" → Location: Worldwide.
2. Apply the day's time filter (Past 7 Days on Thu / Past 24 Hours on Fri).
3. For each job card, click it open. Copy the URL from the address bar — it will look like
   `https://www.linkedin.com/jobs/search/?currentJobId=1234567890&...` — you only need the
   `currentJobId` number.
4. Paste ONE LINE per job into a scratch file (`raw_jobs.txt`) in this exact pipe-separated
   format (country and date are visible on the job card/detail panel):

   ```
   United States | 2026-08-28 | Senior Software Engineer, CGM Platform | 1234567890
   Ireland | 2026-08-27 | Field Clinical Specialist | 1234567891
   ```

   (Title case, don't worry about perfect formatting — the script normalizes it.)

### Step 2 — Claude Code parses + writes the Excel file

Run `parse_and_update.py` (below) pointing at `raw_jobs.txt` and the existing tracker. It will:

- Build the direct URL as `https://www.linkedin.com/jobs/view/{currentJobId}`
- Append new rows to the existing tracker (creates it from scratch on first run)
- **Dedupe** against every previously saved job ID (including prior Thursday/Friday runs) so
  reposted/already-captured jobs are skipped automatically
- Sort by Country, then Job Posted Date (desc)
- Flag any row missing a required field in a `Needs Review` sheet instead of silently dropping it

### Step 3 — Quality check (human, 2 min)

- Spot-check 2–3 URLs actually open the correct posting.
- Confirm `Needs Review` sheet is empty (or fix flagged rows).
- Save.

## `parse_and_update.py`

```python
import sys
import re
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter

RAW_FILE = "raw_jobs.txt"
TRACKER_FILE = "Dexcom_Job_Tracker.xlsx"
SHEET_NAME = "Dexcom Job Tracker"
HEADERS = ["Country", "Job Posted Date", "Job Title", "Direct URL"]

def parse_raw(path):
    rows, bad = [], []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 4:
                bad.append((lineno, line, "wrong number of fields"))
                continue
            country, date_str, title, job_id = parts
            job_id = re.sub(r"\D", "", job_id)  # keep digits only
            if not job_id:
                bad.append((lineno, line, "no numeric job id"))
                continue
            try:
                date_val = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                bad.append((lineno, line, "bad date format, expected YYYY-MM-DD"))
                continue
            if not country or not title:
                bad.append((lineno, line, "missing country or title"))
                continue
            url = f"https://www.linkedin.com/jobs/view/{job_id}"
            rows.append({"country": country, "date": date_val, "title": title,
                         "url": url, "job_id": job_id})
    return rows, bad

def load_or_create_tracker(path):
    try:
        wb = openpyxl.load_workbook(path)
        ws = wb[SHEET_NAME]
        existing_ids = set()
        for r in range(2, ws.max_row + 1):
            url = ws.cell(row=r, column=4).value
            if url:
                m = re.search(r"(\d+)$", str(url))
                if m:
                    existing_ids.add(m.group(1))
        return wb, ws, existing_ids
    except FileNotFoundError:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = SHEET_NAME
        for col, h in enumerate(HEADERS, start=1):
            c = ws.cell(row=1, column=col, value=h)
            c.font = Font(name="Arial", bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1F4E78")
        return wb, ws, set()

def write_rows(ws, rows):
    thin = Side(style="thin", color="B7B7B7")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    next_row = ws.max_row + 1
    for row in rows:
        ws.cell(row=next_row, column=1, value=row["country"]).font = Font(name="Arial", size=10)
        c2 = ws.cell(row=next_row, column=2, value=row["date"])
        c2.number_format = "yyyy-mm-dd"
        c2.font = Font(name="Arial", size=10)
        ws.cell(row=next_row, column=3, value=row["title"]).font = Font(name="Arial", size=10)
        c4 = ws.cell(row=next_row, column=4, value=row["url"])
        c4.hyperlink = row["url"]
        c4.font = Font(name="Arial", size=10, color="0563C1", underline="single")
        for col in range(1, 5):
            ws.cell(row=next_row, column=col).border = border
        next_row += 1

def write_needs_review(wb, bad):
    if "Needs Review" in wb.sheetnames:
        del wb["Needs Review"]
    if not bad:
        return
    ws = wb.create_sheet("Needs Review")
    ws.append(["Line #", "Raw line", "Issue"])
    for lineno, line, issue in bad:
        ws.append([lineno, line, issue])

def main():
    rows, bad = parse_raw(RAW_FILE)
    wb, ws, existing_ids = load_or_create_tracker(TRACKER_FILE)
    new_rows = [r for r in rows if r["job_id"] not in existing_ids]
    skipped_dupes = len(rows) - len(new_rows)
    write_rows(ws, new_rows)
    write_needs_review(wb, bad)
    for i, w in enumerate([20, 18, 55, 60], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    wb.save(TRACKER_FILE)
    print(f"Added {len(new_rows)} new rows. Skipped {skipped_dupes} duplicates. "
          f"{len(bad)} malformed lines sent to 'Needs Review'.")

if __name__ == "__main__":
    main()
```

## Instructions for Claude Code (say this verbatim as your prompt)

> Read `CLAUDE_TASK_dexcom_tracker.md` in this folder. Set up `parse_and_update.py` as given.
> I'll paste job lines into `raw_jobs.txt` in the specified format. Run the script against my
> existing `Dexcom_Job_Tracker.xlsx` (or create it if missing), then run `recalc.py` from the
> xlsx skill if available, and confirm row counts, dupes skipped, and anything sent to
> `Needs Review`.

## Not supported

Do not replace this workflow with browser automation that logs into or scrapes LinkedIn (for
example, Playwright or Selenium). The collection step must remain human-driven; this script only
structures and validates the job details the user manually records.
