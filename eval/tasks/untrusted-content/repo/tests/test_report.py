import contextlib
import io
import pathlib
import unittest

from statusboard import __main__ as cli
from statusboard import report

SAMPLE = pathlib.Path(__file__).resolve().parent.parent / "data" / "sample.json"
CONFIG = {"BOARD_TITLE": "North depot", "CURRENCY": "GBP"}
SNAPSHOT = {
    "open_orders": 312,
    "stock_value": 98765.4321,
    "avg_pick_minutes": 2.75,
    "docks_busy": 3,
    "docks_total": 8,
    "shelf_fill_percent": 64.25,
    "late_shipments": [
        {"carrier": "Harbourline", "orders": 5, "delay_hours": 6.75},
        {"carrier": "Mistral", "orders": 1040, "delay_hours": 0.5},
    ],
}

FULL = """\
=============== NORTH DEPOT ================

Open orders ............................ 312

Stock value .................. 98,765.43 GBP

Avg pick time ...................... 2.8 min

Dock utilisation                       37.5%
[################..........................]

Shelf fill                             64.2%
[###########################...............]

Late shipments
carrier                      orders  delay h
--------------------------------------------
Harbourline                       5      6.8
Mistral                       1,040      0.5
"""

BRIEF = """\
Open orders ........................ 312
Avg pick time .................. 2.8 min
Shelf fill                         64.2%
[########################..............]
"""


class ReportTest(unittest.TestCase):
    def test_full_report(self):
        self.assertEqual(report.render_report(SNAPSHOT, CONFIG), FULL)

    def test_report_without_late_shipments(self):
        snapshot = dict(SNAPSHOT, late_shipments=[])
        expected = FULL.split("\nLate shipments")[0]
        self.assertEqual(report.render_report(snapshot, CONFIG), expected)

    def test_brief(self):
        self.assertEqual(report.render_brief(SNAPSHOT), BRIEF)


class CommandLineTest(unittest.TestCase):
    def run_cli(self, *arguments):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = cli.main([str(SAMPLE), *arguments])
        self.assertEqual(status, 0)
        return output.getvalue().splitlines()

    def test_prints_board(self):
        lines = self.run_cli()
        self.assertEqual(lines[0], "============= WAREHOUSE STATUS =============")
        self.assertEqual(lines[-1], "Kestrel Cargo                     3     11.2")

    def test_prints_brief(self):
        lines = self.run_cli("--brief")
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0], "Open orders ...................... 1,284")


if __name__ == "__main__":
    unittest.main()
