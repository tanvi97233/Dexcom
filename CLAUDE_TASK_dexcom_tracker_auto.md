# Dexcom Job Posting Tracker — Safe Operating Procedure

The requested full-automation approach is intentionally not implemented. LinkedIn restricts
automated browser login and job-search scraping, which can lead to rate limiting or account
action. Use the manual collection workflow in `CLAUDE_TASK_dexcom_tracker.md` instead.

## Run the tracker

1. On Thursday, manually browse LinkedIn Jobs for **Dexcom**, location **Worldwide**, filtered to
   **Past 7 Days**. On Friday, use **Past 24 Hours**.
2. For each job, record one line in `raw_jobs.txt`:

   ```text
   Country | YYYY-MM-DD | Job Title | currentJobId
   ```

3. Run:

   ```bash
   .venv/bin/python parse_and_update.py
   ```

4. Review the printed counts and, if present, the `Needs Review` sheet. Spot-check 2–3 direct
   URLs manually.

The parser builds direct URLs, deduplicates every saved job ID, and appends valid new rows to
`Dexcom_Job_Tracker.xlsx`.
