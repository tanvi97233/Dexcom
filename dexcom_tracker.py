#!/usr/bin/env python3
"""Collect publicly rendered Dexcom LinkedIn job cards and maintain the Excel tracker."""
import argparse
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

from discovery import DiscoveryError, configured_linkedin_provider, load_env
from tracker_engine import canonical_url, is_dexcom_employer, update_tracker, validate, within_window


def copy_to_downloads(workbook: Path, downloads_dir: Path | None = None) -> Path:
    """Copy a completed workbook to Downloads, creating that directory if needed."""
    destination_dir = downloads_dir or Path.home() / "Downloads"
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / workbook.name
    shutil.copy2(workbook, destination)
    return destination


def main() -> int:
    load_env()
    parser = argparse.ArgumentParser(description="Track public Dexcom LinkedIn Jobs results in Excel.")
    parser.add_argument("--filter", required=True, choices=["7days", "24hours"])
    parser.add_argument("--max-results", type=int, default=int(os.getenv("RESULTS_PER_QUERY", "50")))
    parser.add_argument("--max-search-queries", type=int, default=1, help="Retained for CLI compatibility; public LinkedIn Jobs is the primary source.")
    parser.add_argument("--output", default=os.getenv("OUTPUT_FILE", "Dexcom_Job_Tracker.xlsx"))
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(filename="logs/dexcom_tracker.log", level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    label = "Past 7 Days" if args.filter == "7days" else "Past 24 Hours"
    print("Starting Dexcom Job Tracker...\n\nDiscovery method: LinkedIn public Jobs page")
    print(f"Company: {os.getenv('COMPANY_NAME', 'Dexcom')}\nLocation: Worldwide\nFilter: {label}\n\nOpening Chrome...")
    provider = configured_linkedin_provider(args.filter, args.verbose)
    try:
        discovered = provider.search(args.filter, args.max_results)
    except DiscoveryError as error:
        print(f"\nLinkedIn public job search could not be accessed.\n{error}\nNo jobs were collected. Excel was not modified.")
        return 2
    finally:
        provider.close()
    job_urls = [item for item in discovered if canonical_url(item.direct_url)[1]]
    unique, duplicates = {}, 0
    for item in job_urls:
        _, job_id = canonical_url(item.direct_url)
        if job_id in unique: duplicates += 1
        else: unique[job_id] = item
    dexcom = [item for item in unique.values() if is_dexcom_employer(item)]
    reference = datetime.now(); valid, failures = [], []
    for item in dexcom:
        record, error = validate(item, reference)
        if error: failures.append(f"{item.direct_url}: {error}"); continue
        if within_window(record.posted_at, reference, args.filter): valid.append(record)
    added = existing = 0
    saved_copy = None
    if not args.dry_run and valid:
        output = Path(args.output)
        try:
            added, existing = update_tracker(valid, output)
        except Exception as error:
            logging.exception("Excel update failed")
            print(f"\nExcel update failed. Downloads copy was not created.\n{error}")
            return 1
        try:
            saved_copy = copy_to_downloads(output.resolve())
        except OSError as error:
            logging.exception("Downloads copy failed")
            print(f"\nExcel was updated, but the Downloads copy could not be saved.\n{error}")
            return 1
    print("\nDexcom Job Tracker\n------------------")
    print(f"LinkedIn job cards discovered: {provider.last_cards_seen}")
    print(f"Valid LinkedIn job URLs:      {len(job_urls)}")
    print(f"Unique jobs:                  {len(unique)}")
    print(f"Dexcom jobs:                  {len(dexcom)}")
    print(f"Jobs within date range:       {len(valid)}")
    print(f"Validation failures:          {len(failures)}")
    print(f"Duplicates removed:           {duplicates}")
    print(f"Existing jobs skipped:        {existing}")
    print(f"New jobs added:               {added}")
    print(f"\nExcel: {args.output}" + (" (dry run — unchanged)" if args.dry_run else ""))
    if saved_copy:
        print(f"Saved copy: {saved_copy}")
    for failure in failures:
        logging.warning(failure)
        if args.verbose: print(f"  Invalid: {failure}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
