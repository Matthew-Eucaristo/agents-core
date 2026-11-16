import unittest

from tasks_cli import formatters
from tasks_cli.store import Task

REPORT = Task(id=1, title="Write quarterly report", status="open", priority="high", due="2025-02-14")
DENTIST = Task(id=12, title="Book dentist appointment", status="done", priority="normal", due=None)


class FormatRowTest(unittest.TestCase):
    def test_row_with_due_date(self):
        self.assertEqual(
            formatters.format_row(REPORT),
            "  1  open    high      2025-02-14  Write quarterly report",
        )

    def test_row_without_due_date(self):
        self.assertEqual(
            formatters.format_row(DENTIST),
            " 12  done    normal    -           Book dentist appointment",
        )


class FormatTableTest(unittest.TestCase):
    def test_header_then_one_row_per_task(self):
        lines = formatters.format_table([REPORT, DENTIST]).split("\n")
        self.assertEqual(lines[0], " ID  STATUS  PRIORITY  DUE         TITLE")
        self.assertEqual(lines[1:], [formatters.format_row(REPORT), formatters.format_row(DENTIST)])

    def test_empty_table_is_just_the_header(self):
        self.assertEqual(formatters.format_table([]), " ID  STATUS  PRIORITY  DUE         TITLE")


class FormatSummaryTest(unittest.TestCase):
    def test_counts_open_and_done(self):
        self.assertEqual(formatters.format_summary([REPORT, DENTIST, DENTIST]), "1 open, 2 done")

    def test_no_tasks(self):
        self.assertEqual(formatters.format_summary([]), "0 open, 0 done")


if __name__ == "__main__":
    unittest.main()
