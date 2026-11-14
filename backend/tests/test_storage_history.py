import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import storage


class StorageHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_path = storage.DB_PATH
        storage.DB_PATH = Path(self.tmp.name) / "test.db"
        storage.init_db()

    def tearDown(self):
        storage.DB_PATH = self.old_path
        self.tmp.cleanup()

    def test_round_trip_snapshot_and_alert(self):
        payload = {
            "mode": "demo", "repository": "demo/repo", "developer": "demo-user",
            "events_collected": 12, "collection": {"commits": 4},
            "results": [{"category": "Testing", "alert": True, "drift_score": 71.5,
                          "trajectory": "gradual-decline", "current_score": 42,
                          "baseline_mean": 66, "recommendation": "Add focused tests.",
                          "explanation": ["Testing signals reduced."]}],
        }
        run_id, timestamp = storage.save_run(payload)
        runs = storage.run_history(10)
        self.assertEqual(runs[0]["run_id"], run_id)
        self.assertEqual(runs[0]["results"][0]["category"], "Testing")
        self.assertEqual(runs[0]["collection"]["commits"], 4)
        alerts = storage.alert_history(10)
        self.assertEqual(alerts[0]["id"], f"{run_id}:Testing")
        self.assertEqual(alerts[0]["drift_score"], 71.5)

    def test_migrates_legacy_schema(self):
        with sqlite3.connect(storage.DB_PATH) as conn:
            conn.execute("DROP TABLE IF EXISTS runs")
            conn.execute("""CREATE TABLE runs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, mode TEXT NOT NULL, repository TEXT NOT NULL, developer TEXT NOT NULL, events INTEGER NOT NULL, alerts INTEGER NOT NULL, average_drift REAL NOT NULL, average_signal REAL NOT NULL, results_json TEXT NOT NULL)""")
            conn.commit()
        storage.init_db()
        with sqlite3.connect(storage.DB_PATH) as conn:
            cols = {row[1] for row in conn.execute("PRAGMA table_info(runs)").fetchall()}
        self.assertIn("payload_json", cols)


if __name__ == "__main__":
    unittest.main()
