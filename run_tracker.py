#!/usr/bin/env python3
"""Command-line entry point for the source-independent Dexcom tracker."""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from tracker_engine import process_records, read_input


def configure_logging() -> Path:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    path = log_dir / f"dexcom_tracker_{datetime.now():%Y%m%d_%H%M%S}.log"
    logging.basicConfig(filename=path, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate, deduplicate, and maintain the Dexcom Excel job tracker.")
    parser.add_argument("--input", required=True, help="Externally collected job data in CSV or JSON format.")
    parser.add_argument("--filter", choices=["7days", "24hours"], help="Optional source-window label stored in the log.")
    parser.add_argument("--tracker", default="Dexcom_Job_Tracker.xlsx", help="Output workbook path.")
    args = parser.parse_args()
    log_path = configure_logging()
    try:
        input_path = Path(args.input)
        records = read_input(input_path)
        result = process_records(records, Path(args.tracker))
    except (OSError, ValueError) as error:
        logging.exception("Run failed")
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    filter_label = {"7days": "Past 7 Days", "24hours": "Past 24 Hours"}.get(args.filter, "Not supplied")
    logging.info("filter=%s input=%s records=%d valid=%d added=%d duplicates=%d invalid=%d", args.filter, input_path, result.input_records, result.valid_records, result.new_records, result.duplicates, len(result.invalid))
    print("Dexcom Job Tracker")
    print("------------------")
    print(f"Filter: {filter_label}")
    print(f"Input records: {result.input_records}")
    print(f"Valid records: {result.valid_records}")
    print(f"New jobs added: {result.new_records}")
    print(f"Duplicates skipped: {result.duplicates}")
    print(f"Invalid records: {len(result.invalid)}")
    print()
    print(f"Excel: {args.tracker}")
    print(f"Log: {log_path}")
    if result.invalid:
        print("Validation report:")
        for error in result.invalid:
            print(f"- {error}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
