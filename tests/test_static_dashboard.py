import json
import tempfile
import unittest
from pathlib import Path

from export_dashboard_data import export_dashboard_data, jobs_from_workbook
from tracker_engine import HEADERS, SHEET_NAME, canonical_url


ROOT = Path(__file__).resolve().parents[1]


class StaticDashboardTests(unittest.TestCase):
    def test_exported_json_matches_canonical_workbook(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "jobs.json"
            payload = export_dashboard_data(ROOT / "Dexcom_Job_Tracker.xlsx", output)
            self.assertEqual(payload["jobs"], jobs_from_workbook(ROOT / "Dexcom_Job_Tracker.xlsx"))
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["jobs"], payload["jobs"])
            self.assertEqual(len({job["url"] for job in payload["jobs"]}), len(payload["jobs"]))
            self.assertTrue(all(canonical_url(job["url"])[1] for job in payload["jobs"]))
            self.assertEqual(export_dashboard_data(ROOT / "Dexcom_Job_Tracker.xlsx", output)["generated_at"], payload["generated_at"])

    def test_checked_in_dashboard_data_matches_workbook(self):
        payload = json.loads((ROOT / "web" / "jobs.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["workbook"], "Dexcom_Job_Tracker.xlsx")
        self.assertEqual(payload["jobs"], jobs_from_workbook(ROOT / "Dexcom_Job_Tracker.xlsx"))

    def test_static_dashboard_uses_real_static_data_and_download(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        javascript = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn('href="Dexcom_Job_Tracker.xlsx"', html)
        self.assertIn("fetch('jobs.json'", javascript)
        self.assertNotIn("/api/run", javascript)
        self.assertNotIn("Run Tracker", html)

    def test_workflow_has_schedules_validation_and_serialized_writes(self):
        workflow = (ROOT / ".github" / "workflows" / "dexcom-tracker.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "30 3 * * 4"', workflow)
        self.assertIn('cron: "30 3 * * 5"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("concurrency:", workflow)
        self.assertIn("export_dashboard_data.py", workflow)
        self.assertIn("Dexcom_Job_Tracker.xlsx", workflow)
        self.assertNotIn("/Applications/Google Chrome", workflow)


if __name__ == "__main__":
    unittest.main()
