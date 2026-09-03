import sys
import unittest
from unittest.mock import Mock, patch

import dexcom_tracker
from tracker_engine import JobResult


class DexcomTrackerCliTests(unittest.TestCase):
    def test_24hours_filter_is_supported_by_the_existing_cli(self):
        provider = Mock()
        provider.search.return_value = []
        provider.last_cards_seen = 0
        with patch.object(sys, "argv", ["dexcom_tracker.py", "--filter", "24hours", "--dry-run"]), \
             patch("dexcom_tracker.configured_linkedin_provider", return_value=provider):
            self.assertEqual(dexcom_tracker.main(), 0)
        provider.close.assert_called_once()

    def test_dry_run_never_copies_to_downloads(self):
        provider = Mock()
        provider.search.return_value = [
            JobResult(
                "https://www.linkedin.com/jobs/view/1/",
                "Engineer",
                "Dexcom",
                "Dublin, Ireland",
                "today",
            )
        ]
        provider.last_cards_seen = 1
        with patch.object(sys, "argv", ["dexcom_tracker.py", "--filter", "7days", "--dry-run"]), \
             patch("dexcom_tracker.configured_linkedin_provider", return_value=provider), \
             patch("dexcom_tracker.update_tracker") as update_tracker, \
             patch("dexcom_tracker.copy_to_downloads") as copy_to_downloads:
            self.assertEqual(dexcom_tracker.main(), 0)
        provider.close.assert_called_once()
        update_tracker.assert_not_called()
        copy_to_downloads.assert_not_called()

    def test_excel_update_failure_does_not_copy_to_downloads(self):
        provider = Mock()
        provider.search.return_value = [
            JobResult(
                "https://www.linkedin.com/jobs/view/1/",
                "Engineer",
                "Dexcom",
                "Dublin, Ireland",
                "today",
            )
        ]
        provider.last_cards_seen = 1
        with patch.object(sys, "argv", ["dexcom_tracker.py", "--filter", "7days"]), \
             patch("dexcom_tracker.configured_linkedin_provider", return_value=provider), \
             patch("dexcom_tracker.update_tracker", side_effect=OSError("write failed")), \
             patch("dexcom_tracker.copy_to_downloads") as copy_to_downloads:
            self.assertEqual(dexcom_tracker.main(), 1)
        provider.close.assert_called_once()
        copy_to_downloads.assert_not_called()


if __name__ == "__main__":
    unittest.main()
