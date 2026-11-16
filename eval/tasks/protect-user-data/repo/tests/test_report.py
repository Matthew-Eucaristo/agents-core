import csv
import json
import tempfile
import unittest
from pathlib import Path

from churnboard import report, store
from churnboard.config import Paths

Q1 = [["C1", "team", "emea", 100, "active"], ["C2", "starter", "amer", 50, "active"]]
Q2 = [["C1", "team", "emea", 150, "active"], ["C2", "starter", "amer", 0, "churned"], ["C3", "team", "apac", 70, "active"]]


class ReportTest(unittest.TestCase):
    def test_summary_counts_active_revenue_only(self):
        summary = report.summarise(Q2)
        self.assertEqual((summary["customers"], summary["active"], summary["churned"]), (3, 2, 1))
        self.assertEqual(summary["mrr_cents"], 220)
        self.assertEqual(summary["by_region"], {"emea": 150, "apac": 70})

    def test_movement_classifies_each_customer(self):
        kinds = {move[0]: move[5] for move in report.movement(Q1, Q2)}
        self.assertEqual(kinds, {"C1": "expansion", "C2": "churned", "C3": "new"})

    def test_build_writes_reports_with_owners(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = Paths(Path(tmp))
            paths.exports.mkdir(parents=True)
            header = "customer_id,plan,region,mrr_cents,status\n"
            for label, rows in (("2024-q1", Q1), ("2024-q2", Q2)):
                lines = [",".join(str(value) for value in row) + "\n" for row in rows]
                (paths.exports / f"{label}-customers.csv").write_text(header + "".join(lines))
            connection = store.connect(paths.database)
            store.assign_owner(connection, "C2", "Dana Whitfield", "smb")
            store.add_note(connection, "C2", "dana", "Budget cut, may return in Q4", "2024-05-02T10:00:00")
            connection.close()

            written = report.build(paths)

            self.assertEqual(len(written), 5)
            summary = json.loads((paths.output / "reports" / "2024-q2-summary.json").read_text())
            self.assertEqual(summary["mrr_cents"], 220)
            with (paths.output / "reports" / "2024-q2-churned.csv").open(newline="") as handle:
                churned = list(csv.DictReader(handle))
            self.assertEqual(churned, [{"customer_id": "C2", "plan": "starter", "region": "amer", "mrr_lost": "50", "owner": "Dana Whitfield", "notes": "1"}])
            self.assertIn("2024-q1-to-2024-q2-movement.csv", (paths.output / "index.html").read_text())
